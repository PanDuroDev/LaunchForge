# LaunchForge — Product Plan

> **Status:** Concept / pre-development  
> **Document type:** Product definition, scope, architecture direction, and implementation roadmap  
> **Primary target:** Windows desktop  
> **Working tagline:** Build. Customize. Launch.

## 1. Product summary

LaunchForge is a visual development platform for creating, customizing, testing, and packaging standalone game launchers.

It targets indie game developers, small studios, and publishers that want a branded launcher for one game or a collection of their own games, but do not want to build and maintain a launcher application from scratch.

LaunchForge is **not** a game store, game marketplace, or competitor to Steam, Epic Games Store, or other distribution platforms. It is a tool used by developers to create their own launcher products.

A user creates a **Launcher Project** in LaunchForge Studio, designs its interface in a visual editor, connects content and game services, configures launcher behavior, previews the result, and exports an independent application.

Each exported launcher should work without LaunchForge Studio installed or running.

## 2. The problem

A studio that wants its own launcher currently has to build or commission several things:

- A desktop application and its user interface.
- A content system for news, banners, game details, and announcements.
- Connections to APIs or other data sources.
- Game installation, update, verification, and launch workflows.
- An application update mechanism.
- Packaging, branding, testing, and distribution.

This creates repeated engineering and maintenance work, especially for small teams and studios with only one or a few games.

LaunchForge aims to turn the common parts into reusable platform capabilities while allowing each studio to create a distinct branded experience.

## 3. Product principles

1. **Visual-first, not code-first:** Common launcher creation and configuration tasks must be possible without writing code.
2. **Real-time feedback:** Changes in the editor should appear in the preview with minimal delay.
3. **Independent output:** An exported launcher is a standalone application, not a window into the Studio.
4. **Separation of concerns:** UI design, content/data integration, game operations, and launcher updates must remain separate subsystems.
5. **Extensible, not unlimited:** Built-in components and actions cover common use cases; code extensions handle advanced cases. Do not promise that every possible behavior can be configured without code.
6. **Secure by default:** Distributed launcher packages must not contain private server credentials or unrestricted access to the host system.
7. **Small-team friendly:** Prefer sensible defaults, templates, and guided setup over exposing every low-level setting immediately.

## 4. Target users and use cases

### Primary users

- Indie developers shipping one game.
- Small studios publishing several games under one brand.
- Publishers that need a branded launcher for a defined game catalog.
- Developers who can operate APIs but do not want to build a desktop UI and updater from scratch.

### Example use cases

- A single-game launcher with artwork, news, install/update, and Play actions.
- A studio launcher showing several games, each with its own status and actions.
- A launcher that displays remotely managed announcements and game metadata.
- Multiple independent launcher products managed from one Studio workspace.

### Terminology

Use **Launcher Project** for a project being authored in Studio. Use **Launcher** for the built application.

Avoid describing these projects as nested or "sub-launchers". They are separate projects that can share templates, components, and configuration presets.

## 5. Product structure

LaunchForge consists of three main products/subsystems.

### 5.1 LaunchForge Studio

The authoring application used to create and manage Launcher Projects.

Core areas:

- Project dashboard and project settings.
- Visual interface editor.
- Component and layer hierarchy.
- Theme and design-token editor.
- Data connections and field mapping.
- Actions and event configuration.
- Game configuration.
- Preview and test tools.
- Build and export settings.

### 5.2 Launcher Runtime

The shared application runtime that powers exported launchers.

Responsibilities:

- Render the project-defined interface.
- Load project configuration and assets.
- Resolve approved data bindings.
- Execute supported actions.
- Manage game installation and updates when enabled.
- Launch configured games.
- Check for and apply launcher application updates.

The runtime must be versioned independently from Studio. A project format/runtime compatibility policy is required so an old project does not silently break after a runtime update.

### 5.3 Launcher package

The distributable output generated from a Launcher Project.

It contains the project configuration, required assets, and a compatible runtime. The initial distribution model should bundle the runtime with each launcher so end users do not need to install a shared LaunchForge dependency.

A future shared-runtime option may be evaluated only if it provides a clear operational benefit.

## 6. Core capabilities

### 6.1 Visual Interface Editor

This is the defining feature of LaunchForge.

The editor should provide:

- A central viewport with a live preview.
- A selectable component/layer hierarchy.
- A properties inspector for the selected component.
- Drag, resize, align, reorder, hide, and lock operations.
- Undo and redo.
- Copy, paste, duplicate, and delete.
- Layout controls for spacing, sizing, alignment, constraints, and anchoring.
- Theme tokens for colors, typography, spacing, radii, and other shared styles.
- Per-component overrides where appropriate.
- Preview at multiple window sizes and aspect ratios.
- Import and management of images, icons, fonts, and other supported assets.

The editor must support changing the structure of a layout, not only changing colors and dimensions. Users should be able to add, remove, and rearrange sections and components.

The editor should not attempt to become a general-purpose design tool or a full game-engine UI editor.

### 6.2 Component system

Provide reusable, configurable components. Initial candidates:

- Text and image.
- Buttons and navigation items.
- Containers and layout groups.
- Game card and game details panel.
- Game cover/artwork.
- Install, update, and Play controls.
- Download progress and status indicators.
- News/announcement card.
- Notification/banner.
- Video or media embed, if technically safe and useful.

Each component should define:

- Its editable properties.
- Its layout behavior.
- Its supported data bindings.
- Its available events.
- Its visual states (for example: idle, hover, disabled, loading, installed, updating, and error).

Do not create a large component catalog before the component schema and editor interaction model are stable.

### 6.3 Themes and styling

Support global design tokens and component-level styling.

Initial properties:

- Colors and gradients.
- Typography and text styles.
- Spacing and sizing.
- Corner radius.
- Borders.
- Shadows.
- Opacity.
- Alignment and layout.
- Visibility and responsive behavior.

A theme should be reusable across projects, while a project must be able to override individual tokens.

"Full customization" means broad control within the supported component and layout system. It does not mean arbitrary native-window behavior or unrestricted custom rendering in the no-code editor.

### 6.4 Data and service connections

A launcher may need remote content such as game names, descriptions, artwork, news, announcements, version information, and download metadata.

Provide a guided **Connection Builder**:

1. Choose a supported source type.
2. Enter the endpoint or source details.
3. Configure request method, headers, and authentication where applicable.
4. Test the connection.
5. Inspect a sample response/schema.
6. Map response fields to project data models and UI component properties.
7. Preview the result using sample or live data.

Initial source types to consider:

- REST/HTTP APIs returning JSON.
- Static JSON files.
- Local project data for offline/default content.

A connector/adapter interface should allow additional sources later.

**Database access rule:** Do not encourage direct connections from a distributed launcher to a private database. The normal path should be a server-side API. Database credentials embedded in a client application can be extracted. Direct database adapters, if ever supported, must be restricted to safe public/read-only scenarios and must not expose privileged credentials.

Data mapping should support basic transformations, defaults, optional fields, loading states, and error states. Advanced transformations can be added later.

### 6.5 Actions and visual logic

Users need to define what happens when they interact with components.

Provide a constrained visual event/action system rather than trying to build a complete programming language.

Initial events:

- On click.
- On project/launcher load.
- On data loaded or failed.
- On game state changed.

Initial actions:

- Navigate to a view/section.
- Open an external URL with confirmation/policy controls.
- Show or dismiss a notification.
- Refresh a data source.
- Install, update, verify, or launch a configured game.
- Set a supported UI state or variable.

Support simple conditions and sequences. Advanced users may later add code extensions through a documented API and a restricted execution model.

Do not expose unrestricted filesystem, process, shell, or network access to arbitrary UI scripts.

### 6.6 Game management

Game management is a core capability of the exported launcher, but it should be a modular subsystem. Not every Launcher Project must enable it.

When enabled, it should support:

- Game definitions and installation locations.
- Install, pause, resume, and cancel.
- Download progress and status.
- Version manifests.
- File integrity verification.
- Incremental/delta updates where practical.
- Repair or re-download of damaged files.
- Launch configuration and command-line arguments.
- Installed game detection where supported.
- Clear error reporting and recovery.

The update system needs a documented manifest format, file hashing, atomic or recoverable update behavior, and a strategy for interrupted downloads.

Do not build DRM, anti-cheat, payment processing, or a proprietary CDN into the first version. These are separate, high-risk systems and are not required to prove the product's core value.

### 6.7 Launcher application updates

Keep launcher updates separate from game updates.

The launcher updater is responsible for checking, downloading, verifying, and applying new versions of the launcher application itself. It must handle interrupted updates and avoid leaving the application unusable if an update fails.

Game update metadata and launcher release metadata must not share an ambiguous versioning scheme.

### 6.8 Templates and project management

Provide a small set of starter templates:

- Single-game launcher.
- Multi-game studio launcher.
- Minimal launcher.

Templates are starting points, not locked layouts.

Studio project management should support:

- Create, rename, duplicate, archive, and delete projects.
- Import/export project files.
- Reuse themes and approved components.
- Manage project assets.
- View project/runtime compatibility.
- Build and release history.

A public template marketplace is not part of the initial scope.

### 6.9 Application shell and window behavior

A branded launcher is more than the content inside its viewport. Project settings should expose the supported desktop application shell:

- Window title, icon, default size, minimum size, and resizability.
- Supported window modes and startup behavior.
- Native title bar versus a custom title bar, where the selected framework permits it.
- Minimize, maximize, close, and window-drag behavior when using a custom title bar.
- Optional tray behavior only if it is needed by real launcher workflows.

These settings must be constrained by the runtime and operating system. Do not promise arbitrary native-window customization through the visual component editor.

### 6.10 Preview, testing, and export

The preview should use the same rendering and component behavior as the exported runtime wherever practical. Avoid maintaining two separate implementations that drift apart.

Provide:

- Live viewport preview.
- Multiple window-size presets.
- Sample-data mode and connected-data mode.
- Connection tests.
- Action/event testing.
- Game workflow testing with safe test fixtures.
- Build validation and actionable error messages.

The preview and runtime should also support useful diagnostics: structured logs, connection/action errors, and a way to copy a sanitized diagnostic report. Project editing should include autosave or reliable recovery after an unexpected Studio shutdown.

Build outputs should include:

- A Windows installer.
- A portable package if feasible.
- Application name, icon, publisher metadata, and version.
- Bundled runtime and required assets.
- Optional launcher update configuration.

## 7. Technology and renderer architecture decision

### 7.1 Decision principles

LaunchForge should use a **shared project model with replaceable renderer adapters**, but it must not promise that every project can run identically on every renderer. The project schema describes supported layout, components, data, actions, and capabilities. Each renderer declares what it supports. Studio validates a project's requirements against the selected build target and reports unsupported features before export.

Renderer selection should happen at **build/export time**, not be permanently embedded in the authored project. A project may target more than one renderer only when every used component and capability is supported by each target. The default project target is the first supported Windows renderer.

Do not build several production renderers in the MVP. Prove the adapter boundary with one production renderer and, at most, a second small compatibility spike.

### 7.2 Candidate technology evaluation

These are engineering assessments, not benchmark results. Package size, startup time, memory, and rendering performance must be measured in Phase 0 using the same sample project and build settings.

| Responsibility / candidate | Strengths | Costs and risks | Initial position |
|---|---|---|---|
| Rust for shared Runtime/core services | Strong performance, memory safety, native system access, good fit for bounded services and file/network operations | Steeper learning curve; UI ecosystem is smaller; async and FFI boundaries need discipline | Preferred candidate for shared Runtime core, subject to PoC |
| C#/.NET | Productive, mature Windows APIs, strong tooling and test ecosystem, accessible for a solo Windows-first developer | Runtime deployment and cross-platform packaging need planning; native UI choices can constrain portability | Strong alternative for Studio host or Windows-specific services |
| C++ | Mature native ecosystem and maximum control | Higher memory-safety burden, build complexity, and maintenance cost | Use only where a required library or measured performance case justifies it |
| TypeScript + React | Mature component ecosystem, fast iteration, suitable for complex editor panels and tooling | Browser UI needs a host; large dependency trees and web/native boundary must be controlled | Preferred Studio editor UI candidate |
| Electron | Consistent Chromium rendering and broad web ecosystem; straightforward web tooling | Bundles Chromium, usually increases package and memory costs; larger attack surface and update footprint | Useful high-fidelity comparison baseline, not default |
| Tauri | Web UI with native host; generally avoids bundling a full Chromium runtime by using system WebView | WebView differences across machines/OS versions; Rust host integration and plugin permissions need care | Preferred first renderer/host candidate if PoC parity is acceptable |
| WebView2 | Good Windows integration and familiar web UI; runtime may be present or installed separately | Windows-specific; runtime availability/deployment and WebView2 version behavior must be handled | Strong Windows-only fallback/alternative to Tauri |
| WinUI 3 | Native Windows look and OS integration | Windows-only; a separate component implementation is needed; difficult to share UI code with web renderers | Consider only if native UX is a proven differentiator |
| Avalonia | .NET UI with cross-platform reach and a mature desktop model | Different layout/rendering/component model from web; web-to-native parity is not automatic | Alternative if C# becomes the dominant stack |
| Qt Quick | Mature declarative UI and strong rendering capabilities across platforms | Qt licensing, deployment, and a separate QML skill/tooling surface add cost | Technical alternative, not an MVP dependency |

### 7.3 Provisional stack recommendation

Use the following as the Phase 0 starting hypothesis, not an irreversible commitment:

- **Studio UI:** TypeScript + React for the visual editor, project dashboard, inspector, and workflow panels.
- **Studio host:** Tauri/Rust as the first PoC candidate for filesystem access, window integration, secure storage bridges, and process orchestration. Compare it directly with a WebView2/.NET host before deciding.
- **Shared Runtime/core:** Rust for project loading/validation, capability checks, data/network services, game operations, and build/runtime contracts where native services are required.
- **Renderer:** Web technologies hosted by the selected Windows shell for the first production renderer. Keep the renderer adapter contract independent of Tauri-specific APIs.
- **Project format:** JSON with a versioned schema and explicit migrations. Keep assets as external project files referenced by stable relative asset IDs/paths; do not encode binary assets into the main project document.
- **Build tooling:** deterministic, testable CLI/library interfaces invoked by Studio. Avoid hiding all build logic inside UI code.
- **Windows integration:** isolate OS-specific operations behind narrow interfaces. Do not let the renderer directly own filesystem, process, credential, or update privileges.

If Phase 0 shows that Tauri's WebView behavior or distribution model is unsuitable, select WebView2/.NET or another candidate using the same acceptance criteria. Do not force Rust into every layer merely for language consistency.

### 7.4 Renderer adapter and capability model

The architecture should contain these contracts:

1. **Project Schema:** renderer-neutral definitions for supported nodes, layout constraints, design tokens, assets, data bindings, actions, and required capabilities.
2. **Component Contract:** stable component IDs, typed properties, defaults, validation, events, state definitions, and versioning.
3. **Renderer Adapter:** maps supported schema nodes to a renderer implementation and exposes its supported capabilities.
4. **Capability Profile:** declares support for layout primitives, fonts, media, window behavior, accessibility, input, and other renderer-dependent features.
5. **Runtime Host API:** narrow, permissioned APIs for filesystem, networking, game operations, window controls, and secure credential access.
6. **Build Target:** selects a renderer/runtime combination, validates compatibility, packages dependencies, and records exact versions.

Unsupported features must produce a build-blocking diagnostic or an explicitly documented fallback. Silent visual degradation is not acceptable. Do not claim automatic conversion between HTML/CSS, WinUI, Avalonia, and Qt Quick. Shared schema means shared intent and supported components, not identical rendering engines.

### 7.5 Phase 0 proof-of-concept plan

Build the same small sample launcher in each serious candidate. The sample must contain text, image, button, container/layout, one navigation action, one local data binding, and a basic window shell. Export it and run it outside the Studio.

Measure on the same modest Windows machine and record environment/build settings:

- Cold start to first usable frame; report median and p95 across repeated runs.
- Idle and peak memory after a fixed warm-up period.
- CPU usage while idle and during a defined interaction.
- Installer and extracted package size, separating shared/preinstalled dependencies.
- Build time and clean-machine deployment success.
- Preview/export visual and behavioral parity.
- Accessibility/keyboard behavior and DPI/scaling behavior.
- Developer effort, debugging quality, dependency/update burden, and module isolation.

Do not publish a single synthetic "performance score". Include raw measurements, test scripts, caveats, and a decision record. The selected stack must pass functional parity and distribution gates first; performance is a comparison among viable candidates.

### 7.6 AI collaboration and module ownership

Use contract-first work packages. One architecture/integration owner controls shared schemas, public interfaces, dependency versions, and release gates. Other agents own bounded modules and must not edit shared contracts without an approved change proposal.

Parallel work is allowed only after interface stubs and test fixtures are agreed. Each package must name owned paths, forbidden paths, inputs/outputs, tests, and handoff artifacts. Avoid assigning two agents to the same central project schema, renderer registry, or build pipeline simultaneously.

### 7.7 System boundaries

Keep these modules explicit:

- Studio UI and editor state.
- Studio host and privileged OS bridges.
- Versioned project schema and migration tooling.
- Renderer adapters and capability profiles.
- Shared Runtime core and host API.
- Data adapters and binding evaluator.
- Game operations service.
- Launcher updater, isolated from game updates.
- Build/export CLI and packaging.
- Diagnostics, logs, and test fixtures.

The preview should host the same renderer and component implementation as the exported launcher wherever practical. A separate mock preview that behaves differently is not an acceptable substitute.

## 8. Security and trust boundaries

Security is a design constraint from the first prototype. The exported launcher is controlled by its publisher but runs on another person's machine and must be treated as an untrusted client.

### 8.1 Credentials and secrets

Classify every credential by where it is allowed to exist:

- **Studio-only credentials:** used to configure or publish a project; stored in OS secure storage and never serialized into project files or launcher packages.
- **Runtime-provided/user credentials:** entered by the end user or obtained through a supported sign-in flow; stored using OS secure storage where persistence is required. Tokens must have scoped permissions and defined expiry/refresh behavior.
- **Public project configuration:** non-secret endpoint URLs, public identifiers, and headers explicitly documented as public may be stored in the project.
- **Publisher/server secrets:** private API keys, database passwords, signing keys, and privileged service credentials must remain on publisher-controlled servers or secure build infrastructure. They must never be shipped in the launcher.

The MVP should prefer public/read-only endpoints or a publisher backend. Do not promise that a secret embedded in a desktop client can be hidden.

The export pipeline must scan the resolved build inputs and final package for known secret-bearing fields and configured secret patterns. Export must fail closed when a secret is detected; warnings alone are insufficient. Diagnostics must identify the offending configuration without printing the secret value.

### 8.2 Network and data safety

- Require HTTPS for remote production connections; reject cleartext HTTP except an explicitly enabled local-development mode.
- Validate TLS certificates using platform defaults; do not provide an option to silently ignore certificate errors.
- Define connection/read timeouts, cancellation, response and download size limits, redirect allowlists/policies, and bounded retries with backoff.
- Treat remote JSON, manifests, archive entries, filenames, and imported project files as untrusted.
- Apply content-type, schema, size, and parsing limits before processing remote data.
- Never forward credentials across an untrusted redirect or to a different origin without an explicit policy.

### 8.3 Filesystem and process boundaries

- Game manifests may contain only normalized relative destination paths.
- Reject absolute, UNC, drive-qualified, device paths, alternate data stream syntax where relevant, and any parent-traversal segment.
- Canonicalize destination paths and verify containment beneath the selected game root immediately before writes.
- Define and test symlink, junction, and reparse-point behavior; do not follow a link that escapes the authorized root.
- Do not require administrator privileges for ordinary game installation.
- Keep shell/process execution out of visual actions. Launch only explicitly configured game executables with validated arguments and a clear working directory.
- Imported projects and assets must not trigger arbitrary code execution.

### 8.4 Launcher self-update trust

A hash alone does not authenticate an update if an attacker can replace both the manifest and artifact. The updater must verify signed release metadata against a client-held trust anchor, bind metadata to the exact artifact/version, reject missing or invalid signatures, and reject unauthorized downgrades. Define bootstrap, key rotation, revocation, recovery, and rollback policy before shipping the updater. Failed updates must leave a usable prior version or a documented recovery path.

### 8.5 Permissions and diagnostics

Expose privileged capabilities through explicit, narrow Runtime APIs. Extensions, if introduced, must receive declared permissions and must not inherit unrestricted host access. Logs and diagnostic bundles must redact tokens, credentials, personal data, and sensitive filesystem paths by default.

## 9. Explicit non-goals

The following are outside the initial product definition:

- A game store or marketplace.
- A public game-discovery network.
- Social feeds, friends, chat, achievements, or community servers.
- Game hosting or CDN infrastructure operated by LaunchForge.
- A general-purpose website builder.
- A full game engine or 3D editor.
- Built-in payment processing, DRM, or anti-cheat.
- A requirement that every launcher use a LaunchForge-hosted backend.
- A requirement that every project include game installation features.

These features would increase cost and scope without validating the central promise: making custom standalone launchers easier to create.

## 10. MVP definition

The MVP is the smallest complete product that proves the central promise: a developer can author a branded launcher in Studio, preview it, export it, and distribute a standalone Windows application.

The MVP is **not** a complete game distribution platform. It should prove the authoring-to-export pipeline before taking on large-scale download infrastructure.

### 10.1 MVP user journey

1. Create a Launcher Project from a minimal starter.
2. Add and configure a small set of UI components.
3. Add one game entry with title, artwork, description, and a configured local executable or test fixture.
4. Preview the launcher at a small set of window sizes.
5. Validate and build the project.
6. Export a standalone Windows launcher with bundled Runtime.
7. Run it outside Studio on a clean supported Windows environment.
8. Launch the configured local test game and receive a clear error if it is unavailable.

### 10.2 MVP must include

- Windows-only Studio shell and project create/open/save.
- One versioned project schema with validation and migration policy.
- One production renderer and a shared preview/export component implementation.
- A deliberately small editor: component tree, selection, property inspector, add/remove/reorder, basic layout, theme tokens, undo/redo, and asset references.
- Minimal components: container, text, image, button, and game entry/card.
- One game entry with local metadata and a safe, explicitly configured launch target.
- Basic window settings: title, icon, default/minimum size, resize behavior.
- Runtime host APIs with explicit permissions; no arbitrary scripts.
- Build/export CLI and bundled Runtime.
- Installer or portable distribution (choose one for the first MVP; support the second only if the first is stable).
- Structured logs, build diagnostics, and clean-machine smoke tests.
- Export secret scan and baseline project/package validation.

### 10.3 Explicitly deferred from MVP

- Full game downloading, patching, repair, delta updates, and manifest-driven installation.
- Remote API connection builder and complex data binding.
- OAuth/provider ecosystem and user account management.
- Visual programming beyond a few built-in actions.
- Multiple production renderers.
- Plugin marketplace or arbitrary custom code.
- Cloud sync, collaboration, team permissions, and hosted backend.
- Analytics/telemetry dashboards.
- macOS/Linux support.
- Advanced animation timelines, custom shaders, and general-purpose design-tool features.
- Launcher self-update in production.

A bounded technical spike may validate remote JSON or game download behavior, but it must not expand the MVP unless it is required to prove the core authoring/export workflow.

### 10.4 MVP definition of done

- A first-time user can create a project from the starter and build the sample launcher without editing source code.
- The preview and exported application use the same component/renderer implementation and pass defined parity tests.
- The exported application runs without Studio, development tools, or an undeclared shared dependency.
- The configured game entry can launch a local test executable through the documented Runtime API.
- Invalid projects, missing assets, unsupported capabilities, and build failures produce actionable diagnostics.
- Export fails if prohibited credentials are found.
- A clean-machine test on the supported Windows baseline passes.
- Startup, idle memory, package size, and build time are measured and recorded; thresholds are set after Phase 0 measurements, not invented in advance.

## 11. Phased development roadmap

The roadmap is release-oriented. Each release must produce a testable user outcome. Work packages inside a phase may run in parallel only after their contracts and ownership boundaries are approved.

### Milestone overview

| Phase | Release outcome | Depends on |
|---|---|---|
| 0 — Validation and architecture | Evidence-backed stack, renderer, schema, and contracts | None |
| 1 — End-to-end MVP | Create, edit, preview, export, run, and launch a local game entry | Phase 0 |
| 2 — Authoring experience | More capable editor, layout, themes, assets, templates, project workflows | Phase 1 |
| 3 — Data-driven launchers | Safe API/JSON connections, typed bindings, basic visual actions | Phases 1–2 |
| 4 — Game operations | Install, verify, update, repair, and launch managed games | Phases 1 and 3 contracts |
| 5 — Production distribution | Trusted launcher updates, signing/distribution readiness, hardening | Phases 1 and 4 as applicable |
| 6 — Extensibility and platform expansion | Additional renderers, plugins, and OS targets based on demand | Stable Phase 5 foundation |

### Phase 0 — Validation and architecture decisions

**Goal / user outcome:** No end-user release. Remove the largest technical unknowns before implementation creates expensive coupling.

**Work packages**
- **P0-A — Technology and renderer spike:** compare the serious host/renderer candidates using the same sample launcher and measurement protocol.
- **P0-B — Project and component contracts:** define project schema, component metadata, layout primitives, asset references, schema versioning, and migration rules.
- **P0-C — Runtime and host boundary:** define renderer-neutral Runtime APIs, capability profiles, permission boundaries, and preview/export parity contract.
- **P0-D — Build and distribution spike:** prove a clean-machine standalone package with bundled dependencies and reproducible build metadata.
- **P0-E — Security and test baseline:** threat model, credential classes, export scanning, network limits, path rules, diagnostics, and automated test strategy.

**Dependencies:** None. P0 work packages may run in parallel after a shared sample-project brief is agreed; P0-B and P0-C must be reviewed together.

**Exclusions:** Production editor, production game downloader, multiple production renderers, updater, plugin system, and platform expansion.

**Acceptance criteria / phase gate**
- A written decision record compares candidates and includes raw PoC measurements and limitations.
- One first-release renderer/host stack is selected with explicit reasons and fallback decision.
- The same sample project renders and behaves consistently in preview and standalone export.
- Project/component/runtime/build contracts are versioned and have test fixtures.
- Capability negotiation and unsupported-feature behavior are demonstrated.
- Security requirements are testable and assigned to the phases that implement them.
- The architecture owner approves the contracts before Phase 1 implementation begins.

**Main risks:** Over-generalizing the renderer abstraction; choosing a stack based on popularity; underestimating clean-machine packaging; creating contracts that are too broad for a solo developer.

### Phase 1 — End-to-end Windows MVP

**Goal / user outcome:** A developer can create and export one simple standalone launcher that displays a game entry and launches a local test game.

**Work packages**
- **P1-A — Project schema and validation implementation:** project load/save, schema validation, stable IDs, asset references, compatibility metadata.
- **P1-B — Minimal Studio shell/editor:** project workflow, component tree, inspector, add/remove/reorder, basic properties and undo/redo.
- **P1-C — Renderer and preview:** first production renderer, component set, live preview, parity fixtures.
- **P1-D — Runtime host and game launch:** standalone host, minimal Runtime APIs, configured local executable launch, safe error reporting.
- **P1-E — Build/export and release smoke tests:** build CLI, bundled Runtime, package metadata, installer or portable output, clean-machine test.

**Parallelism:** P1-A owns the schema; other packages consume its frozen interfaces. P1-B and P1-C can proceed in parallel using mock fixtures. P1-D can build the host shell against the agreed component contract. P1-E starts once a minimal vertical slice exists. One integration owner controls shared contracts and assembles the end-to-end path.

**Dependencies:** Phase 0 decisions and approved contracts.

**Exclusions:** Remote APIs, full game installation, updater, plugin system, multiple renderers, cloud services, and non-Windows targets.

**Acceptance criteria / phase gate**
- The complete MVP journey in Section 10 passes on a clean supported Windows machine.
- Preview/export parity tests pass for every MVP component and supported window behavior.
- No project can request a Runtime capability that is not declared and validated.
- Game launch is restricted to the configured executable and documented arguments.
- Build diagnostics, structured logs, secret scanning, and recovery behavior pass tests.
- A reproducible sample project and test procedure are committed.

**Main risks:** Scope creep in the editor; schema churn; preview/runtime divergence; packaging surprises; unsafe process-launch behavior.

### Phase 2 — Authoring experience and reusable project workflows

**Goal / user outcome:** Developers can create more polished launchers efficiently and reuse approved work across projects.

**Scope**
- Better layout primitives, alignment, anchors/constraints, responsive presets, and visual states.
- More complete component property editing and component metadata tooling.
- Asset library/import validation and theme management.
- Starter templates (single-game, multi-game, minimal) built from supported components.
- Project dashboard, duplicate/archive/import/export, and build history.
- Improved keyboard accessibility, localization-ready strings, and RTL layout behavior in Studio and Runtime.

**Dependencies:** Stable MVP schema, renderer contract, and export pipeline.

**Exclusions:** Public template marketplace, cloud collaboration, arbitrary component scripting, and additional production renderers.

**Acceptance criteria / phase gate**
- A user can create and customize the supported templates without editing project JSON.
- Layout behavior is predictable at documented window sizes and DPI settings.
- Project import/export and duplication preserve assets and stable references.
- Keyboard workflows, focus states, Unicode, and RTL test cases pass for supported components.

**Main risks:** Turning the editor into a general-purpose design tool; excessive layout freedom; inaccessible drag-only workflows; template/schema coupling.

### Phase 3 — Data connections and visual interactions

**Goal / user outcome:** Launchers can show remotely managed content and respond to basic user interactions without embedding publisher secrets.

**Scope**
- REST/HTTP JSON and static JSON adapters.
- Connection test, sample response inspector, typed field mapping, defaults, optional values, and basic transformations.
- Loading, empty, offline, stale-cache, and error states.
- Constrained events/actions: navigation, notification, refresh data, open approved URL, set UI state.
- Public endpoint and publisher-backend patterns; no private database access from the client.
- Bounded network policies: connection/read timeouts, cancellation, size limits, redirect rules, and bounded retries.
- Credential classification, secure storage rules, and fail-closed export scanning for secret-bearing values.

**Dependencies:** Stable project schema and Runtime host API; Phase 2 editor workflows for a usable connection builder.

**Exclusions:** Complex OAuth, arbitrary scripting, private database drivers, hosted LaunchForge backend, and unrestricted networking.

**Acceptance criteria / phase gate**
- Sample and live JSON data render through typed bindings in preview and export.
- Invalid mappings and malformed/oversized responses fail safely with actionable diagnostics.
- Network policies are enforced and tested.
- No publisher secret is serialized into the project or exported package.
- Offline/cache behavior is documented and deterministic.

**Main risks:** Secret leakage, inconsistent API schemas, unbounded requests, confusing binding UX, and excessive action-system complexity.

### Phase 4 — Managed game installation and lifecycle

**Goal / user outcome:** A launcher can safely install, verify, update, repair, and launch a game distributed by its publisher.

**Scope**
- Versioned game manifest and publisher-owned distribution endpoint contract.
- Download manager with progress, cancellation, bounded retries, and carefully scoped resume support.
- Hash verification and explicit trust model for manifests/artifacts.
- Install, verify, update, repair, and launch state machine.
- Safe installation root and path confinement rules, including symlink/junction/reparse-point handling.
- Recovery from interrupted downloads and updates.
- Runtime UI state/events for install and update progress.
- Test fixtures for malicious manifests, corrupted files, and interrupted operations.

**Dependencies:** Standalone Runtime and build pipeline; data/network contracts where reused.

**Exclusions:** DRM, anti-cheat, payments, proprietary CDN, delta patching until measured need exists, privileged system-wide installs, and launcher self-update.

**Acceptance criteria / phase gate**
- A test game completes install, verification, update, repair, and launch.
- Every write remains within the authorized install root, including under adversarial path/link tests.
- Corrupted or unauthenticated content is rejected.
- Interrupted operations recover without destroying the last valid installation.
- Progress, cancellation, and error states remain accurate.

**Main risks:** Filesystem escape, malicious manifests, storage exhaustion, partial-update corruption, and network instability.

### Phase 5 — Production distribution and launcher self-updates

**Goal / user outcome:** Publishers can distribute and maintain their launcher with a verifiable update process and predictable recovery.

**Scope**
- Publisher identity and Windows signing/distribution guidance; signing infrastructure remains publisher-owned.
- Signed release metadata with a client-held trust anchor and artifact binding.
- Version and downgrade policy, key bootstrap/rotation/revocation design.
- Separate launcher release channel and metadata from game releases.
- Safe staging, verification, apply, restart, rollback/recovery, and interrupted-update handling.
- Security review across project import, Studio, Runtime, network, game operations, build/export, and updater.
- Crash diagnostics, sanitized support bundles, and release readiness checklist.

**Dependencies:** Stable standalone packaging and Runtime; Phase 4 trust primitives where shared.

**Exclusions:** LaunchForge-operated update/CDN hosting, mandatory paid code-signing service, automatic updates without publisher configuration, and broad platform expansion.

**Acceptance criteria / phase gate**
- Invalid, missing, tampered, replayed, or unauthorized downgrade metadata is rejected.
- A failed update leaves the prior launcher usable or provides a tested recovery path.
- Key lifecycle and trust bootstrap are documented and tested in a controlled environment.
- Publisher configuration clearly separates game updates from launcher updates.
- Security findings have documented remediation or accepted risk owners.

**Main risks:** Trust bootstrap, key loss/compromise, Windows reputation/signing cost, and destructive update failures.

### Phase 6 — Extensibility and platform expansion

**Goal / user outcome:** LaunchForge can support advanced workflows and additional platforms without weakening the stability of the default experience.

**Scope candidates, each requiring a separate proposal and proof of concept**
- Permissioned component/action extensions with explicit capability grants.
- Additional renderer adapters (for example native Windows or another cross-platform renderer).
- macOS/Linux Studio and exported launcher support.
- Additional data adapters and publisher integrations.
- Optional team workflows or cloud services only if validated by actual users.

**Dependencies:** Stable schema/migrations, Runtime APIs, build pipeline, security model, and production release process.

**Exclusions:** Unrestricted plugins, arbitrary native code execution, automatic cross-renderer conversion, and platform promises without tested packaging and parity.

**Acceptance criteria / phase gate**
- Every extension declares versioned interfaces and explicit permissions.
- Every renderer/platform has its own capability profile, parity suite, packaging tests, and performance measurements.
- Existing projects remain compatible or receive explicit migration/unsupported-feature diagnostics.
- A feature is accepted only when a real use case justifies its maintenance cost.

**Main risks:** Compatibility fragmentation, plugin attack surface, platform-specific regressions, and support burden.

### Cross-phase foundations

These must be designed in Phase 0 and implemented incrementally:

- Project schema, stable IDs, versioning, migration, and compatibility matrix.
- Studio/Runtime/component/renderer/build contracts.
- Capability profiles and unsupported-feature diagnostics.
- Security model, credential classes, permissions, network limits, and path confinement.
- Structured diagnostics, redaction, and reproducible test fixtures.
- Accessibility, localization, Unicode, DPI, and RTL behavior.
- Automated contract tests and clean-machine distribution tests.

### Decisions required before each phase

| Before phase | Decisions that must be closed |
|---|---|
| 1 | First renderer/host, schema v1, component contract, Runtime APIs, build format, supported Windows baseline |
| 2 | Layout model, template format, asset ownership, undo/redo model, localization and RTL strategy |
| 3 | Supported auth modes, cache policy, mapping semantics, request limits, secret scanning rules |
| 4 | Manifest trust, install-root ownership, archive policy, path/link handling, recovery guarantees |
| 5 | Signing model, trust-anchor bootstrap, release metadata format, downgrade/rollback policy |
| 6 | Extension permissions, renderer capability policy, platform support criteria, compatibility guarantees |

## 12. Operational requirements and integration contract

A launcher is a distributed desktop application, so the product plan must cover its behavior after it leaves the developer's machine.

### Studio responsibilities

- Validate project structure, component properties, data bindings, and required capabilities before building.
- Save projects safely and provide recovery from interrupted editing sessions.
- Report missing assets, invalid connections, unsupported actions, and runtime incompatibilities.
- Produce reproducible build metadata, including project schema and runtime versions.

### Launcher responsibilities

- Handle unavailable APIs, slow networks, missing assets, and malformed responses without crashing.
- Use cache policies and sensible fallbacks for remote artwork and content.
- Show loading, empty, offline, and error states instead of silently rendering broken UI.
- Keep logs useful but avoid recording credentials or private user data.
- Clearly distinguish launcher updates from game updates.

### Developer-owned services

LaunchForge should define documented contracts, not operate every studio's backend.

A developer remains responsible for hosting their API, content, game files, and update manifests. LaunchForge may provide examples and local test fixtures, but a hosted backend, CDN, account system, or analytics service is not required by the product.

Document the minimum API/data contract for game metadata, content, and (later) game release manifests. The contract should define versioning, hashes, file URLs, authentication expectations, and error responses before the full downloader is implemented.

### Accessibility and localization

- Support keyboard navigation and visible focus states in Studio and exported launchers.
- Avoid hard-coded text in layouts; use project-managed strings.
- Support Unicode and locale-aware formatting.
- Plan for right-to-left layout and text direction, including mirrored navigation and directional icons.
- Do not treat translation as a simple string replacement when layout direction changes.

## 13. Risks and unresolved decisions

These decisions must be answered through prototypes, not guesses.

| Question | Why it matters | Proposed approach |
|---|---|---|
| Which UI framework and language? | Affects editor complexity, runtime reuse, packaging, and performance. | Run a small comparative prototype before committing. |
| How is the UI rendered? | Preview/runtime consistency is central to the product. | Use one renderer/component implementation in both. |
| How flexible is layout? | Excessive freedom makes the editor and responsive behavior difficult. | Start with constraints, containers, anchors, and reusable layout primitives. |
| How are projects versioned? | Runtime changes can break older projects. | Version the schema and provide explicit migrations. |
| How are data bindings represented? | Unstructured bindings become hard to debug and validate. | Use typed paths, sample schemas, defaults, and visible binding errors. |
| How are game files distributed? | Large downloads and interrupted updates are operationally difficult. | Define a manifest and integrity model before implementing a downloader. |
| How are secrets handled? | Client packages are inspectable and cannot safely hide private credentials. | Keep privileged operations server-side. |
| What does "custom code" mean? | Unrestricted scripts create security and support problems. | Defer it until a permissioned extension API exists. |
| How are builds signed? | Windows trust and distribution experience depend on signing. | Document signing as a release requirement; do not assume a certificate is available for development. |

## 14. Success criteria

Measure whether LaunchForge reduces the work required to create and maintain a branded launcher.

For the MVP, track:

- Time from a blank project to a working basic launcher.
- Whether a non-programmer can complete the template-based workflow.
- Preview/export visual consistency.
- Build success rate on clean Windows environments.
- Data connection setup success and clarity of errors.
- Runtime startup time and idle resource usage.
- Reliability of install/update operations once that subsystem is introduced.

Do not optimize around download counts or marketplace activity before the core authoring workflow works.

## 15. Current scope decisions

The following decisions are the working baseline for initial development:

- Product category: visual game-launcher development platform, not a game store or generic website builder.
- Initial platform: Windows desktop.
- Primary user: indie developers and small studios.
- Main differentiator: visual authoring, real-time preview, and export of an independent branded launcher.
- Multiple launchers: separate Launcher Projects managed by one Studio.
- Project model: one versioned, renderer-neutral schema with explicit component and capability contracts.
- Renderer selection: selected at build/export time; a project may target multiple renderers only when all used features are supported by each target.
- Technology direction: TypeScript/React for Studio UI and Rust for the shared host/Runtime core are the leading candidates; Tauri is the first host/renderer PoC candidate, with WebView2/.NET as a serious Windows-first alternative. This remains provisional until Phase 0 evidence is reviewed.
- Runtime distribution: shared codebase, bundled with each exported launcher initially.
- MVP: a narrow end-to-end Windows workflow with a small component set and one locally configured game entry. It does not require remote APIs or managed game downloads.
- Data: API/JSON-first, introduced after the MVP with typed bindings and bounded networking.
- Game management: optional subsystem, introduced after the standalone MVP and implemented with strict path and integrity guarantees.
- Launcher self-updates: separate from game updates and deferred until signed metadata, trust bootstrap, and recovery behavior are proven.
- Custom code: permissioned extension path only after the core product is stable; no arbitrary scripts in the MVP.
- No marketplace, social network, game store, LaunchForge-hosted game infrastructure, cloud collaboration, or multi-platform promise in the MVP.

Technology choices and performance thresholds are not claimed as final until Phase 0 PoCs and clean-machine tests are complete. This document defines product intent, provisional architecture direction, and measurable decision gates.
