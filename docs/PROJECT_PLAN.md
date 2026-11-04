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

### 6.9 Preview, testing, and export

The preview should use the same rendering and component behavior as the exported runtime wherever practical. Avoid maintaining two separate implementations that drift apart.

Provide:

- Live viewport preview.
- Multiple window-size presets.
- Sample-data mode and connected-data mode.
- Connection tests.
- Action/event testing.
- Game workflow testing with safe test fixtures.
- Build validation and actionable error messages.

Build outputs should include:

- A Windows installer.
- A portable package if feasible.
- Application name, icon, publisher metadata, and version.
- Bundled runtime and required assets.
- Optional launcher update configuration.

## 7. High-level architecture direction

Keep these boundaries explicit:

- **Studio UI:** project authoring and editing.
- **Project schema:** versioned declarative representation of layouts, components, themes, bindings, actions, and capabilities.
- **Preview host:** renders a project using the runtime's renderer and test services.
- **Runtime:** renders and executes a built project.
- **Data adapters:** retrieve and normalize external content.
- **Game service:** installation, verification, update, and launch operations.
- **Launcher updater:** updates the launcher application.
- **Build pipeline:** validates and packages a project.

Prefer a versioned, declarative project format over generating arbitrary application source code from every visual edit. The project format should be inspectable, portable, and migratable.

The exact programming language, UI framework, rendering technology, and installer technology remain open technical decisions. They should be selected after a small technical spike proves that the editor, preview, runtime, and packaging can share the required component model.

## 8. Security and trust boundaries

Security requirements are part of the product, not a later polish task.

- Never embed private API keys, database passwords, or signing secrets in a launcher package.
- Treat API responses and downloaded manifests as untrusted input.
- Verify downloaded files using cryptographic hashes and authenticated release metadata.
- Use HTTPS for remote connections.
- Store user-specific secrets in the operating system's secure credential storage when required.
- Restrict code extensions and expose capabilities through explicit permissions.
- Do not allow arbitrary UI code to execute shell commands or access arbitrary files by default.
- Validate project files and imported assets.
- Make external URL opening and privileged actions explicit.
- Provide clear publisher/update trust information to end users.

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

The MVP should prove one complete workflow: a developer can create a branded launcher visually, connect simple content, preview it, and export a working Windows application.

### MVP must include

- Windows-only Studio.
- One versioned Launcher Project format.
- A small component set: text, image, container, button, game card, and basic navigation.
- Visual hierarchy and properties inspector.
- Live preview using the runtime renderer.
- Theme tokens and basic layout controls.
- REST/JSON connection with sample response inspection and field mapping.
- Basic events/actions, including navigation and external URL.
- A single-game launcher template and a multi-game template.
- A bundled runtime and Windows build/export.
- Basic validation and useful error messages.

### MVP should defer

- Full game patching and delta updates.
- Multiple authentication providers and complex OAuth flows.
- Arbitrary custom code plugins.
- Template marketplace.
- Cloud project collaboration.
- Multi-user team permissions.
- Analytics and telemetry dashboards.
- macOS and Linux builds.
- Advanced animation timelines and custom shaders.

A small game install/launch proof-of-concept can be built as a separate technical spike, but it should not block validating the visual editor and export pipeline.

## 11. Proposed development phases

### Phase 0 — Technical validation

- Choose candidate language, UI framework, renderer, and packaging path.
- Define a minimal project schema.
- Render the same sample project in both preview and standalone runtime.
- Verify that a project can be packaged with a bundled runtime.
- Record performance and memory use on a modest Windows PC.

**Exit criteria:** One simple project renders consistently in Studio preview and as an exported application.

### Phase 1 — Editor foundation

- Project creation and persistence.
- Component tree and selection.
- Add, remove, reorder, and configure components.
- Basic layout and theme editing.
- Undo/redo.
- Live preview.

**Exit criteria:** A user can build and save a basic static launcher without writing code.

### Phase 2 — Data and interactions

- REST/JSON connection workflow.
- Response inspection and field mapping.
- Loading/error/empty states.
- Basic event/action editor.
- Single-game and multi-game templates.

**Exit criteria:** A launcher can display remote content and respond to basic user interactions.

### Phase 3 — Runtime and distribution

- Runtime validation and project compatibility.
- Windows packaging and application metadata.
- Installer and portable output.
- Basic launcher self-update design and proof-of-concept.

**Exit criteria:** A user can export and run an independent launcher on a clean Windows environment.

### Phase 4 — Game operations

- Game manifests and version model.
- Download manager.
- Install, pause/resume, verify, repair, and launch.
- Interrupted-update recovery.
- Game status integration with UI components.

**Exit criteria:** A test game can be installed, verified, updated, and launched reliably.

### Phase 5 — Hardening and expansion

- Security review.
- Performance and accessibility improvements.
- Project migration tooling.
- More components and data adapters.
- Additional operating systems only after the Windows workflow is stable.

## 12. Risks and unresolved decisions

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

## 13. Success criteria

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

## 14. Current scope decisions

The following decisions are the working baseline for initial development:

- Product category: visual game-launcher development platform.
- Initial platform: Windows desktop.
- Primary user: indie developers and small studios.
- Main differentiator: visual editor with real-time preview and independent application export.
- Multiple launchers: separate Launcher Projects managed by one Studio.
- Runtime: shared codebase, bundled with each exported launcher initially.
- Data: API/JSON-first, with guided visual mapping.
- Game management: optional subsystem, not mandatory for every project.
- Custom code: advanced extension path, not required for the MVP.
- No marketplace, social network, game store, or LaunchForge-hosted game infrastructure in the MVP.

This document defines product intent and scope. It does not prescribe a final technology stack or claim that the architecture has been technically validated.
