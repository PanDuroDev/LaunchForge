# LaunchForge Phase 0 renderer spike

This spike tests one narrow architectural claim: preview and exported launcher can consume the same project fixture and the exact same renderer implementation without giving the renderer host privileges.

It is intentionally dependency-free. It is not the Studio editor, a Tauri build, or a distributable Windows launcher. The proposed production stack remains TypeScript/React for Studio UI with a host-neutral shared renderer hosted by Tauri/Rust. This spike isolates the shared project/renderer contract before adding a native shell.

## Layout

- `contracts/project-v1.schema.json`: machine-readable schema v1.
- `shared/contract.mjs`: bounded semantic validator for the spike.
- `shared/renderer.mjs`: pure renderer serializer plus delegated, allowlisted navigation handling.
- `shared/app.mjs`: common load/validate/mount path.
- `preview.html` + `preview.mjs`: Studio-side preview fixture.
- `runtime.html` + `runtime.mjs`: exported Runtime entry point.
- `fixtures/sample-project.json`: same project used by both paths.
- `scripts/build-export.mjs`: produces `dist/` using the exact shared source files.
- `tests/phase0.test.mjs`: schema/security and preview/export parity checks.

## Run
```sh
node --test tests/*.test.mjs
node scripts/build-export.mjs
python -m http.server 4173
```

Open `http://localhost:4173/preview.html`. To inspect the exported copy, start a second server with `python -m http.server 4174 --directory dist` and open `http://localhost:4174/`.

The two browser paths are intentionally served over HTTP so module loading and `fetch()` behave as they will in an embedded WebView.

## What the spike proves

- Schema v1 rejects unknown versions, duplicate IDs, unapproved component/action types, oversized project JSON, and unsafe asset paths.
- Text and attribute values are escaped before the renderer serializes them.
- Local game data resolves through a typed game ID binding.
- Preview and export call the same renderer module; the export script copies renderer, validator, and project bytes. Tests compare SHA-256 hashes and rendered output.
- The renderer receives project data and typed action callbacks (`navigate(target)` and `launchGame(gameId)`) only. The PoC does not execute a game process. It does not import Tauri or expose filesystem/process/network APIs.
- `src-tauri/` contains a no-command Tauri v2 shell; the Windows Actions workflow builds it and checks that the process creates a main window. That CI smoke test is not a fresh-user clean-machine install test.

## What it does not prove
- The local execution environment cannot compile the Tauri/Rust host. A Windows Actions job is configured to compile a portable executable, smoke-test its window, and upload an artifact; the result is pending until the workflow runs.
- No fresh-user clean-machine deployment is proved by the CI runner alone.
- No clean-machine WebView2 deployment, first-frame timing, memory, CPU, package-size, DPI, screen-reader, or RTL test is claimed.
- HTML serializer parity is not a substitute for screenshot/interaction parity in the final WebView host.

Do not treat a passing Node test run as Phase 0 completion. The outstanding native and clean-machine gate is documented in `docs/phase-0/measurement-protocol.md`.
