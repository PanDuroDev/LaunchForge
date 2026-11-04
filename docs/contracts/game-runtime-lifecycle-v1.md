# Game lifecycle API v1 (prototype proposal)

> **Status: adapter proposal only.** No approved Phase 1 Runtime API, renderer event contract, or native process policy is present on main. This document is an integration proposal, not a shared contract change.

## Operations

The prototype exposes synchronous calls over an injected transaction engine:

- install(game_id, version, verified_artifacts)
- update(game_id, version, verified_artifacts)
- repair(game_id, version, verified_artifacts)
- apply_verified_manifest(action, verified_manifest, provider) to acquire signed-manifest files, report download progress/cancellation, map them into transaction artifacts, and clean temporary downloads after staging
- verify(game_id, version, manifest_file_records) -> bool
- launch(game_id, version, manifest_file_records, LaunchConfig, LauncherAdapter)
- cancel() for an operation currently staging files
- process_exited(exit_code) called by the native Runtime when a process handle exits

Download/acquisition is separated behind VerifiedArtifactProvider. BoundedDownloaderProvider is a structural adapter for the Phase 4.1 downloader's download(entry, temp_dir, cancelled, progress) method; it refuses non-private or symlink-containing temp-directory paths, requires one returned artifact per declared manifest path, and removes its own temporary files after use. The manifest-to-artifact mapper does not authenticate the manifest: it accepts only an already signature-verified 4.1 result. The transaction engine independently reopens and rehashes every source while staging it.

## State model

idle -> downloading -> staging -> committing -> verifying -> installed -> ready -> launching -> running -> ready

downloading is present only when apply_verified_manifest uses a provider; direct install/update/repair calls begin at staging.

Errors and cancellations are terminal for an operation: error or cancelled. The snapshot includes an operation ID, game ID, version, bytes complete/total, message and an error code. Byte progress is emitted while staging; the commit phase is intentionally non-cancellable because interruption safety is provided by the transaction journal/recovery algorithm.

Proposed error codes should be standardized with the Runtime owner: manifest_untrusted, download_failed, integrity_mismatch, storage_limit, insufficient_space, cancelled, transaction_recovery_required, install_path_unsafe, launch_not_declared, launch_blocked, and process_start_failed.

## Launch boundary

LauncherAdapter.launch(installation_root, executable_relative, expected_sha256, arguments) is a protocol only. The prototype never invokes a shell or directly spawns a process.

The native Runtime implementation must:

- accept only an executable path present in the verified release manifest;
- reopen the executable handle-relatively under the trusted install root and reject symlinks/reparse points;
- verify or otherwise bind the executable file handle to the expected SHA-256 immediately before process creation;
- pass arguments as an argument vector, never through a shell string;
- apply the approved process permissions, working-directory policy, environment policy and Windows Job Object/lifecycle behavior;
- return a process handle and report process exit through process_exited.

The controller validates the executable is declared and bounds argument count/length/NULs, but the actual process creation and race-resistant launch check are intentionally left to the native host.

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

- Phase 1 Runtime host/lifecycle/process contract and event threading policy.
- Approved UI state/event registry.
- Native Windows filesystem and process-launch implementation.
- Accepted Phase 4.1 manifest/download result types and cancellation/progress interfaces.
- Runtime version compatibility and error-code ownership.
