# Phase 0 contract proposal: Project, renderer, Runtime, and build v1

- **Status:** Frozen candidate for integration-owner review; not approved for Phase 1 until the PR is accepted.
- **Scope:** Only the minimum end-to-end MVP surface. This is not a general plugin or web-app schema.

## 1. Project document

The normative machine-readable shape is `poc/contracts/project-v1.schema.json`. The executable semantic validator used by the spike is `poc/shared/contract.mjs`.

Top-level fields:

| Field | Contract |
|---|---|
| `format` | Literal `launchforge.project` |
| `schemaVersion` | Integer exactly `1` for this contract |
| `projectId` | Stable UUIDv4, generated once and retained across edits/exports |
| `name` | User-facing project name, 1–80 characters |
| `window` | Title, required `iconAssetId`, default/minimum dimensions, and resizable flag; validated bounds are in schema v1 |
| `theme` | Three named color tokens: `surface`, `text`, `accent`; RGB hex only |
| `assets` | Stable asset ID, kind (`image` or `applicationIcon`), and portable relative project path |
| `games` | Local game metadata with stable ID and `coverAssetId` reference |
| `components` | Exactly one root container in v1; child tree is capped and typed |

The schema is intentionally constrained. Schema v1 supports `container`, `text`, `image`, `button`, and `gameCard`; it does not support arbitrary HTML, CSS, JavaScript, remote data binding, plugins, custom components, or a general-purpose layout language.

## 2. Stable identifiers and assets

- IDs are UUIDv4 strings and are assigned when an entity is created. They are not derived from names, list position, display order, or file path.
- IDs are unique across the project, assets, games, and components in one project document.
- Renaming or reordering an entity does not change its ID.
- Components reference assets and games by ID, never by array index or user-visible name.
- Asset paths are relative to the project root and use `/` separators. Schema v1 accepts one filename under `assets/` only. Absolute paths, drive/UNC/device paths, `..`, backslashes, ADS syntax, encoded separators, and reserved Windows device names are rejected.
- A lexical path check is not sufficient at runtime. The Rust host must canonicalize the final destination immediately before access and reject symlink, junction, or reparse-point escapes from the authorized project/install root.
- Export records the resolved asset inventory and SHA-256 values in build metadata. The main project document does not embed binary assets.

### Application icon contract

- `window.iconAssetId` is required and must reference one project asset whose kind is exactly `applicationIcon`. It is a stable UUID reference, not a user-supplied path.
- An `applicationIcon` asset must use one plain project-relative filename under `assets/` with a lowercase `.ico` extension. An ordinary `image` asset cannot be used as the application icon.
- The Windows ICO must contain 16, 24, 32, 48, 64, and 256 pixel image entries. The build validates the ICO directory and each entry's bounds before native compilation. This follows Tauri's [Windows icon requirements](https://v2.tauri.app/develop/icons/).
- The Windows build resolves the asset ID from the validated project, canonicalizes its path under the project assets root, and stages those exact bytes as `src-tauri/icons/icon.ico`. Tauri embeds that resource into the portable executable; the launcher does not depend on a separate icon file at runtime.
- Build metadata records `applicationIconAssetId` and `applicationIconSha256`. The icon is also included in `assetManifestSha256`. A missing, malformed, or non-`applicationIcon` reference blocks export.

This is a pre-approval completion of the v1 candidate, not a migration of released data. No project schema has been accepted or shipped yet. Once this v1 contract is approved, changing the icon field or its required file format is a breaking schema change and requires an explicit migration/version proposal.

## 3. Component and layout contract

Every component has `{ id, type, props }`. Only containers have `children`. Component type and properties are allowlisted; unknown types and unknown actions fail validation.

- `container`: `axis` (`vertical` or `horizontal`), integer `gap` and `padding` in the documented range, and a theme-token background.
- `text`: literal text or a local typed binding to one game's `title` or `description`, plus font size and a theme-token color.
- `image`: `assetId`, required accessibility `alt`, and `fit` (`cover` or `contain`).
- `button`: a label and an allowlisted action. The PoC emits typed `navigate(target)` and `launchGame(gameId)` actions. It does not start a process. The MVP Runtime resolves the game ID to a preconfigured trusted launch target; the component cannot supply an executable path, shell command, or arbitrary argument string.
- `gameCard`: a `gameId` reference resolved from local project data.

Layout units are CSS pixels at the renderer's CSS-pixel coordinate system. The MVP has no arbitrary absolute positioning, transforms, user-supplied CSS, script execution, or implicit renderer fallback. Supported capabilities must be declared by each build target, and unsupported required features block export.

## 4. Renderer contract

Logical interface:

```ts
interface RendererAdapter {
  readonly id: string;
  readonly contractVersion: 1;
  validate(project: ProjectV1): Diagnostic[];
  render(project: ProjectV1, mount: HTMLElement, context: RenderContext): Dispose;
}
```

The production preview and exported Runtime must use the same renderer package version and component definitions. Differences are allowed only in the host adapter supplied through `RenderContext`, not in layout, binding, or component rendering behavior. `RenderContext` may expose typed actions and diagnostics; it must not expose generic filesystem, shell, process, credential, or network access.

Build-time target selection is outside the authored project. A project does not claim that every renderer supports every feature. The target declares a capability profile and export fails on unsupported required features.

The POC provides the executable baseline for this rule: both preview and export call `shared/app.mjs` and `shared/renderer.mjs`; the exporter copies those exact files into `dist/`, and a test compares their SHA-256 hashes and rendered output.

## 5. Runtime host API boundary

The MVP host surface is capability-oriented, not a generic bridge:

| Capability | Allowed contract | Explicitly forbidden |
|---|---|---|
| Project / asset loading | Load the selected project and assets by stable ID after containment checks | Arbitrary frontend-provided absolute file reads/writes |
| Window | Apply validated project window title/size/resizability | Arbitrary native window or OS manipulation |
| Game launch | `launchGame(gameId)` resolves a preconfigured trusted launch target on the host side | Frontend-supplied executable path, shell command, arbitrary process spawn, unvalidated command line |
| Secure storage | Scoped get/set for explicitly classified user credentials only, when a later MVP feature requires it | Publisher/server secrets in a client package; generic secret dump/export |
| Diagnostics | Structured event codes and sanitized context | Tokens, credentials, full private paths, arbitrary payload logging |
| Network | No remote network capability in the Phase 1 MVP | Generic HTTP, private database access, arbitrary URL fetches from visual actions |

The game-launch resolver and exact first-run path selection UX remain Phase 1 implementation details. The invariant is frozen now: UI actions identify a configured game by ID; only the host decides whether/how that game may be launched.

## 6. Build/export interface

Logical request:

```ts
interface BuildRequestV1 {
  projectPath: string;
  targetId: "windows-tauri-webview2";
  outputDirectory: string;
  distribution: "portable";
}
```

Logical result:

```ts
interface BuildResultV1 {
  buildId: string;
  artifactPath: string;
  projectSchemaVersion: 1;
  runtimeVersion: string;
  rendererId: string;
  rendererContractVersion: 1;
  assetManifestSha256: string;
  applicationIconAssetId: string;
  applicationIconSha256: string;
  diagnostics: Diagnostic[];
}
```

The build request deliberately does not duplicate the icon path or ID: it resolves the single source of truth through `projectPath` → `window.iconAssetId`. `BuildResultV1` returns the resolved icon asset ID and SHA-256 so the embedded Windows resource can be audited against the project. The initial distribution format is **portable** for the MVP spike; do not add an installer until the portable package is stable. The actual Windows package format is not validated by the browser-only PoC. Export must validate the project, resolve the complete asset set, scan for prohibited secrets, verify target capabilities, copy the shared renderer/runtime, and write deterministic metadata. A failure in any security-critical step blocks export.

## 7. Versioning and migration policy

- Project schema, Runtime API, renderer contract, and build manifest are separately versioned.
- `schemaVersion` is an integer; changing required fields, meaning, or compatibility in a breaking way requires a new schema version.
- Unknown future schema versions are rejected. There is no best-effort downgrade or silent field dropping.
- Migrations are explicit, ordered, deterministic transformations (`N -> N+1`) with fixture coverage. They preserve IDs and asset identity.
- Studio writes a migrated copy only after successful validation and retains a recoverable backup of the original. Export never mutates the source project.
- Runtime compatibility is expressed in build metadata; old projects are not silently paired with an incompatible Runtime.

## 8. Diagnostics contract

A diagnostic has `code`, `severity` (`info|warning|error`), `message`, and optional `entityId`/field path. Messages must be actionable and must not include secret values. Unsupported required capabilities and schema errors are build-blocking. Warnings do not override security errors.

## 9. Compatibility impact

This proposal establishes new v1 contracts in a repository that currently has no implementation or project files. It does not migrate existing user data. Once accepted, Phase 1 must implement these definitions rather than creating parallel schema, component, or Runtime API variants. Any change after acceptance requires a proposal describing compatibility, migration, fixtures, and the affected Phase 1 work packages.
