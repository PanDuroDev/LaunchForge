# ADR-0001: Windows-first host and shared renderer

- **Status:** Candidate selected for Phase 0 validation; final acceptance is blocked on Windows packaging and clean-machine evidence.
- **Date:** 2026-11-04
- **Scope:** Phase 0 only. This decision does not authorize Phase 1 editor or launcher implementation.

## Context

LaunchForge needs a Windows-first Studio, a standalone exported launcher, a small privileged host surface, and one renderer/component implementation shared by Studio preview and export. The project plan explicitly shortlists Tauri + web UI, WebView2 + .NET, and Electron. Framework performance has not been measured in this repository and must not be inferred from marketing claims.

## Candidate comparison

| Candidate | Advantages for LaunchForge | Costs / risks | Decision |
|---|---|---|---|
| **Tauri v2 + TypeScript/React + Rust** | Rust host and service core; web UI can be reused; Windows WebView2 is supplied by the OS/runtime; granular capability configuration; no bundled full Chromium runtime in the default architecture | WebView2 availability/version policy; Tauri/Rust learning and build chain; command bridge must remain narrow; renderer still needs browser/DPI testing | **Selected candidate** |
| **WebView2 + .NET + TypeScript/React** | Direct Windows integration; mature .NET tooling and APIs; reuse the same web renderer; explicit control of WebView2 deployment | Windows-only; host/renderer bridge still needs a permission model; Evergreen relies on installed runtime and Fixed Version packaging adds more than 250 MB according to Microsoft | **Fallback** if Tauri fails a concrete Windows integration or packaging gate |
| **Electron + TypeScript/React** | Consistent bundled Chromium baseline; mature web ecosystem and straightforward web tooling; same component package can be reused | Bundles Chromium/Node-related runtime; larger update/security footprint; main/renderer IPC must be carefully constrained; more than is justified for a Windows-only MVP | **Not selected** unless a measured cross-machine browser consistency requirement outweighs package and maintenance costs |

These are architecture assessments, not benchmark results. Tauri documents its Rust + OS WebView architecture and small package rationale; its capability system scopes frontend access but does not make unsafe Rust commands safe. Microsoft documents Evergreen WebView2 as shared and auto-updated, while Fixed Version places the runtime in the package and adds more than 250 MB. Electron's own security guidance requires sandboxing, context isolation, restrictive content policy, and validated IPC. See references below.

## Decision

Use the following implementation direction for the MVP, subject to Phase 0.3 Windows evidence:

- **Studio UI:** TypeScript + React. Editor state and authoring workflows remain in the UI layer; the UI does not own privileged OS access.
- **Studio host:** Tauri v2 with Rust. Expose only purpose-built, typed commands. No generic filesystem, shell, process, or unrestricted network command.
- **Shared renderer:** a renderer-neutral project model plus one web renderer/component package. Studio preview and exported Runtime must import the same renderer implementation and the same component definitions. The renderer package must not import Tauri APIs.
- **Runtime/core:** Rust for project loading/validation, capability checks, configured local-game launch, safe asset resolution, and bounded OS services. Keep host APIs narrow and versioned.
- **Build tooling:** a deterministic Rust CLI/library boundary invoked by Studio. Build decisions and validation must not be hidden in React components.
- **First production renderer:** web renderer hosted by Tauri's Windows WebView2. The project schema does not permanently select the host; target selection occurs during export. No second production renderer in the MVP.
- **Fallback:** WebView2 + .NET host, reusing the same web renderer and schema. Do not fork the component implementation.

The Phase 0 spike in `poc/` proves the renderer contract with a dependency-free shared DOM rendering module and includes a minimal no-command Tauri host plus a Windows CI build/smoke-test job. It is deliberately not presented as proof that the production React editor or fresh-user clean-machine installation already work.

## Responsibility map

| Layer | Language / technology | Owns | Must not own |
|---|---|---|---|
| Studio editor UI | TypeScript + React | Editing state, component tree, inspector, user workflows, preview orchestration | Direct process execution, arbitrary filesystem access, private credentials |
| Privileged host | Rust + Tauri v2 | Window integration, approved OS commands, secure-storage adapter, app lifecycle | Component layout/rendering rules, arbitrary frontend-requested commands |
| Shared renderer | TypeScript/DOM first; host-neutral package | Component rendering, layout semantics, visual states, accessibility semantics | Host APIs, file reads outside supplied assets, arbitrary script evaluation |
| Runtime core | Rust | Project validation, safe path resolution, allowlisted game-launch service, diagnostics | Generic shell or unrestricted process/network API |
| Build/export | Rust CLI/library | Validation, asset closure, secret scan, renderer/runtime bundling, build manifest | UI state or undocumented side effects |
| Tests | Node test runner + Rust tests + Windows integration tests | Contract fixtures, renderer parity, hostile-input tests, packaging and clean-machine tests | Replacing actual Windows acceptance with Linux-only unit tests |

## Why Tauri is the leading candidate

The product is Windows-first, needs a web authoring surface, and does not yet have a requirement that justifies bundling a second browser engine. Tauri keeps the renderer independent from host commands and uses the system WebView. Its capability model provides a useful boundary for plugin permissions, but it is only one layer: each Rust command must still validate its arguments and enforce authorization itself.

WebView2/.NET remains a credible fallback because it uses the same web renderer and gives direct Windows control. It is not chosen by assumption that it is slower or faster. WebView2's Evergreen mode reduces per-app runtime duplication but allows browser updates to change the rendering baseline; Fixed Version makes that baseline more deterministic at a documented package-size cost. The MVP should prefer Evergreen and test compatibility unless measured regressions require a pinned runtime.

Electron is not rejected as technically incapable. It is rejected as the default because LaunchForge has no current requirement for a bundled Chromium baseline that justifies its deployment and security maintenance costs. Electron's renderer can be safely constrained, but it still needs careful sandbox, context-isolation, CSP, navigation, and IPC design.

## Required proof before final approval

The following evidence is still outstanding and is a hard Phase 0.3 gate:

1. Complete the Windows CI Tauri build and inspect its artifact/logs.
2. Repeat the build on a clean Windows x64 user VM and verify WebView2 prerequisite behavior.
3. Run the exported sample without Studio, Node, Rust, or other undeclared development dependencies.
4. Capture startup-to-first-usable-frame, idle/peak memory, idle/interaction CPU, build time, package size, and clean-machine result using a recorded machine/build configuration.
5. Verify keyboard navigation, focus, Unicode, RTL baseline, and 100/150/200% DPI behavior.
6. Confirm preview/export parity in the actual WebView2 host, not only in the host-neutral renderer tests.

No comparative benchmark number is asserted by this ADR. If Tauri fails one of these gates, record the failure and rerun the sample and protocol against WebView2/.NET. Do not add Electron or another renderer merely to keep comparisons going.

## Consequences

- React is an editor technology, not permission to run arbitrary user code in the launcher.
- The shared renderer package is host-neutral and consumed by preview and export.
- Renderer-dependent features are capability-checked; shared schema does not promise universal renderer portability.
- Tauri capabilities are configured by window label and kept minimal. Remote content is not allowed to call privileged host commands.
- The fallback changes only the host integration; it must not create a second component schema or renderer.

## References

- [Tauri architecture](https://v2.tauri.app/concept/architecture/)
- [Tauri capabilities and security boundaries](https://tauri.app/security/capabilities/)
- [Microsoft WebView2 distribution modes](https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution)
- [Electron process sandboxing](https://www.electronjs.org/docs/latest/tutorial/sandbox)
- [Electron security recommendations](https://www.electronjs.org/docs/latest/tutorial/security)
