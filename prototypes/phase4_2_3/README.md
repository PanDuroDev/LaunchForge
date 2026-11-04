# LaunchForge Phase 4.2 / 4.3 prototype

**Prototype only; not integrated with Launcher Runtime.** This is a separate, self-contained handoff branch so it can be reviewed in parallel with the Phase 4.1 manifest/downloader PR. It defines small adapter seams rather than modifying shared Runtime contracts that do not exist on main.

## Phase 4.2: transactional installation

- Installs a complete immutable game-program directory from verified artifact files.
- Re-hashes each source while copying into a fresh sibling staging directory.
- Uses same-parent, same-filesystem directory renames; the old install remains in a backup sibling until the new tree has been fully re-verified.
- Publishes a bounded durable journal before the first rename; startup recovery infers transaction state from the journal plus target/stage/backup entries.
- Uses per-install flock, absolute parent-path walk from / with O_NOFOLLOW, directory file descriptors, openat-style relative operations, O_EXCL staging files, file/directory fsync, and no-follow recursive cleanup.
- Enforces file count, aggregate bytes, cross-platform destination path rules, and a free-space safety reserve. Cancellation is accepted during staging and disabled after commit begins.
- verify inventories the full tree and rejects extra files, symlinks, hard links and special filesystem objects, in addition to rechecking every declared hash.
- The install directory is dedicated to immutable program files. Save games/configuration must live in a separate user-data directory; full-directory replacement intentionally removes old extras.

## Phase 4.3: lifecycle boundary

GameLifecycleService exposes synchronous install/update/repair/verify/launch states with operation IDs, byte progress, cancellation, structured terminal errors and a narrow LauncherAdapter protocol. It rejects new delivery or verification work while a game process is launching or running; the native process-exit event releases that gate. An exit callback that races with launch_game returning is reconciled atomically, so an already-exited process is not published as RUNNING. It never calls subprocess or a shell. The native Runtime adapter must re-open the declared executable handle-relatively, validate the expected hash/reparse state, and launch with an argument vector under the approved process policy.

VerifiedArtifactProvider and BoundedDownloaderProvider form a narrow seam to the 4.1 BoundedDownloader interface without importing the still-unmerged 4.1 PR. The provider requires a user-owned temp directory inaccessible to group/other, maps exactly the manifest paths, forwards download progress/cancellation, and cleans provider-created temp files after staging. Every file is re-opened and rehashed by the transaction engine.

## Run

From this directory:

    python -m unittest discover -s tests -v
    python -m compileall -q launchforge_delivery tests

No third-party dependencies are required.

## Security boundary and limitations

- **POSIX prototype only.** The implementation fails closed on Windows because Python's portable path APIs cannot provide the required race-resistant Win32 reparse-point handling. Production Windows support must use an approved Rust/.NET host and handle-relative Win32 operations; no fallback to path-based resolve()/is_symlink() checks is acceptable.
- The install parent must be owned by the current user and not group/world writable. Its ancestors are opened component-by-component without following symlinks.
- The download temp directory must be private, owned by the current user, and inaccessible to group/other. Its complete path is opened component-by-component without following symlinks.
- The LauncherAdapter is an interface only and accepts a configured game ID, never a renderer-supplied executable path or command. The native Runtime resolves executable/arguments from host-owned configuration, validates the executable handle and expected manifest hash immediately before process creation, and owns argument/environment policy, graceful shutdown, process exit monitoring and Windows Job Object behavior.
- Phase 4.1 integration uses a structural adapter to avoid importing an unmerged PR. Manifest trust/bootstrap and network transport are not duplicated here; every source is hashed again when staged.
- It does not define an install location chooser, multi-volume migration, game save migration, ACL policy, key rotation/revocation, or anti-rollback state.
- The current Phase 4.1 manifest prototype does not specify executable permission metadata; the POSIX prototype creates files as private non-executable data. A portable/POSIX release needs a signed executable-attribute decision. Windows process launch and ACL semantics must be supplied by the approved native Runtime.
- Full-directory swap is not delta patching and only suits immutable program files, not saves or mutable publisher/user data.
