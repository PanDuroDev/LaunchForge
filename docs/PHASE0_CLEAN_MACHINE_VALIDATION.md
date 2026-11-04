# Phase 0 clean-machine validation procedure

## Purpose and boundary

This procedure closes one specific Phase 0 evidence gap: checking that the portable Tauri spike can be launched by a standard user on a fresh Windows x64 machine, without Studio, Node.js, Rust, or build tools.

It consumes the portable ZIP produced by the Phase 0 Windows spike workflow in PR #16. It does not change the proposed project schema, renderer API, Runtime API, build contract, or selected stack. It is a validation helper, not a production installer or an approval of the Phase 0 candidate.

The portable spike does **not** bundle Microsoft Edge WebView2 Runtime. WebView2 is a prerequisite and must be recorded separately. A missing runtime is a failed clean-machine prerequisite, not a reason to silently install or download anything during this test.

## Required test machine

Use a fresh Windows 10/11 x64 VM matching the project's ultimately approved support baseline. The support baseline is not yet frozen, so record the exact OS build.

Run the test from a standard, non-elevated user session. Do not install LaunchForge Studio, Node.js, npm, Rust, Cargo, or Visual Studio Build Tools. Record whether those tools are present anyway. Record the WebView2 Runtime version and display scale.

The machine should have no prior LaunchForge files or state. Start from a clean VM snapshot for each independent run. Do not use the Windows GitHub Actions runner as a substitute for this fresh-user test.

## Obtain the candidate package

1. Open PR #16 and its Checks/Actions run history.
2. Select a successful run of the Phase 0 Windows spike workflow.
3. Download the **launchforge-phase0-windows-portable** artifact. GitHub Actions provides this artifact as an outer ZIP archive.
4. Extract the outer archive into a temporary working directory. It contains the inner **LaunchForge-Phase0-Portable.zip** produced by the workflow.
5. Keep the extracted inner ZIP unchanged. Record the inner ZIP's SHA-256 before testing; pass this inner ZIP to the verifier.

If the workflow did not upload an artifact, the clean-machine test cannot start. The run must first complete the build, smoke, packaging, and upload steps.

## Run the verifier

From a non-elevated PowerShell session, run:

    .\scripts\verify-phase0-portable.ps1 -PackageZip .\LaunchForge-Phase0-Portable.zip -OutputPath .\phase0-clean-machine-report.json

The script:

- Rejects unsafe ZIP paths, traversal entries, symlinks, duplicate destinations, and archives that exceed the entry/expanded-size limits.
- Requires the spike executable, build metadata, and reviewed Cargo.lock.
- Checks the schema/build metadata, asset manifest digests, and application-icon reference.
- Records the ZIP and executable SHA-256, compressed/extracted size, OS, CPU, RAM, and developer-tool presence.
- Requires a standard non-elevated user and an installed WebView2 Runtime.
- Launches the executable, waits for a LaunchForge main window, and verifies that the process remains alive during the smoke interval.
- Writes a JSON report even when validation fails.

A successful process/window check is not a first-usable-frame measurement. The script labels the startup result as startup-to-window-handle time to avoid overstating what it measures.

The verifier's **-ValidateOnly** switch is used only by its Windows CI unit tests. It validates archive safety and package metadata without attempting to launch the placeholder test executable.

## Manual evidence still required

The script does not prove the following Phase 0 acceptance items. Record each result separately rather than inferring it from a successful process launch:

| Area | Required evidence |
|---|---|
| Preview/export parity | Same fixture and renderer build; compare actual WebView2 screenshots and key interactions, not only source hashes or serialized HTML |
| DPI | Repeat at 100%, 150%, and 200% scale; record screenshots and any clipping/layout defects |
| Keyboard and focus | Navigate all visible controls with keyboard only; record focus visibility and usable activation behavior |
| Accessibility | Inspect accessible names/roles with Windows accessibility tools or a screen reader; record tool and version |
| Unicode/RTL | Verify representative Unicode text and Arabic/RTL layout in both preview and exported host |
| First usable frame | Instrument a renderer-ready marker; do not substitute the native window handle timestamp |
| CPU/memory | Use the dedicated process-tree measurement protocol with idle and fixed-interaction samples |
| Build/package | Record clean build time, compressed ZIP bytes, extracted bytes, and exact dependency/runtime policy |

The current Phase 0 candidate also needs its Windows workflow to upload the package successfully. A successful compile or window smoke test alone does not satisfy the clean-machine gate.

## Evidence to attach to the Phase 0 handoff

Attach:

- The unchanged portable ZIP and its SHA-256.
- **phase0-clean-machine-report.json**.
- OS build, VM configuration, CPU/RAM, display scale, and WebView2 version.
- Screenshots for preview/export at each tested display scale.
- Keyboard, focus, accessibility, Unicode/RTL observations.
- Raw performance samples and the exact scripts/commands used.
- A list of failed checks, environmental limitations, and the owner of each remaining risk.

Do not report Phase 0 as complete until the missing manual and clean-machine evidence is attached and reviewed. A waiver must name its owner, rationale, affected acceptance criterion, and residual risk.
