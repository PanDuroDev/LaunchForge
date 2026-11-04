"""Narrow adapter from a verified Phase 4.1 manifest/download result to 4.2.

Uses structural attributes on purpose: importing Phase 4.1 directly would make
this handoff branch unbuildable while PR #12 is still independent/unmerged.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Mapping

from .transaction import Artifact, FileRecord, TransactionError, UnsupportedPlatformError, validate_relative_path


def _require_private_temp_directory(path: Path) -> None:
    """Open every component without following links and require a private final dir."""
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise UnsupportedPlatformError("private temp-directory validation requires the approved POSIX backend")
    if not path.is_absolute() or any(part in (".", "..") for part in path.parts):
        raise TransactionError("download temp directory must be absolute and contain no dot components")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for component in path.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or (info.st_mode & 0o077)):
            raise TransactionError("download temp directory must be user-owned and inaccessible to group/other")
    except OSError as exc:
        raise TransactionError("download temp directory path contains an inaccessible or symlinked component") from exc
    finally:
        os.close(fd)


def artifacts_from_verified_manifest(manifest: object, verified_downloads: Mapping[str, Path]) -> tuple[Artifact, ...]:
    """Map signed manifest entries to verified temp files without trusting their paths.

    Contract: manifest must be the result of successful publisher-signature
    verification. verified_downloads maps each manifest path to a temp file
    returned only after size/hash verification. TransactionEngine reopens source
    files without following symlinks and hashes them again while staging.
    """
    files = getattr(manifest, "files", None)
    if not isinstance(files, (tuple, list)) or not files:
        raise TransactionError("verified manifest does not expose a non-empty files collection")
    expected: set[str] = set()
    artifacts: list[Artifact] = []
    for entry in files:
        try:
            relative = entry.path
            size = entry.size
            digest = entry.sha256
        except AttributeError as exc:
            raise TransactionError("manifest file entry lacks path/size/sha256") from exc
        validate_relative_path(relative)
        if relative in expected:
            raise TransactionError("manifest contains duplicate file destinations")
        expected.add(relative)
        source = verified_downloads.get(relative)
        if source is None:
            raise TransactionError(f"verified download is missing for {relative}")
        artifacts.append(Artifact(FileRecord(relative, size, digest), Path(source)))
    if set(verified_downloads) != expected:
        raise TransactionError("download mapping has missing or unexpected manifest destinations")
    return tuple(artifacts)


class BoundedDownloaderProvider:
    """Adapter for the Phase 4.1 BoundedDownloader without importing its module.

    downloader must implement the 4.1 download(entry, temporary_directory,
    cancelled=..., progress=...) interface. The temp directory must be private
    and owned by the current user. cleanup only unlinks names created/returned
    by this provider; it never recursively deletes the temp directory.
    """

    def __init__(self, downloader: object, temporary_directory: Path) -> None:
        self.downloader = downloader
        self.temporary_directory = Path(temporary_directory)
        _require_private_temp_directory(self.temporary_directory)
        self._last_paths: set[Path] = set()

    def acquire(self, verified_manifest: object, progress, cancelled) -> Mapping[str, Path]:
        files = getattr(verified_manifest, "files", None)
        if not isinstance(files, (tuple, list)) or not files:
            raise TransactionError("verified manifest does not expose a non-empty files collection")
        total = sum(entry.size for entry in files)
        completed = 0
        downloads: dict[str, Path] = {}
        self._last_paths = set()
        try:
            for entry in files:
                if cancelled():
                    raise TransactionError("download operation cancelled")

                def per_file_progress(done: int, expected: int) -> None:
                    if type(done) is not int or type(expected) is not int or expected != entry.size or done < 0 or done > expected:
                        raise TransactionError("downloader emitted invalid progress values")
                    progress(completed + done, total)

                path = Path(self.downloader.download(
                    entry,
                    self.temporary_directory,
                    cancelled=cancelled,
                    progress=per_file_progress,
                ))
                if (not path.is_absolute() or path.parent != self.temporary_directory
                        or not path.name.startswith("launchforge-download-") or path.is_symlink() or not path.is_file()):
                    raise TransactionError("downloader returned a path outside its private temp-file contract")
                downloads[entry.path] = path
                self._last_paths.add(path)
                completed += entry.size
                progress(completed, total)
            return downloads
        except Exception:
            self.cleanup(downloads)
            raise

    def cleanup(self, downloads: Mapping[str, Path]) -> None:
        for path in set(Path(value) for value in downloads.values()) | self._last_paths:
            if path.parent != self.temporary_directory or not path.name.startswith("launchforge-download-"):
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                # Leave an unremovable temp artifact for diagnostics; never recurse.
                pass
        self._last_paths.clear()
