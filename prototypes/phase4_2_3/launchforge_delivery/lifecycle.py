"""Runtime-facing lifecycle facade with an explicit launch-adapter seam.

No subprocess is spawned here. Production Runtime must implement LauncherAdapter
using its approved process policy and handle-based executable validation.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Protocol, runtime_checkable

from .transaction import Artifact, FileRecord, InstallResult, TransactionEngine, TransactionError
from .manifest_adapter import artifacts_from_verified_manifest


class GameState(str, Enum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    STAGING = "staging"
    COMMITTING = "committing"
    VERIFYING = "verifying"
    INSTALLED = "installed"
    READY = "ready"
    LAUNCHING = "launching"
    RUNNING = "running"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass(frozen=True)
class GameSnapshot:
    operation_id: str
    game_id: str
    state: GameState
    version: Optional[str] = None
    completed_bytes: int = 0
    total_bytes: int = 0
    message: str = ""
    error_code: Optional[str] = None


@dataclass(frozen=True)
class LaunchConfig:
    executable: str
    arguments: tuple[str, ...] = ()


@runtime_checkable
class LauncherAdapter(Protocol):
    """Narrow bridge implemented by the approved native Runtime host."""

    def launch(self, installation_root: Path, executable_relative: str, expected_sha256: str, arguments: tuple[str, ...]) -> object:
        """Launch via handle-relative validation, without a shell, and return a process handle."""
        ...


@runtime_checkable
class VerifiedArtifactProvider(Protocol):
    """Adapter implemented by the Phase 4.1 downloader/provider."""

    def acquire(self, verified_manifest: object, progress: Callable[[int, int], None], cancelled: Callable[[], bool]) -> Mapping[str, Path]:
        """Return manifest-path -> fully size/hash-verified temporary-file paths."""
        ...


class GameLifecycleService:
    """Synchronous lifecycle API over a TransactionEngine.

    Inputs to install/update/repair are already-downloaded artifacts. The adapter
    must only supply paths emitted by a successfully authenticated bounded
    downloader. TransactionEngine rehashes every source while copying, so a
    source mutation between download verification and staging is rejected.
    """

    def __init__(self, engine: TransactionEngine, *, on_change: Optional[Callable[[GameSnapshot], None]] = None) -> None:
        self.engine = engine
        self.on_change = on_change
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._busy = False
        self._snapshot = GameSnapshot("", "", GameState.IDLE)
        self._process_handle: object | None = None

    @property
    def snapshot(self) -> GameSnapshot:
        with self._lock:
            return self._snapshot

    def cancel(self) -> bool:
        """Cancel an operation while it is staging; commit is intentionally non-cancellable."""
        with self._lock:
            if not self._busy or self._snapshot.state not in (GameState.DOWNLOADING, GameState.STAGING):
                return False
            self._cancel.set()
            return True

    def install(self, game_id: str, version: str, artifacts: Iterable[Artifact]) -> InstallResult:
        return self._apply("install", game_id, version, artifacts)

    def update(self, game_id: str, version: str, artifacts: Iterable[Artifact]) -> InstallResult:
        return self._apply("update", game_id, version, artifacts)

    def repair(self, game_id: str, version: str, artifacts: Iterable[Artifact]) -> InstallResult:
        return self._apply("repair", game_id, version, artifacts)

    def _apply(self, action: str, game_id: str, version: str, artifacts: Iterable[Artifact]) -> InstallResult:
        items = tuple(artifacts)
        total = sum(item.record.size for item in items)
        self._begin(game_id, version, total, GameState.STAGING)
        return self._execute(action, game_id, version, items, total)

    def apply_verified_manifest(self, action: str, manifest: object, provider: VerifiedArtifactProvider) -> InstallResult:
        """Acquire Phase 4.1 verified files, adapt them, then transact atomically."""
        if action not in ("install", "update", "repair"):
            raise TransactionError("unsupported game delivery operation")
        try:
            game_id = manifest.game_id
            version = manifest.release_version
            files = tuple(manifest.files)
            total = sum(entry.size for entry in files)
        except (AttributeError, TypeError) as exc:
            raise TransactionError("manifest does not expose the verified release interface") from exc
        if not files or any(type(entry.size) is not int or entry.size < 0 for entry in files):
            raise TransactionError("manifest file list or file sizes are invalid")
        self._begin(game_id, version, total, GameState.DOWNLOADING)

        def download_progress(done: int, expected: int) -> None:
            if type(done) is not int or type(expected) is not int or done < 0 or expected != total or done > total:
                raise TransactionError("artifact provider emitted invalid aggregate progress")
            self._set(GameState.DOWNLOADING, completed_bytes=done, total_bytes=expected, message="Downloading and verifying release artifacts")

        downloads: Mapping[str, Path] = {}
        try:
            downloads = provider.acquire(manifest, download_progress, self._cancel.is_set)
            if self._cancel.is_set():
                raise TransactionError("operation cancelled before staging")
            artifacts = artifacts_from_verified_manifest(manifest, downloads)
            self._set(GameState.STAGING, completed_bytes=0, total_bytes=total, message="Staging verified artifacts")
        except Exception as exc:
            cleanup = getattr(provider, "cleanup", None)
            if callable(cleanup):
                cleanup(downloads)
            if self._cancel.is_set():
                self._set(GameState.CANCELLED, message="Operation cancelled during download", error_code="cancelled")
            else:
                self._set(GameState.ERROR, message=str(exc), error_code=type(exc).__name__)
            with self._lock:
                self._busy = False
                self._cancel.clear()
            raise
        try:
            return self._execute(action, game_id, version, artifacts, total)
        finally:
            cleanup = getattr(provider, "cleanup", None)
            if callable(cleanup):
                cleanup(downloads)

    def _execute(self, action: str, game_id: str, version: str, items: tuple[Artifact, ...], total: int) -> InstallResult:
        def progress(done: int, expected: int) -> None:
            self._set(GameState.STAGING, completed_bytes=done, total_bytes=expected, message="Staging verified artifacts")

        def phase(name: str) -> None:
            mapping = {"committing": GameState.COMMITTING, "verifying": GameState.VERIFYING}
            self._set(mapping[name], completed_bytes=total, total_bytes=total, message=name.capitalize() + " installation")

        try:
            method = getattr(self.engine, action)
            result = method(
                game_id,
                version,
                items,
                progress=progress,
                phase=phase,
                cancelled=self._cancel.is_set,
            )
            self._set(GameState.INSTALLED, completed_bytes=total, total_bytes=total, message=f"{action.capitalize()} complete")
            return result
        except Exception as exc:
            if self._cancel.is_set():
                self._set(GameState.CANCELLED, message="Operation cancelled before commit", error_code="cancelled")
            else:
                self._set(GameState.ERROR, message=str(exc), error_code=type(exc).__name__)
            raise
        finally:
            with self._lock:
                self._busy = False
                self._cancel.clear()

    def verify(self, game_id: str, version: str, records: Iterable[FileRecord]) -> bool:
        expected = tuple(records)
        self._begin(game_id, version, sum(x.size for x in expected), GameState.VERIFYING)
        try:
            valid = self.engine.verify(expected)
            self._set(GameState.READY if valid else GameState.ERROR, message="Installed files verified" if valid else "Installed files failed integrity verification", error_code=None if valid else "integrity_mismatch")
            return valid
        except Exception as exc:
            self._set(GameState.ERROR, message=str(exc), error_code=type(exc).__name__)
            raise
        finally:
            with self._lock:
                self._busy = False

    def launch(self, game_id: str, version: str, records: Iterable[FileRecord], config: LaunchConfig, adapter: LauncherAdapter) -> object:
        expected = tuple(records)
        self._begin(game_id, version, sum(x.size for x in expected), GameState.VERIFYING)
        try:
            if not self.engine.verify(expected):
                raise TransactionError("launch blocked: installed game failed integrity verification")
            declared = {item.path: item for item in expected}
            if not isinstance(config.executable, str) or config.executable not in declared:
                raise TransactionError("launch executable is not declared in the verified manifest")
            from .transaction import validate_relative_path
            validate_relative_path(config.executable)
            if not isinstance(config.arguments, (tuple, list)) or len(config.arguments) > 128 or any(not isinstance(a, str) or len(a) > 4096 or "\x00" in a for a in config.arguments):
                raise TransactionError("launch arguments exceed the supported safe bounds")
            self._set(GameState.LAUNCHING, message="Starting verified game executable")
            handle = adapter.launch(self.engine.install_dir, config.executable, declared[config.executable].sha256, tuple(config.arguments))
            if handle is None:
                raise TransactionError("Runtime adapter did not return a process handle")
            self._process_handle = handle
            self._set(GameState.RUNNING, message="Game process started")
            return handle
        except Exception as exc:
            self._set(GameState.ERROR, message=str(exc), error_code=type(exc).__name__)
            raise
        finally:
            with self._lock:
                self._busy = False

    def process_exited(self, exit_code: Optional[int] = None) -> None:
        """Called by the native Runtime adapter when its process handle exits."""
        if self.snapshot.state != GameState.RUNNING:
            raise TransactionError("process-exit event received while the game is not running")
        self._process_handle = None
        self._set(GameState.READY, message="Game process exited" if exit_code is None else f"Game process exited ({exit_code})")

    def _begin(self, game_id: str, version: str, total: int, state: GameState) -> None:
        with self._lock:
            if self._busy:
                raise TransactionError("another game operation is already running")
            self._busy = True
            self._cancel.clear()
            snapshot = GameSnapshot(uuid.uuid4().hex, game_id, state, version, 0, total, state.value)
            self._snapshot = snapshot
        self._notify(snapshot)

    def _set(self, state: GameState, *, completed_bytes: Optional[int] = None, total_bytes: Optional[int] = None, message: str = "", error_code: Optional[str] = None) -> None:
        with self._lock:
            current = self._snapshot
            snapshot = GameSnapshot(
                operation_id=current.operation_id,
                game_id=current.game_id,
                state=state,
                version=current.version,
                completed_bytes=current.completed_bytes if completed_bytes is None else completed_bytes,
                total_bytes=current.total_bytes if total_bytes is None else total_bytes,
                message=message,
                error_code=error_code,
            )
            self._snapshot = snapshot
        self._notify(snapshot)

    def _notify(self, snapshot: GameSnapshot) -> None:
        if self.on_change is not None:
            try:
                self.on_change(snapshot)
            except Exception:
                # UI/telemetry observers must not abort filesystem transactions.
                pass
