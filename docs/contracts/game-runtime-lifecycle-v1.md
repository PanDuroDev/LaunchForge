# Game lifecycle API v1 (prototype proposal)

> **Status: adapter proposal only.** No approved Phase 1 Runtime API, renderer event contract, or native process policy is present on main. This document is an integration proposal, not a shared contract change.

## Operations

The prototype exposes synchronous calls over an injected transaction engine:

- install(game_id, version, verified_artifacts)
- update(game_id, version, verified_artifacts)
- repair(game_id, version, verified_artifacts)
- apply_verified_manifest(action, verified_manifest, provider) to acquire signed-manifest files, report download progress/cancellation, map them into transaction artifacts, and clean temporary downloads after staging
- verify(game_id, version, manifest_file_records) -> bool
- launch(game_id, version, manifest_file_records, LauncherAdapter); the renderer/host action supplies a configured game ID only, never a path or arbitrary arguments
- cancel() for an operation currently staging files
- process_exited(exit_code) called by the native Runtime when a process handle exits. The callback may race with launch_game returning for a very short-lived process; the service records such an exit during LAUNCHING and publishes READY instead of a stale RUNNING state.

Download/acquisition is separated behind VerifiedArtifactProvider. BoundedDownloaderProvider is a structural adapter for the Phase 4.1 downloader's download(entry, temp_dir, cancelled, progress) method; it refuses non-private or symlink-containing temp-directory paths, requires one returned artifact per declared manifest path, and removes its own temporary files after use. The manifest-to-artifact mapper does not authenticate the manifest: it accepts only an already signature-verified 4.1 result. The transaction engine independently reopens and rehashes every source while staging it.

## State model

idle -> downloading -> staging -> committing -> verifying -> installed -> ready -> launching -> running -> ready

downloading is present only when apply_verified_manifest uses a provider; direct install/update/repair calls begin at staging.

Errors and cancellations are terminal for an operation: error or cancelled. The snapshot includes an operation ID, game ID, version, bytes complete/total, message and an error code. Byte progress is emitted while staging; the commit phase is intentionally non-cancellable because interruption safety is provided by the transaction journal/recovery algorithm. The lifecycle service rejects all new delivery/verification/launch operations while the game process is launching or running. An exit callback delivered concurrently while launch_game is still returning is recorded under the lifecycle lock and reconciled atomically with the process handle; the service does not publish RUNNING for a process already reported exited. The native Runtime must report process exit before an update, repair, verification, or second launch may begin.

Proposed error codes should be standardized with the Runtime owner: manifest_untrusted, download_failed, integrity_mismatch, storage_limit, insufficient_space, cancelled, transaction_recovery_required, install_path_unsafe, launch_not_declared, launch_blocked, and process_start_failed.

## Launch boundary

LauncherAdapter.launch_game(game_id) is a protocol only. The prototype never invokes a shell or directly spawns a process.

The native Runtime implementation must:

- expose only `launch_game(game_id)` to the lifecycle/renderer-facing interface; resolve the executable and launch arguments from host-owned configuration, never from UI-supplied paths or command strings;
- reopen the configured executable handle-relatively under the trusted install root and reject symlinks/reparse points;
- verify or otherwise bind the executable file handle to the approved manifest SHA-256 immediately before process creation;
- pass host-configured arguments as an argument vector, never through a shell string;
- apply the approved process permissions, working-directory policy, environment policy and Windows Job Object/lifecycle behavior;
- return a process handle and report process exit through process_exited. Exit monitoring may use a separate thread; the adapter must not assume launch_game always returns before an exit notification is delivered, and must deliver the terminal event once for the process it launched.

The lifecycle controller verifies the declared installed-file set, then passes only the game ID to the native host. The host must resolve the launch target from trusted project configuration, confirm that target belongs to the verified installed release, and perform the race-resistant handle validation immediately before launch.

## UI mapping proposal

| Runtime state | UI meaning | Typical action |
|---|---|---|
| downloading | Fetching and validating publisher artifacts | Cancel |
| staging | Preparing verified game files | Cancel |
| committing | Applying complete install/update | Disable cancellation; show indeterminate commit |
| verifying | Checking installed files | Wait / retry on failure |
| installed / ready | Playable installation | Play; Verify; Update |
| launching | Starting game process | Disable duplicate Play |
| running | Game process is active | Focus/close actions subject to Runtime policy |
| cancelled | Operation stopped before commit | Install/Update again |
| error | Operation failed with stable code and diagnostic message | Retry/Repair/Copy diagnostics |

Pause/resume and background scheduling are not implemented. The current service is synchronous. A production host must define thread dispatch, operation scheduling and whether a game can launch while another game operation is active.

## Integration blockers

- Phase 1 Runtime host/lifecycle/process contract and event threading policy. The production adapter must confirm its event-dispatch model and preserve one process-specific exit notification even when it races with launch_game.
- Approved UI state/event registry.
- Native Windows filesystem and process-launch implementation.
- Accepted Phase 4.1 manifest/download result types and cancellation/progress interfaces.
- Runtime version compatibility and error-code ownership.
