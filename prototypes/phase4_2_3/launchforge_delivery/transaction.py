"""Crash-recoverable directory-swap installation prototype (POSIX only).

The install directory must be dedicated to immutable game program files. User
saves/configuration belong outside it. Windows is deliberately fail-closed
until a handle-relative Win32 reparse-point backend is approved and implemented.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fails closed at construction
    fcntl = None


class TransactionError(RuntimeError):
    """A release could not be installed safely."""


class IntegrityError(TransactionError):
    """An input artifact or installed file failed integrity verification."""


class RecoveryError(TransactionError):
    """A pending transaction was ambiguous and was not changed automatically."""


class UnsupportedPlatformError(TransactionError):
    """The platform lacks the required handle-relative filesystem primitives."""


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Artifact:
    record: FileRecord
    source: Path


@dataclass(frozen=True)
class InstallResult:
    action: str
    version: str
    bytes_written: int
    file_count: int


@dataclass(frozen=True)
class RecoveryReport:
    transactions_seen: int
    transactions_recovered: int


_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
_WINDOWS_RESERVED.update(f"COM{i}" for i in range(1, 10))
_WINDOWS_RESERVED.update(f"LPT{i}" for i in range(1, 10))
_WINDOWS_RESERVED.update(f"COM{s}" for s in ("¹", "²", "³"))
_WINDOWS_RESERVED.update(f"LPT{s}" for s in ("¹", "²", "³"))
_HEX_256 = re.compile(r"[0-9a-f]{64}\Z")


def validate_relative_path(path: str, max_path_chars: int = 240) -> tuple[str, ...]:
    """Validate a destination name on both POSIX and Windows filesystems."""
    if not isinstance(path, str) or not path or len(path) > max_path_chars:
        raise TransactionError("destination path is empty or exceeds the path limit")
    if unicodedata.normalize("NFC", path) != path:
        raise TransactionError("destination path must already be Unicode NFC normalized")
    if path.startswith("/") or "\\" in path or "\x00" in path:
        raise TransactionError("destination path must be relative and use '/' separators")
    if any(ch in path for ch in '<>:"|?*') or any(ord(ch) < 32 or ord(ch) == 127 for ch in path):
        raise TransactionError("destination path contains a Windows-invalid character")
    parts = tuple(path.split("/"))
    if not parts or any(p in ("", ".", "..") for p in parts):
        raise TransactionError("destination path contains an empty, '.' or '..' component")
    for part in parts:
        if part.endswith((".", " ")):
            raise TransactionError("destination components may not end in dot or space")
        if len(part.encode("utf-16-le")) // 2 > 255:
            raise TransactionError("destination component exceeds the Windows component limit")
        if part.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
            raise TransactionError("destination path contains a reserved Windows device name")
    return parts


def _validate_records(records: Iterable[FileRecord], max_files: int, max_total_bytes: int, max_path_chars: int) -> tuple[FileRecord, ...]:
    items = tuple(records)
    if not items or len(items) > max_files:
        raise TransactionError("release must contain a non-empty bounded file list")
    seen: set[str] = set()
    total = 0
    for item in items:
        if not isinstance(item, FileRecord):
            raise TransactionError("release entries must be FileRecord values")
        validate_relative_path(item.path, max_path_chars)
        if type(item.size) is not int or item.size < 0:
            raise TransactionError(f"invalid size for {item.path}")
        if not isinstance(item.sha256, str) or not _HEX_256.fullmatch(item.sha256):
            raise TransactionError(f"invalid SHA-256 for {item.path}")
        total += item.size
        if total > max_total_bytes:
            raise TransactionError("release exceeds the configured aggregate size limit")
        key = unicodedata.normalize("NFC", item.path).casefold()
        if key in seen:
            raise TransactionError("release contains case-insensitive destination collisions")
        key_parts = key.split("/")
        if any("/".join(key_parts[:i]) in seen for i in range(1, len(key_parts))):
            raise TransactionError("a destination is nested below another file")
        if any(old.startswith(key + "/") for old in seen):
            raise TransactionError("a destination conflicts with an existing directory path")
        seen.add(key)
    return items


def _require_posix_primitives() -> None:
    needed = ("O_DIRECTORY", "O_NOFOLLOW")
    if os.name != "posix" or fcntl is None or any(not hasattr(os, n) for n in needed) or not hasattr(os, "supports_dir_fd"):
        raise UnsupportedPlatformError("safe transaction backend is not available on this platform; refusing path-based fallback")
    if os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd or os.rename not in os.supports_dir_fd:
        raise UnsupportedPlatformError("required dir_fd operations are unavailable; refusing unsafe fallback")


def _open_absolute_directory(path: Path) -> int:
    """Open an absolute directory by walking from '/' without following symlinks."""
    _require_posix_primitives()
    if not path.is_absolute():
        raise TransactionError("filesystem paths must be absolute")
    parts = path.parts
    if any(part in (".", "..") for part in parts):
        raise TransactionError("filesystem paths may not contain '.' or '..' components")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for component in parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _open_directory_at(parent_fd: int, name: str) -> int:
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    st = os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode):
        os.close(fd)
        raise TransactionError(f"{name!r} is not a directory")
    return fd


def _lstat_at(parent_fd: int, name: str):
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _open_absolute_regular_file(path: Path) -> int:
    if not path.is_absolute() or any(part in (".", "..") for part in path.parts):
        raise TransactionError("artifact source must be an absolute path without dot components")
    parent = _open_absolute_directory(path.parent)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        except OSError as exc:
            raise TransactionError("artifact source is missing, inaccessible, or a symlink/reparse point") from exc
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd)
            raise TransactionError("artifact source must be a regular non-symlink file")
        return fd
    finally:
        os.close(parent)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError(errno.EIO, "short write while staging artifact")
        view = view[written:]


def _ensure_directories(root_fd: int, components: tuple[str, ...]) -> int:
    """Create/open nested directories and return an fd for the leaf parent."""
    current = os.dup(root_fd)
    try:
        for name in components:
            try:
                os.mkdir(name, 0o700, dir_fd=current)
                os.fsync(current)
            except FileExistsError:
                pass
            nxt = _open_directory_at(current, name)
            os.close(current)
            current = nxt
        return current
    except BaseException:
        os.close(current)
        raise


def _write_journal(parent_fd: int, journal_name: str, journal: dict) -> None:
    """Durably publish a journal in the same directory as stage/backup/target."""
    encoded = json.dumps(journal, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > 2 * 1024 * 1024:
        raise TransactionError("transaction journal exceeds its size limit")
    temp_name = journal_name + ".tmp"
    temp_fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
    try:
        _write_all(temp_fd, encoded)
        os.fsync(temp_fd)
    except BaseException:
        os.close(temp_fd)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    else:
        os.close(temp_fd)
    os.rename(temp_name, journal_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    os.fsync(parent_fd)


def _read_limited_file_at(parent_fd: int, name: str, limit: int) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            raise RecoveryError("transaction journal is not a bounded regular file")
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise RecoveryError("transaction journal exceeded its read limit")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _json_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecoveryError("transaction journal contains duplicate keys")
        result[key] = value
    return result


def _read_journal(parent_fd: int, journal_name: str) -> dict:
    try:
        raw = _read_limited_file_at(parent_fd, journal_name, 2 * 1024 * 1024)
        data = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_json_no_duplicates)
    except RecoveryError:
        raise
    except Exception as exc:
        raise RecoveryError("transaction journal is malformed") from exc
    required = {"schema", "transaction", "target", "stage", "backup", "game_id", "version", "old_exists", "files"}
    if (not isinstance(data, dict) or set(data) != required or type(data.get("schema")) is not int
            or data.get("schema") != 1 or type(data.get("old_exists")) is not bool):
        raise RecoveryError("transaction journal fields are invalid")
    if not isinstance(data["files"], list):
        raise RecoveryError("transaction journal file list is invalid")
    return data


def _ensure_existing_directories(root_fd: int, components: tuple[str, ...]) -> int:
    current = os.dup(root_fd)
    try:
        for name in components:
            nxt = _open_directory_at(current, name)
            os.close(current)
            current = nxt
        return current
    except BaseException:
        os.close(current)
        raise


def _open_relative_file(root_fd: int, relative: str, max_path_chars: int = 240) -> int:
    parts = validate_relative_path(relative, max_path_chars)
    parent = _ensure_existing_directories(root_fd, parts[:-1])
    try:
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            os.close(fd)
            raise IntegrityError(f"installed path is not a regular file: {relative}")
        return fd
    finally:
        os.close(parent)


def _hash_fd(fd: int, expected_size: Optional[int] = None) -> tuple[int, str]:
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    total = 0
    while True:
        block = os.read(fd, 1024 * 1024)
        if not block:
            break
        total += len(block)
        digest.update(block)
        if expected_size is not None and total > expected_size:
            break
    return total, digest.hexdigest()


def _inventory_tree(root_fd: int, prefix: str = "") -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    for name in os.listdir(root_fd):
        st = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        relative = f"{prefix}/{name}" if prefix else name
        if stat.S_ISLNK(st.st_mode):
            raise IntegrityError(f"installed tree contains a symlink: {relative}")
        if stat.S_ISDIR(st.st_mode):
            directories.add(relative)
            child_fd = _open_directory_at(root_fd, name)
            try:
                child_files, child_dirs = _inventory_tree(child_fd, relative)
                files.update(child_files)
                directories.update(child_dirs)
            finally:
                os.close(child_fd)
        elif stat.S_ISREG(st.st_mode):
            files.add(relative)
        else:
            raise IntegrityError(f"installed tree contains a special filesystem object: {relative}")
    return files, directories


def _verify_tree(parent_fd: int, target_name: str, records: tuple[FileRecord, ...], max_path_chars: int = 240) -> bool:
    try:
        root_fd = _open_directory_at(parent_fd, target_name)
    except (FileNotFoundError, OSError, TransactionError):
        return False
    try:
        expected_files = {record.path for record in records}
        expected_directories: set[str] = set()
        for record in records:
            parts = record.path.split("/")
            for depth in range(1, len(parts)):
                expected_directories.add("/".join(parts[:depth]))
        try:
            actual_files, actual_directories = _inventory_tree(root_fd)
        except (OSError, TransactionError):
            return False
        if actual_files != expected_files or actual_directories != expected_directories:
            return False
        for record in records:
            try:
                fd = _open_relative_file(root_fd, record.path, max_path_chars)
            except (OSError, TransactionError):
                return False
            try:
                size, digest = _hash_fd(fd, record.size)
            finally:
                os.close(fd)
            if size != record.size or digest != record.sha256:
                return False
        return True
    finally:
        os.close(root_fd)


def _cleanup_tree_at(parent_fd: int, name: str, expected_device: Optional[int] = None) -> None:
    """Remove a tree without following symlinks or traversing mounted filesystems."""
    st = _lstat_at(parent_fd, name)
    if st is None:
        return
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
        os.unlink(name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        return
    if expected_device is not None and st.st_dev != expected_device:
        raise TransactionError("refusing to remove a directory on another filesystem")
    child_fd = _open_directory_at(parent_fd, name)
    try:
        child_st = os.fstat(child_fd)
        if expected_device is not None and child_st.st_dev != expected_device:
            raise TransactionError("refusing to traverse a mounted directory")
        for entry in os.listdir(child_fd):
            entry_st = _lstat_at(child_fd, entry)
            if entry_st is None:
                continue
            if stat.S_ISDIR(entry_st.st_mode) and not stat.S_ISLNK(entry_st.st_mode):
                _cleanup_tree_at(child_fd, entry, child_st.st_dev)
            else:
                os.unlink(entry, dir_fd=child_fd)
    finally:
        os.close(child_fd)
    os.rmdir(name, dir_fd=parent_fd)
    os.fsync(parent_fd)


class TransactionEngine:
    """Stage a full immutable release, then swap the directory with recovery.

    This backend is POSIX-only and requires O_NOFOLLOW + dir_fd. It deliberately
    refuses Windows rather than emulating safe operations with racy Path calls.
    """
    def __init__(
        self,
        install_dir: Path,
        *,
        max_files: int = 10000,
        max_total_bytes: int = 64 * 1024 * 1024 * 1024,
        max_path_chars: int = 240,
        min_free_bytes: int = 64 * 1024 * 1024,
        chunk_size: int = 1024 * 1024,
        fault_hook: Optional[Callable[[str], None]] = None,
    ) -> None:
        _require_posix_primitives()
        self.install_dir = Path(install_dir)
        if not self.install_dir.is_absolute() or self.install_dir.name in ("", ".", ".."):
            raise TransactionError("install_dir must be an absolute dedicated directory path")
        if any(part in (".", "..") for part in self.install_dir.parts):
            raise TransactionError("install_dir may not contain dot components")
        validate_relative_path(self.install_dir.name, 255)
        for name, value in (("max_files", max_files), ("max_total_bytes", max_total_bytes), ("max_path_chars", max_path_chars), ("min_free_bytes", min_free_bytes), ("chunk_size", chunk_size)):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self.max_files = max_files
        self.max_total_bytes = max_total_bytes
        self.max_path_chars = max_path_chars
        self.min_free_bytes = min_free_bytes
        self.chunk_size = chunk_size
        self.fault_hook = fault_hook
        self.parent_path = self.install_dir.parent
        self.target_name = self.install_dir.name
        self.name_prefix = f".{self.target_name}.launchforge-"
        self.stage_prefix = self.name_prefix + "stage-"
        self.backup_prefix = self.name_prefix + "backup-"
        self.journal_prefix = self.name_prefix + "journal-"
        self.lock_name = self.name_prefix + "lock"

    @contextmanager
    def _locked_parent(self) -> Iterator[int]:
        parent_fd = _open_absolute_directory(self.parent_path)
        lock_fd = -1
        try:
            parent_stat = os.fstat(parent_fd)
            if parent_stat.st_uid != os.getuid() or (parent_stat.st_mode & 0o022):
                raise TransactionError("install parent must be owned by this user and not group/world writable")
            lock_fd = os.open(self.lock_name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
            lock_stat = os.fstat(lock_fd)
            if not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_uid != os.getuid() or (lock_stat.st_mode & 0o077):
                raise TransactionError("transaction lock is not a private regular file owned by this user")
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            yield parent_fd
        finally:
            if lock_fd >= 0:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)
            os.close(parent_fd)

    def install(self, game_id: str, version: str, artifacts: Iterable[Artifact], *, progress=None, phase=None, cancelled=None) -> InstallResult:
        return self._apply("install", game_id, version, artifacts, require_existing=False, progress=progress, phase=phase, cancelled=cancelled)

    def update(self, game_id: str, version: str, artifacts: Iterable[Artifact], *, progress=None, phase=None, cancelled=None) -> InstallResult:
        return self._apply("update", game_id, version, artifacts, require_existing=True, progress=progress, phase=phase, cancelled=cancelled)

    def repair(self, game_id: str, version: str, artifacts: Iterable[Artifact], *, progress=None, phase=None, cancelled=None) -> InstallResult:
        return self._apply("repair", game_id, version, artifacts, require_existing=True, progress=progress, phase=phase, cancelled=cancelled)

    def _apply(self, action: str, game_id: str, version: str, artifacts: Iterable[Artifact], require_existing: bool, *, progress=None, phase=None, cancelled=None) -> InstallResult:
        if not isinstance(game_id, str) or not game_id or len(game_id) > 128:
            raise TransactionError("game_id is invalid")
        if not isinstance(version, str) or not version or len(version) > 128:
            raise TransactionError("release version is invalid")
        artifact_items = tuple(artifacts)
        records = _validate_records((a.record for a in artifact_items), self.max_files, self.max_total_bytes, self.max_path_chars)
        total_bytes = sum(record.size for record in records)

        with self._locked_parent() as parent_fd:
            self._recover_locked(parent_fd)
            target_stat = _lstat_at(parent_fd, self.target_name)
            existing = target_stat is not None
            if existing and (not stat.S_ISDIR(target_stat.st_mode) or stat.S_ISLNK(target_stat.st_mode)):
                raise TransactionError("install target exists but is not a real directory")
            if existing and (target_stat.st_uid != os.getuid() or (target_stat.st_mode & 0o022)):
                raise TransactionError("existing install directory must be owned by this user and not group/world writable")
            if require_existing and not existing:
                raise TransactionError(f"cannot {action}: no installation exists")
            if not require_existing and existing:
                raise TransactionError("cannot install: target already exists; use update or repair")
            statvfs = os.fstatvfs(parent_fd)
            free = statvfs.f_bavail * statvfs.f_frsize
            if free < total_bytes + self.min_free_bytes:
                raise TransactionError("insufficient free space for staged release and safety reserve")

            token = uuid.uuid4().hex
            stage_name = self.stage_prefix + token
            backup_name = self.backup_prefix + token
            journal_name = self.journal_prefix + token + ".json"
            os.mkdir(stage_name, 0o700, dir_fd=parent_fd)
            os.fsync(parent_fd)
            stage_fd = _open_directory_at(parent_fd, stage_name)
            try:
                bytes_written = 0
                for artifact in artifact_items:
                    bytes_written += self._stage_artifact(stage_fd, artifact, progress=progress, progress_before=bytes_written, total_bytes=total_bytes, cancelled=cancelled)
                if cancelled and cancelled():
                    raise TransactionError("operation cancelled before commit")
                os.fsync(stage_fd)
            except BaseException:
                os.close(stage_fd)
                _cleanup_tree_at(parent_fd, stage_name)
                raise
            os.close(stage_fd)

            journal = {
                "schema": 1,
                "transaction": token,
                "target": self.target_name,
                "stage": stage_name,
                "backup": backup_name,
                "game_id": game_id,
                "version": version,
                "old_exists": existing,
                "files": [{"path": r.path, "size": r.size, "sha256": r.sha256} for r in records],
            }
            _write_journal(parent_fd, journal_name, journal)

            try:
                if phase:
                    phase("committing")
                if self.fault_hook:
                    self.fault_hook("before_swap")
                if existing:
                    if _lstat_at(parent_fd, backup_name) is not None:
                        raise TransactionError("random backup destination already exists")
                    os.rename(self.target_name, backup_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                    os.fsync(parent_fd)
                    if self.fault_hook:
                        self.fault_hook("after_old_moved")
                os.rename(stage_name, self.target_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                os.fsync(parent_fd)
                if self.fault_hook:
                    self.fault_hook("after_new_moved")
                if phase:
                    phase("verifying")
                if not _verify_tree(parent_fd, self.target_name, records, self.max_path_chars):
                    raise IntegrityError("committed installation failed post-swap verification")
                if self.fault_hook:
                    self.fault_hook("after_commit_verified")
                if existing:
                    _cleanup_tree_at(parent_fd, backup_name, os.fstat(parent_fd).st_dev)
                os.unlink(journal_name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except Exception:
                # Regular errors are recovered synchronously. BaseException
                # (KeyboardInterrupt/process termination) leaves the journal.
                self._recover_locked(parent_fd)
                raise
            return InstallResult(action=action, version=version, bytes_written=bytes_written, file_count=len(records))

    def _stage_artifact(self, stage_fd: int, artifact: Artifact, *, progress=None, progress_before=0, total_bytes=0, cancelled=None) -> int:
        record = artifact.record
        parts = validate_relative_path(record.path, self.max_path_chars)
        parent = _ensure_directories(stage_fd, parts[:-1])
        try:
            source_fd = _open_absolute_regular_file(Path(artifact.source))
            try:
                dest_fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            except BaseException:
                os.close(source_fd)
                raise
            try:
                source_stat = os.fstat(source_fd)
                if source_stat.st_size != record.size:
                    raise IntegrityError(f"artifact size changed or does not match metadata: {record.path}")
                digest = hashlib.sha256()
                total = 0
                while True:
                    if cancelled and cancelled():
                        raise TransactionError("operation cancelled while staging")
                    block = os.read(source_fd, self.chunk_size)
                    if not block:
                        break
                    total += len(block)
                    if total > record.size or total > self.max_total_bytes:
                        raise IntegrityError(f"artifact exceeds declared size: {record.path}")
                    digest.update(block)
                    _write_all(dest_fd, block)
                    if progress:
                        progress(progress_before + total, total_bytes)
                os.fsync(dest_fd)
                if total != record.size or digest.hexdigest() != record.sha256:
                    raise IntegrityError(f"artifact hash or size mismatch: {record.path}")
                os.fsync(parent)
                return total
            finally:
                os.close(source_fd)
                os.close(dest_fd)
        finally:
            os.close(parent)

    def verify(self, records: Iterable[FileRecord]) -> bool:
        validated = _validate_records(records, self.max_files, self.max_total_bytes, self.max_path_chars)
        with self._locked_parent() as parent_fd:
            return _verify_tree(parent_fd, self.target_name, validated, self.max_path_chars)

    def recover(self) -> RecoveryReport:
        with self._locked_parent() as parent_fd:
            return self._recover_locked(parent_fd)

    def _recover_locked(self, parent_fd: int) -> RecoveryReport:
        names = set(os.listdir(parent_fd))
        journal_names = sorted(name for name in names if name.startswith(self.journal_prefix) and name.endswith(".json"))
        seen = 0
        recovered = 0
        known_stages: set[str] = set()
        known_backups: set[str] = set()

        for journal_name in journal_names:
            journal_st = _lstat_at(parent_fd, journal_name)
            if (journal_st is None or not stat.S_ISREG(journal_st.st_mode) or stat.S_ISLNK(journal_st.st_mode)
                    or journal_st.st_uid != os.getuid() or (journal_st.st_mode & 0o077)):
                raise RecoveryError("transaction journal is not a private regular file owned by this user")
            journal = _read_journal(parent_fd, journal_name)
            token = journal_name[len(self.journal_prefix):-5]
            expected_stage = self.stage_prefix + token
            expected_backup = self.backup_prefix + token
            if journal["transaction"] != token or journal["target"] != self.target_name or journal["stage"] != expected_stage or journal["backup"] != expected_backup:
                raise RecoveryError("transaction journal identity or sibling names are invalid")
            if not re.fullmatch(r"[0-9a-f]{32}", token):
                raise RecoveryError("transaction token is malformed")
            if (not isinstance(journal["game_id"], str) or not journal["game_id"] or len(journal["game_id"]) > 128
                    or not isinstance(journal["version"], str) or not journal["version"] or len(journal["version"]) > 128):
                raise RecoveryError("transaction journal release identity is invalid")
            records = _validate_records(
                (FileRecord(x.get("path"), x.get("size"), x.get("sha256")) for x in journal["files"] if isinstance(x, dict)),
                self.max_files,
                self.max_total_bytes,
                self.max_path_chars,
            )
            if len(records) != len(journal["files"]):
                raise RecoveryError("transaction journal contains malformed file records")
            stage_name = expected_stage
            backup_name = expected_backup
            known_stages.add(stage_name)
            known_backups.add(backup_name)
            target = _lstat_at(parent_fd, self.target_name)
            stage = _lstat_at(parent_fd, stage_name)
            backup = _lstat_at(parent_fd, backup_name)
            for label, item in (("target", target), ("stage", stage), ("backup", backup)):
                if item is not None and (not stat.S_ISDIR(item.st_mode) or stat.S_ISLNK(item.st_mode)):
                    raise RecoveryError(f"{label} entry became a symlink or non-directory")
                if item is not None and label in ("stage", "backup") and (item.st_uid != os.getuid() or (item.st_mode & 0o022)):
                    raise RecoveryError(f"{label} directory is not private and owned by this user")

            seen += 1
            if journal["old_exists"]:
                if target is None and backup is not None:
                    # Crash after moving old target to backup, before installing new.
                    os.rename(backup_name, self.target_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                    os.fsync(parent_fd)
                    if stage is not None:
                        _cleanup_tree_at(parent_fd, stage_name, os.fstat(parent_fd).st_dev)
                elif target is not None and backup is not None and stage is None:
                    # New tree was renamed into place. Finalize if intact; otherwise rollback.
                    if _verify_tree(parent_fd, self.target_name, records, self.max_path_chars):
                        _cleanup_tree_at(parent_fd, backup_name, os.fstat(parent_fd).st_dev)
                    else:
                        os.rename(self.target_name, stage_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                        os.rename(backup_name, self.target_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                        os.fsync(parent_fd)
                        _cleanup_tree_at(parent_fd, stage_name, os.fstat(parent_fd).st_dev)
                elif target is not None and backup is None and stage is not None:
                    # The old tree was never moved; discard the uncommitted stage.
                    _cleanup_tree_at(parent_fd, stage_name, os.fstat(parent_fd).st_dev)
                elif target is not None and backup is None and stage is None:
                    # Commit and backup deletion completed; journal deletion was interrupted.
                    if not _verify_tree(parent_fd, self.target_name, records, self.max_path_chars):
                        raise RecoveryError("target is not the journaled release and no backup remains")
                elif target is not None and backup is not None and stage is not None:
                    raise RecoveryError("unexpected target appeared while both stage and backup exist")
                else:
                    raise RecoveryError("transaction is missing its target and recoverable backup")
            else:
                if backup is not None:
                    raise RecoveryError("first-install transaction unexpectedly has a backup")
                if target is None and stage is not None:
                    # First install never reached the swap.
                    _cleanup_tree_at(parent_fd, stage_name, os.fstat(parent_fd).st_dev)
                elif target is not None and stage is None:
                    if not _verify_tree(parent_fd, self.target_name, records, self.max_path_chars):
                        # No previous installation existed; quarantine and remove the invalid candidate.
                        os.rename(self.target_name, stage_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                        os.fsync(parent_fd)
                        _cleanup_tree_at(parent_fd, stage_name, os.fstat(parent_fd).st_dev)
                elif target is not None and stage is not None:
                    raise RecoveryError("unexpected target appeared during first-install recovery")
                # target and stage both missing means cleanup had already removed the stage.

            try:
                os.unlink(journal_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            os.fsync(parent_fd)
            recovered += 1

        # A crash before journal publication can leave a stage dir or temp journal.
        # The install lock guarantees no live operation owns these while recovering.
        for name in sorted(names):
            if name.startswith(self.stage_prefix) and name not in known_stages:
                st = _lstat_at(parent_fd, name)
                if st is not None:
                    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
                        raise RecoveryError("orphan stage entry is not a real directory")
                    _cleanup_tree_at(parent_fd, name, os.fstat(parent_fd).st_dev)
            elif name.startswith(self.journal_prefix) and name.endswith(".json.tmp"):
                st = _lstat_at(parent_fd, name)
                if st is not None:
                    os.unlink(name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
        # Never discard an orphan backup: it may be the only copy of a valid game.
        for name in names:
            if name.startswith(self.backup_prefix) and name not in known_backups and _lstat_at(parent_fd, name) is not None:
                raise RecoveryError("orphan backup found without its transaction journal; manual recovery required")
        return RecoveryReport(transactions_seen=seen, transactions_recovered=recovered)
