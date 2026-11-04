# Game installation transaction v1 (prototype proposal)

> **Status: proposed prototype contract, not approved for production.** This branch demonstrates 4.2 without changing shared schemas or the missing Runtime API. The implementation is POSIX-only; Windows must use the approved native host contract and handle-relative Win32 operations before this can ship.

## Scope

The transaction engine consumes a complete set of already downloaded artifacts. A caller is responsible for authenticating the publisher manifest and obtaining the artifacts through the bounded downloader. The engine treats each source file as untrusted again: it opens it without following symlinks, requires a regular file, copies it into a fresh staging directory, and recomputes its exact size and SHA-256 while copying.

The install directory is dedicated to immutable program files. Save games, settings, caches and mutable user/publisher data must be placed in a separate user-data directory. A release replaces the complete install directory; extra/unmanifested files are not preserved.

## Proposed inputs

    FileRecord(path: str, size: int, sha256: str)
    Artifact(record: FileRecord, source: Path)
    TransactionEngine(install_dir: absolute Path, limits...)

    engine.install(game_id, version, artifacts, progress, phase, cancelled)
    engine.update(game_id, version, artifacts, progress, phase, cancelled)
    engine.repair(game_id, version, artifacts, progress, phase, cancelled)
    engine.verify(records) -> bool
    engine.recover() -> RecoveryReport

artifacts_from_verified_manifest(manifest, verified_downloads) is a structural adapter for the output shape proposed by Phase 4.1. It does not authenticate the manifest itself. The input manifest must already have passed signature verification and every download source must have passed the 4.1 downloader's size/hash checks. The transaction engine verifies source hashes again during the copy.

## Transaction algorithm

1. Acquire an exclusive per-install OS file lock in the trusted parent directory.
2. Recover any previously journaled operation before accepting new work.
3. Validate all destination paths, case-fold/Unicode collisions, file/directory prefix collisions, file count, per-release total bytes and the free-space safety reserve.
4. Create a random, private staging directory as a sibling of the target. The staging directory is on the same filesystem as the current install.
5. Copy each source to a newly created destination using directory file descriptors and no-follow opens. Rehash every byte, fsync each file and the containing directories, and honor cancellation only during this stage.
6. Publish and fsync a bounded transaction journal in the same parent directory.
7. For an update/repair, atomically rename the old install to a unique backup sibling and fsync the parent directory.
8. Atomically rename the staged release to the install name and fsync the parent directory.
9. Inventory the complete installed tree; reject extra files, symlinks, special filesystem objects, and missing/changed files. Recompute every declared SHA-256.
10. Delete the old backup using no-follow recursive deletion, then delete the journal and fsync the parent.

The stage, backup, target and journal are siblings, so the two directory swaps are same-filesystem renames in one parent directory. The previous install is never deleted before the replacement is verified. A normal exception invokes recovery synchronously. A process interruption leaves the journal and sibling directories for recovery on the next startup.

## Recovery cases

| Observed state | Recovery action |
|---|---|
| Old target present; stage present; no backup | Original was not moved; discard stage. |
| Target absent; backup present; stage present | Restore backup to target; discard stage. |
| Target present; backup present; stage absent | Verify target. Finalize by deleting backup if valid; otherwise move candidate aside and restore backup. |
| Target present; no backup; no stage | Treat as a completed commit only if target exactly matches the journal. |
| First install; target absent; stage present | Discard uncommitted stage. |
| First install; target present; stage absent | Keep only if target exactly matches the journal; otherwise quarantine/remove the invalid new install. |
| Backup exists without its journal | Fail closed and require manual recovery; never delete the only possible valid copy automatically. |
| Journal, stage, backup or target has unexpected type/symlink/identity | Fail closed without following the link. |

A test hook simulates interruption at each rename/verification boundary. These tests exercise recovery logic but are not a substitute for power-loss testing on supported Windows filesystems.

## Filesystem security rules in the prototype

- Refuses platforms lacking O_NOFOLLOW, O_DIRECTORY, dir_fd operations, or flock; no path-based fallback is used.
- Walks every component of the absolute parent path from /, opening each component as a directory with O_NOFOLLOW.
- Requires the install parent to be owned by the current user and not group/world writable; lock file must be regular, private, and user-owned.
- Opens source files without following symlinks and requires regular files.
- Creates new destination files with O_EXCL|O_NOFOLLOW; directory creation/open is relative to trusted directory descriptors.
- Checks Windows-invalid path names, device names, trailing dots/spaces, reserved ADS syntax, Unicode normalization, case-fold collisions, and path-prefix conflicts before writes.
- Verifies the entire installed tree, not only declared files; symlinks, hard-linked files, extra files, and special objects cause verification failure.
- Removes backups/stages without following symlinks or traversing another mounted filesystem.
- Uses a size/count quota and checks available space plus a caller-configured safety reserve; write-time ENOSPC still fails before commit.

## Production blockers

1. Implement and review the Windows backend with handle-relative file operations, FILE_FLAG_OPEN_REPARSE_POINT, reparse-tag checks, safe rename/delete semantics and explicit ACL policy. Python POSIX tests do not prove Windows junction/reparse-point safety.
2. Confirm the selected Runtime language/host and port this code; no shared language/toolchain is frozen in main.
3. Approve install-root selection, parent ownership/ACL policy, user-data separation, lock behavior and multi-volume behavior.
4. Approve journal schema/versioning, anti-rollback/current-version state, cleanup retention and manual recovery UX.
5. Agree the Phase 4.1-to-4.2 adapter and error/progress types. The current manifest proposal has no signed executable-permission metadata; a portable target must decide whether an executable attribute belongs in the signed manifest.
6. Perform Windows interruption/power-loss testing on the supported filesystem, including antivirus/file-lock behavior and concurrent processes.

This contract is not permission to distribute managed game operations until the Windows implementation and adversarial gate pass.
