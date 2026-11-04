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

The roadmap is organized around **working product outcomes**, not technology layers. Every phase ends with a usable increment, a testable gate, and a decision about whether the next investment is justified.

Do not implement every subsystem just because it appears in the long-term vision. LaunchForge is a small-team product: the default path should stay narrow, and optional capabilities should remain optional.

### 11.1 Release sequence

| Phase | Release | User-visible result | Depends on |
|---|---|---|---|
| 0 — De-risk the architecture | Internal spike | A proven technical direction and frozen contracts | None |
| 1 — Prove the product | MVP / private preview | Create, edit, preview, export, run, and launch a local game | Phase 0 |
| 2 — Make authoring practical | Studio beta | Build polished launchers with reusable layouts, assets, themes, and templates | Phase 1 |
| 3 — Make content dynamic | Data beta | Display remote content and configure safe interactions | Phase 1; Phase 2 editor foundations |
| 4 — Manage game delivery | Game-operations beta | Install, verify, update, repair, and launch managed games | Phase 1; Phase 3 network/security contracts where reused |
| 5 — Ship and maintain reliably | Production release | Hardened packaging, publisher release workflow, trusted launcher updates | Phases 1–4 as applicable |
| 6 — Expand deliberately | Expansion releases | Optional extensions, additional renderers, and additional OS targets | Stable Phase 5 foundation |

Phase 3 and Phase 2 are separate tracks after Phase 1. The data/runtime contracts can be prototyped while Studio authoring improvements proceed, but the full Connection Builder depends on the editor's stable inspector and project workflows. Phase 4 may prototype its manifest and downloader independently, but must not bypass Phase 0 security contracts or Phase 1 Runtime boundaries.

### 11.2 Phase 0 — De-risk the architecture

**Outcome:** A documented, evidence-backed technical direction. No production product is promised in this phase.

**Work packages**
- **P0-A — Candidate shortlist:** compare Tauri + web UI, WebView2 + .NET, and Electron as the primary practical candidates. Consider WinUI 3, Avalonia, or Qt Quick only if the first three fail a concrete requirement. Do not benchmark every possible framework.
- **P0-B — Responsibility and language map:** decide which layer owns Studio UI, privileged host operations, Runtime services, build tooling, and tests. Rust, C#, and TypeScript are candidates by responsibility, not a requirement to use all of them.
- **P0-C — Project/component contract:** define the smallest schema needed by the MVP, stable IDs, typed properties, asset references, layout semantics, and version/migration policy.
- **P0-D — Preview/export contract:** prove that preview and exported launcher use the same renderer and component implementation. Define capability checks only for real renderer-dependent features.
- **P0-E — Build/distribution spike:** export and run a small launcher on a clean supported Windows machine.
- **P0-F — Security and quality baseline:** threat model, credential classes, network limits, process-launch policy, path rules, diagnostics, and automated test strategy.

**Dependencies and parallelism:** P0-A/B can run together after agreeing on a single sample project. P0-C/D must be designed together. P0-E consumes a candidate stack and early contracts. P0-F reviews the proposed host/runtime boundaries. One architecture owner approves the final decisions.

**Deliverables:** Decision records, PoC source, reproducible test scripts/raw measurements, schema v1, component and Runtime contracts, build interface, threat model, and a Phase 1 ownership map.

**Acceptance criteria**
- A single Windows-first stack and one renderer are selected, with reasons and a fallback.
- The same sample project runs in preview and as a standalone export.
- A clean-machine package works without Studio or undeclared development dependencies.
- The MVP schema and Runtime/build interfaces are small, documented, and covered by fixtures.
- The architecture does not claim universal renderer portability; unsupported capabilities are reported explicitly.
- Phase 1 work can proceed without competing definitions of shared contracts.

**Exclusions:** Production editor, game downloader, launcher updater, plugins, marketplace, cloud services, multiple production renderers, and non-Windows support.

**Main risks:** Spending too long comparing frameworks, designing an abstraction for hypothetical renderers, and selecting a stack from benchmark numbers that do not reflect the actual product.

**Phase gate:** Stop technical exploration when one candidate satisfies the MVP requirements. Do not add another renderer unless a measured requirement forces it.

### 11.3 Phase 1 — Prove the product: end-to-end MVP

**Outcome:** A developer can create a basic Launcher Project, edit a small interface, preview it, export a standalone Windows launcher, run it outside Studio, and launch a configured local game executable.

**Work packages**
- **P1-A — Project foundation:** create/open/save, schema validation, stable IDs, asset references, and compatibility metadata.
- **P1-B — Minimal editor:** component tree, selection, inspector, add/remove/reorder, basic layout properties, and reliable undo/redo for supported edits.
- **P1-C — Shared renderer and preview:** container, text, image, button, and game-entry components; preview at a small set of window sizes.
- **P1-D — Runtime and local game launch:** standalone host, narrow permissioned APIs, configured executable and validated arguments, clear failure states.
- **P1-E — Build/export:** deterministic build command, bundled Runtime/assets, app metadata, and one portable distribution format.
- **P1-F — Integration/release gate:** sample project, parity tests, clean-machine tests, structured logs, diagnostics, and export secret scanning.

**Critical path:** P0 contracts → P1-A schema → P1-C renderer/component contract → P1-D Runtime integration → P1-E export → P1-F clean-machine end-to-end gate. P1-B can develop against fixtures once P1-A freezes the minimum schema. P1-F is owned by the integration lead; it is not an optional final cleanup task.

**MVP boundaries**
- One game entry with local metadata and a publisher/user-configured executable.
- Basic window title, icon, size, and resizability.
- A single starter project and a small component set.
- Basic navigation and local game-launch actions only.
- One production renderer and one Windows output format.

**Acceptance criteria**
- A new user completes the whole journey without editing project JSON or source code.
- Preview and export use the same renderer/components and pass defined parity tests.
- The launcher runs independently on a clean supported Windows machine.
- The game action can launch only the configured executable through the documented Runtime API.
- Invalid projects, missing assets, unsupported features, and build failures have actionable diagnostics.
- Secret scanning blocks export when prohibited credentials are detected.
- The sample project and test procedure are reproducible from a clean checkout.

**Exclusions:** Remote APIs, managed game downloads, repair/update workflows, launcher self-update, multiple renderers, arbitrary scripting, plugins, cloud sync, and non-Windows targets.

**Main risks:** Editor scope creep, schema churn, preview/export drift, unsafe process launch, and packaging surprises.

**Phase gate:** Do not label the MVP complete because the editor or build command works in isolation. The complete clean-machine user journey must pass.

### 11.4 Phase 2 — Make authoring practical: Studio beta

**Outcome:** Developers can create a polished, reusable launcher without fighting the editor or editing project files manually.

**Work packages**
- **P2-A — Layout and responsive behavior:** documented layout primitives, alignment, spacing, sizing, constraints, and a limited set of responsive/window presets.
- **P2-B — Editing workflow:** multi-selection where justified, copy/paste/duplicate, grouping, visibility/locking, inspector quality, and predictable undo/redo.
- **P2-C — Assets and themes:** asset import/library, validation, stable references, theme tokens, and reusable style presets.
- **P2-D — Templates and project workflows:** single-game/multi-game/minimal templates; duplicate, archive, import/export, and project compatibility view.
- **P2-E — Accessibility and localization:** keyboard workflows, focus behavior, Unicode, DPI/scaling, localization-ready strings, and RTL support for the supported component set.

**Dependencies and parallelism:** Phase 1 schema and renderer must be stable. P2-A owns layout semantics; P2-B consumes them. P2-C and P2-D can run in parallel after asset/theme/template contracts are agreed. P2-E tests the actual UI and Runtime behavior throughout, not only at the end.

**Acceptance criteria**
- Users can build and modify the supplied templates without editing JSON.
- Common layout changes are deterministic at documented window sizes and DPI settings.
- Import, duplication, and export preserve assets and stable references.
- Undo/redo, keyboard access, focus visibility, Unicode, and RTL behavior pass tests for supported controls.
- Existing MVP projects open without silent layout or data changes.

**Exclusions:** General-purpose design tooling, timeline animation, custom shaders, public marketplace, cloud collaboration, arbitrary component plugins, and extra production renderers.

**Main risks:** Overbuilding the editor, introducing too many layout modes, and allowing templates to become incompatible with schema evolution.

**Phase gate:** Validate the editor with representative launcher tasks. Features that do not materially improve those tasks stay deferred.

### 11.5 Phase 3 — Make content dynamic: data and interactions

**Outcome:** A launcher can display publisher-managed news, announcements, game metadata, and other remote JSON content with predictable failure behavior.

**Work packages**
- **P3-A — Network/data adapter:** HTTPS JSON requests, cancellation, timeouts, response limits, redirect rules, and bounded retries.
- **P3-B — Typed data model:** response inspection, field mapping, defaults, optional values, and limited safe transformations.
- **P3-C — Connection Builder:** configure/test endpoints, inspect sample data, map fields, and preview with sample/live data.
- **P3-D — UI states and actions:** loading/empty/offline/error/stale states; navigation, refresh, notifications, approved external links, and supported UI state changes.
- **P3-E — Credential/export policy:** credential classification, secure storage where user credentials are required, secret redaction, and fail-closed export checks.

**Dependencies and parallelism:** Runtime/network contracts from Phase 0 and project/component contracts from Phase 1 are mandatory. P3-A/B can be prototyped with fixtures while Phase 2 proceeds. P3-C depends on the stable inspector and project workflows from Phase 2. P3-D depends on a frozen event/action contract. P3-E reviews all packages before release.

**Acceptance criteria**
- Sample and live JSON data bind consistently in preview and exported launcher.
- Invalid mappings, malformed/oversized responses, redirects, timeouts, and cancellation are handled safely.
- Offline and stale-data behavior is documented and tested.
- No publisher-side secret is embedded in project files or exported packages.
- Actions are allowlisted and cannot invoke arbitrary shell, filesystem, or process access.

**Exclusions:** Private database connections, arbitrary scripting, complex OAuth/provider ecosystem, hosted LaunchForge backend, and unrestricted networking.

**Main risks:** Secret leakage, changing remote schemas, excessive transformation features, and preview/runtime behavior differences.

**Phase gate:** A connection is not considered supported until the same fixtures and failure cases pass in Studio preview and exported Runtime.

### 11.6 Phase 4 — Manage game delivery: game operations

**Outcome:** A launcher can safely install, verify, update, repair, and launch a publisher's game.

**Work packages**
- **P4-A — Distribution manifest:** versioned manifest, file metadata, integrity hashes, publisher trust model, and compatibility rules.
- **P4-B — Download service:** bounded downloads, progress, cancellation, storage limits, and carefully scoped resume behavior.
- **P4-C — Installation transaction engine:** staging, verification, safe commit, update/repair, rollback, and interrupted-operation recovery.
- **P4-D — Runtime/UI integration:** game lifecycle API, state machine, progress, errors, and launch configuration.
- **P4-E — Adversarial test suite:** malicious paths/archives, corrupted artifacts, disk exhaustion, interrupted operations, and reparse-point tests.

**Dependencies and parallelism:** Phase 0 filesystem/network/security rules and Phase 1 Runtime/build contracts are mandatory. P4-A and P4-B can work against agreed fixtures in parallel. P4-C depends on their frozen contracts. P4-D consumes the lifecycle API. P4-E is involved from the first implementation, not after feature completion. Reuse Phase 3 transport code only where its trust and integrity model is sufficient; do not conflate content JSON with executable game distribution.

**Acceptance criteria**
- A sample game completes install, verify, update, repair, and launch.
- Manifest authenticity and artifact integrity are verified before installation.
- All writes remain inside the authorized install root, including symlink/junction/reparse-point attack tests.
- Failed or interrupted updates preserve the last valid installation or recover through a tested procedure.
- Disk limits, cancellation, retries, and progress are accurate.
- No administrator privilege is required for ordinary per-user installation.

**Exclusions:** DRM, anti-cheat, payments, proprietary CDN, delta patching before evidence of need, privileged system-wide installation, and launcher self-update.

**Main risks:** Filesystem escape, malicious archives, storage exhaustion, corrupted updates, and trust confusion between manifests and artifacts.

**Phase gate:** Do not distribute this subsystem until adversarial path, integrity, and recovery tests pass.

### 11.7 Phase 5 — Ship and maintain reliably: production release

**Outcome:** Publishers can package and maintain launchers with clear release workflows, trusted application updates, and recoverable failures.

**Work packages**
- **P5-A — Production packaging:** installer/portable decision, application metadata, dependency inventory, clean-machine installation/uninstallation, and upgrade compatibility.
- **P5-B — Publisher release workflow:** versioning, release channels, signing guidance, artifact publishing contract, and reproducible build metadata.
- **P5-C — Launcher updater:** signed release metadata, client trust anchor, artifact binding, downgrade/replay protection, staged apply, rollback, and recovery.
- **P5-D — Security and reliability review:** Studio import, Runtime permissions, networking, game operations, build/export, updater, logs, and dependency review.
- **P5-E — Support readiness:** sanitized diagnostics, crash reporting policy (opt-in), release checklist, migration notes, and documented support boundaries.

**Dependencies and parallelism:** Packaging and support readiness can begin after Phase 1 and mature through Phases 2–4. The updater must not ship before its trust and recovery contracts are approved and the Runtime packaging is stable. Game and launcher update channels must remain distinct.

**Acceptance criteria**
- Clean-machine install, upgrade, uninstall, and recovery tests pass on the supported Windows baseline.
- Release artifacts have documented provenance and integrity checks; signing status is explicit.
- Missing, invalid, tampered, replayed, or unauthorized downgrade metadata is rejected.
- An interrupted/failed launcher update leaves the previous version usable or follows a tested recovery route.
- Key bootstrap, rotation, revocation, and compromise response are documented.
- Logs and diagnostic bundles redact secrets by default.
- All release-blocking security findings are fixed or have an explicitly accepted owner and rationale.

**Exclusions:** LaunchForge-operated CDN/backend, mandatory paid signing service, silent auto-update without publisher opt-in, and automatic multi-platform support.

**Main risks:** Trust bootstrap, signing-key compromise/loss, Windows reputation costs, and update failures that make the launcher unusable.

**Phase gate:** Do not enable production self-updates until signed metadata and recovery behavior pass adversarial tests on clean machines.

### 11.8 Phase 6 — Expand deliberately

**Outcome:** Add capabilities only when user demand and maintenance capacity justify their long-term cost.

**Candidate tracks**
- **P6-A — Permissioned extensions:** versioned extension API, explicit capability grants, isolation, revocation, and compatibility policy.
- **P6-B — Additional renderers:** one adapter PoC at a time, using the same conformance suite and capability declarations.
- **P6-C — Additional platforms:** evaluate Studio and exported Runtime separately for macOS/Linux; do not assume that supporting one implies the other.
- **P6-D — Integrations and services:** additional data sources, publisher integrations, optional cloud/team workflows.
- **P6-E — Compatibility and migration:** project/runtime migration tooling, support matrix, and deprecation policy.

**Dependencies and parallelism:** Stable Phase 5 release process, schema migrations, Runtime API, security model, and named maintenance ownership. Each candidate track is independently prioritized; none is a prerequisite for another.

**Acceptance criteria**
- Extensions have explicit permissions, versioned contracts, and a tested isolation model.
- Each renderer/platform passes conformance, accessibility, packaging, update, and performance tests.
- Existing projects remain compatible or receive explicit migration/unsupported-feature diagnostics.
- Every added platform has separate Studio and Launcher support statements.
- Each feature has demonstrated user demand and a maintainer.

**Exclusions:** Unrestricted plugins, arbitrary native code execution, automatic cross-renderer conversion, unverified platform promises, marketplace, and cloud collaboration without evidence.

**Main risks:** Compatibility fragmentation, plugin attack surface, platform-specific regressions, and support burden.

**Phase gate:** A successful demo is insufficient. Require conformance, security, packaging, migration, and real user workflow evidence.

### 11.9 Dependency and parallel-work rules

| Work | May proceed in parallel with | Must wait for |
|---|---|---|
| Phase 0 candidate PoCs | Security review and initial responsibility mapping | Shared sample and measurement protocol |
| Phase 1 editor UI | Renderer/runtime implementation using fixtures | Frozen schema v1 and component contract |
| Phase 2 assets/themes | Project workflow and accessibility test preparation | Stable project/asset references |
| Phase 3 adapter/binding prototypes | Phase 2 editor improvements | Phase 0 network contract and Phase 1 Runtime boundary |
| Phase 4 manifest/downloader prototypes | Separate test-fixture and threat-model work | Approved filesystem and trust rules |
| Phase 5 packaging documentation | Support/diagnostic preparation | Known MVP package format |
| Phase 6 candidate research | Other independent candidate tracks | Stable public contracts and named owners |

**Integration rules**
- One named architecture/integration owner controls shared schema, public APIs, dependency versions, and release gates.
- Each work package lists owned paths, forbidden paths, public interfaces, tests, and handoff artifacts before implementation.
- Two agents must not independently edit the same schema, renderer registry, Runtime API, or build pipeline.
- Shared-contract changes require an explicit proposal, compatibility impact, migration note, and approval.
- Every handoff includes changed paths, contract changes, tests run/results, known limitations, and next integration steps.
- A phase is not complete when its code is merged; it is complete when its user-visible outcome and acceptance tests pass.

### 11.10 Phase gate checklist

Before starting a phase, confirm:
1. Its user outcome is still valuable and in scope.
2. Required contracts and dependencies are approved.
3. Work packages have non-overlapping ownership.
4. Test fixtures and integration owner are identified.
5. Security and migration impacts are understood.

Before closing a phase, confirm:
1. Acceptance criteria pass on the supported environment.
2. Preview/export or cross-module parity is tested where applicable.
3. Failure, cancellation, and recovery paths are tested.
4. Documentation, diagnostics, and migration notes are updated.
5. Remaining risks have owners and explicit follow-up phases.

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
