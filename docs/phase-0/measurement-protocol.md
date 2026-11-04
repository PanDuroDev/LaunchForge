# Phase 0 measurement protocol and current evidence

## Measurement rules

- Compare candidates only with the same sample project, target machine, display scale, power mode, and warm-up procedure.
- Do not combine unlike builds or report one synthetic performance score.
- Keep raw per-run observations, machine details, build settings, dependency versions, and command output.
- Report median and p95 for cold-start measurements; report idle and interaction CPU separately; report both compressed artifact and extracted directory size.
- State whether WebView2 is preinstalled/shared or packaged. Do not compare a Tauri/Evergreen package with a WebView2 Fixed Version package without calling out the dependency difference.
- Run accessibility, 100/150/200% DPI, keyboard, focus, Unicode, and RTL checks as functional gates, not as invented numeric scores.

## Candidate test matrix

| Metric | Procedure | Result in this execution |
|---|---|---|
| Cold start to first usable frame | 10 cold launches after reboot/logoff; instrument first rendered frame in app; report median/p95 | **Not measured**: no Windows desktop or built native host available |
| Idle / peak memory | Sample full app process tree after 60 s idle and during one fixed interaction | **Not measured** |
| CPU | Sample process-tree CPU for 60 s idle and during fixed interaction; normalize by logical processors | **Not measured** |
| Package size | Record installer/portable bytes and extracted bytes; identify shared WebView2 dependency | **Not measured** |
| Build time | Five clean builds after dependency cache policy is recorded; report median | **Not measured** |
| Clean-machine deployment | Fresh supported Windows VM without development tools; install/launch/uninstall | **Not measured** |
| Preview/export parity | Same fixture, renderer package hash, semantic output and browser screenshot comparison | Node contract/render output parity **passed**; WebView2 screenshot/interaction parity **not measured** |
| Accessibility / DPI | Keyboard-only path, focus visibility, screen-reader labels, Unicode, RTL, 100/150/200% scale | **Not measured** |

## Actual environment available to this run

- Runtime: Node.js `v22.16.0`; npm `10.9.0`; Python `3.13.5`.
- Rust compiler and Cargo: not installed in the local execution environment.
- Operating system: Linux container, not Windows; no WebView2 runtime or Windows desktop session was available.
- A Windows 2022 GitHub Actions job is included to build the Tauri host and perform a process/main-window smoke test. Its result is **pending** until the PR workflow completes; that runner is not a fresh end-user machine.
- npm registry access: unavailable during this run (`EAI_AGAIN` while resolving `registry.npmjs.org`). The Phase 0 PoC therefore has no external npm dependencies.

These are environment limitations, not candidate performance results. No startup, memory, CPU, build-time, or package-size values are claimed.

## Reproduction commands

From `poc/`:

```powershell
node --test tests/*.test.mjs
node scripts/build-export.mjs
python -m http.server 4173
```

Open `http://localhost:4173/preview.html` for the Studio-side renderer fixture. For the exported renderer package, serve `poc/dist/` on a separate local port and open `/index.html`. Do not open the HTML directly as `file://`; browser module and fetch behavior requires HTTP.

For build-time comparisons, run five clean target builds after dependencies are resolved and record each duration and toolchain version. For the native Windows gate, build the Tauri target on a clean Windows x64 VM, then use `scripts/measure-windows.ps1` with the produced executable and package directory. The script records process-tree CPU/memory, extracted package size, and startup-to-window-handle time. Capture a separate first-usable-frame marker from the actual renderer; the script's window-handle timing is only a process/window diagnostic and must not be reported as first-frame latency.

## Raw data status

No native raw measurement file is included because no native Windows build has yet been run in this execution. The first successful Windows Actions run should attach its build log and portable artifact; the clean-machine run must additionally attach the script JSON output, full machine/build manifest, screenshots, and observations to the Phase 0.3 handoff. Until then, Phase 0.3 is blocked and this PR must not be treated as a completed Phase 0 gate.
