# Phase 2 Authoring Specification

> **Status:** Implementation specification / dependency handoff  
> **Parent:** [Issue #4 — Phase 2: Make Authoring Practical](https://github.com/PanDuroDev/LaunchForge/issues/4)  
> **Scope:** Stages 2.1, 2.2, and 2.3  
> **Implementation status:** No Studio/runtime code is implemented by this document.  
> **Compatibility rule:** All wire-format names and API shapes remain subject to approval by the Phase 0/1 integration owner.

This document turns the Phase 2 product requirements into testable authoring behavior. It deliberately does not define a replacement project schema, renderer, editor, or Runtime. Phase 2 implementation must extend the existing Phase 1 contracts rather than create competing ones.

## 1. Repository baseline and constraints

At the time this specification was prepared, `main` contains only:

- `README.md`
- `docs/PROJECT_PLAN.md`

There is no Studio application, Runtime, package manifest, project schema implementation, component registry, renderer adapter, asset service, or test harness in the repository. Phase 1 Issue #3 is still open and has no implementation PR or accepted handoff visible in the repository.

Consequences:

1. There is no executable surface on which to implement or test the authoring features.
2. The project schema, component property contract, renderer capability profile, project/asset references, and undo history interface cannot be safely inferred.
3. The technology direction in `PROJECT_PLAN.md` is provisional. This document does not make it final.
4. This document is useful design work, not evidence that the Studio Beta acceptance criteria have passed.

### Non-negotiable constraints

- Keep one renderer/component implementation for editor preview and exported Runtime wherever practical.
- Keep authored project data renderer-neutral.
- Do not make layout semantics depend on a specific host framework or CSS implementation.
- Do not silently rewrite older MVP projects. Use explicit migrations and preserve unsupported data.
- Keep assets outside the main project document, addressed by stable project-owned references.
- No arbitrary scripts, marketplace, cloud collaboration, timeline editor, custom shaders, or extra production renderer.
- Every imported project/archive is untrusted input.
- Archive extraction must have explicit resource bounds; concrete numeric limits are selected with the approved archive format/library before implementation.
- Shared-contract changes require an explicit proposal, compatibility impact, migration note, and integration-owner approval.

## 2. Phase 2 delivery model

The parent issue defines three ordered stages. Each stage has its own exit gate and handoff. This specification describes the intended behavior for all three, but does not treat later stages as accepted merely because their requirements are documented.

| Stage | Owns | Consumes | Exit gate |
|---|---|---|---|
| **2.1 — Layout foundations** | Layout primitives, sizing, alignment, constraints, supported window presets, deterministic layout behavior | Frozen project/node schema, renderer measurement rules, supported component bounds | Same fixture produces deterministic geometry at documented window sizes and DPI settings |
| **2.2 — Editing workflow, assets, themes, templates** | Selection/edit commands, clipboard, grouping, visibility/locking, assets, theme tokens, templates, project import/export workflows | Accepted 2.1 layout semantics; stable project IDs and asset references; approved component/property contracts | Representative authoring tasks complete in Studio without manual project-file edits |
| **2.3 — Accessibility, localization, beta validation** | Keyboard/focus behavior, Unicode, localization-ready strings, RTL for supported controls, scaling, regression and task validation | Integrated 2.1/2.2 UI and stable project/runtime compatibility contract | Existing MVP projects remain compatible and Studio Beta task/quality gates pass |

P2-A owns layout semantics. P2-B must consume those semantics rather than introducing another layout model. Asset/theme/template submodules may be developed separately only after their shared references and serialization contracts are agreed. Accessibility checks should run throughout implementation, not be postponed to the end.

## 3. Stage 2.1 — Layout foundations

### 3.1 Layout model principles

The editor should feel like a desktop application editor, not a general-purpose pixel canvas. Prefer a small number of composable layout primitives over many overlapping layout modes.

The layout engine must be:

- **Deterministic:** identical project data, renderer version, window size, and DPI inputs produce the same logical geometry.
- **Composable:** containers can contain supported components and other containers.
- **Inspectable:** the editor can explain the effective size, alignment, constraint, and overflow state of a selected node.
- **Renderer-neutral:** the saved meaning is independent of the renderer's native property names.
- **Preview/runtime consistent:** the same layout implementation or conformance-tested implementation is used in preview and export.
- **Backward-compatible:** absent properties in existing MVP projects resolve to documented defaults without rewriting the source document merely because it was opened.

### 3.2 Primitive set

The initial authoring surface should expose only the following primitives:

| Primitive | Purpose | Required behavior |
|---|---|---|
| **Container** | Parent/visual region for child components | Padding, background/border styling through the style system, child clipping/overflow policy, and a layout direction |
| **Vertical stack** | Place children top-to-bottom | Gap, padding, main-axis distribution, cross-axis alignment |
| **Horizontal stack** | Place children left-to-right (or direction-aware in RTL) | Gap, padding, main-axis distribution, cross-axis alignment |
| **Overlay** | Place a small number of intentionally overlapping children | Explicit stacking order and deterministic bounds; later children render above earlier siblings; use only where a launcher UI needs overlays such as a badge over artwork |

Do not add a freeform grid, constraint graph, arbitrary anchors, or a design-tool canvas in this stage. Revisit those only when real launcher tasks demonstrate a need.

### 3.3 Sizing semantics

The inspector should describe sizing in user terms and map it to renderer-neutral semantics:

- **Fixed:** use an explicit logical size.
- **Fit content:** size to the component's intrinsic content, subject to minimum/maximum constraints.
- **Fill available:** begin with the stack's inner main-axis extent after subtracting its leading and trailing padding. Then subtract resolved fixed/fit child sizes and the stack's base gaps. Each fill child has a finite, positive weight; the default weight is **1**. Allocate the remaining space by the active children’s weights.
- **Minimum/maximum:** clamp the proposed fill allocation to the child's minimum and maximum. Resolve constraints iteratively: calculate the aggregate violation across all minimum and maximum violators; when it is positive, freeze only minimum violators, when negative freeze only maximum violators, and when zero freeze all violators. Redistribute the remaining space among children that are not frozen.
- If the combined minimums exceed the available main-axis space, preserve the minimums and report overflow rather than silently shrinking below a minimum. If maximums leave unused space, pass the remainder to the stack's main-axis distribution rule.
- Invalid, non-finite, zero, or negative fill weights are rejected. A minimum greater than its maximum is rejected. Fixed and fit-content sizes are resolved and clamped before fill allocation.

A fixed size is expressed in logical UI units, not physical display pixels. The layout model retains fractional logical-unit values and does not round each child's size independently. The renderer applies DPI/device-scale conversion at the presentation boundary. If physical-pixel snapping is required, calculate shared edges using cumulative positions and a deterministic rounding policy, preserving the total track extent; use logical child order as the stable tie-breaker. Do not serialize device-specific physical pixel values into a project.

Every supported property needs validation for negative sizes, non-finite values, invalid weights, min greater than max, and impossible parent/child combinations. Invalid values must produce an inspector diagnostic and a safe deterministic fallback; they must not crash preview or export.

### 3.4 Alignment, spacing, and overflow

Expose a limited, consistent vocabulary:

- Parent padding and sibling gap.
- Main-axis distribution: start, center, end, and space-between.
- Cross-axis alignment: start, center, end, and stretch where the child supports it.
- Explicit text alignment for text components.
- Child order is the stable **logical** order used by the hierarchy, serialization, keyboard/accessibility reading order, and component identity. RTL changes visual placement, not logical order: for logical children `A, B` in a horizontal RTL stack, `A` remains first in logical and accessibility order but is placed on the right, while `B` is placed to its left. Hit testing follows visible geometry and returns the same stable child identity; it must not rewrite reading order.
- Overlay stacking and hit testing use the same declared child order: later siblings render above earlier siblings. At an overlap, the visually topmost interactive child receives the hit. A non-interactive overlay child is hit-test transparent, so hit testing continues to the next lower interactive child. Preview and exported Runtime must return the same target identity.
- Overflow behavior: visible, clip, or scroll only where the component/runtime supports it.

Do not use the same label for different meanings. For example, container alignment and text alignment must remain distinct in the inspector.

### 3.5 Responsive behavior and window presets

Responsive behavior is a controlled adaptation of the same layout tree, not a separate copy of the design for each window size.

- Start with a small named set of desktop preview presets plus a custom-size preview.
- Layout is resolved from the current available parent size and the authored sizing/alignment rules.
- A project must not depend on a particular monitor resolution.
- If breakpoint-specific overrides are introduced later, they must be explicit, ordered, versioned, and limited to supported properties. Do not silently invent per-preset copies of nodes.
- Window minimum size and resizability are application-shell settings, not ordinary child layout properties.
- Unsupported window sizes or impossible constraints should produce visible diagnostics rather than silent clipping.

**Proposed baseline verification matrix (test fixtures, not a product support promise):**

| Viewport | Scale | Purpose |
|---|---:|---|
| 960 × 600 logical units | 100% | Compact desktop layout |
| 1280 × 720 logical units | 100% | Common desktop preview |
| 1600 × 900 logical units | 100% | Large desktop preview |
| 1280 × 720 logical units | 125% | Fractional DPI scaling |
| 1280 × 720 logical units | 150% | High-DPI scaling |
| 1280 × 720 logical units | 200% | High-DPI scaling |

The integration owner must confirm the supported Windows baseline and actual preset values before these fixtures become a public compatibility promise.

### 3.6 Layout test requirements

- Golden geometry tests for each primitive, sizing mode, axis, alignment, and supported nesting case.
- Padded horizontal-stack fixture: for an outer width of 320 logical units, 16 units of left/right padding, an 80-unit fixed child, two fill children weighted 1:2, and 8-unit base gaps, the fill children receive 64 and 128 units and end at the inner right edge (304). This proves padding is removed before fill allocation.
- Repeat-layout tests proving deterministic results with the same inputs.
- Constraint tests for min/max, zero/negative values, overflow, and insufficient parent space.
- Preview/export parity tests using identical fixtures.
- Overlay hit-test fixture: place two interactive children in overlapping bounds and verify the visually topmost child receives the hit. Repeat with the top child non-interactive and verify the hit passes through to the lower interactive child. Preview and export must return the same target and stable identity mapping.
- DPI tests that verify logical layout remains stable while physical rendering scales.
- RTL tests for direction-aware horizontal flow, without mirroring non-directional content.
- Regression fixtures for existing Phase 1 projects with no new layout properties.

## 4. Stage 2.2 — Editing workflow, assets, themes, and templates

### 4.1 Selection and editing model

The editor should provide a consistent relationship between the viewport, hierarchy, and inspector:

- Selecting a node in either the viewport or hierarchy selects the same stable node ID in both.
- The inspector shows only properties supported by the selected component contract.
- Selection changes must not mutate the project.
- Logical child order remains the source order for hierarchy and accessibility traversal. In an RTL horizontal stack, a two-child fixture with logical order `A, B` places `A` on the right and `B` on the left while keeping the accessible reading order `A, B`. Hit testing each visual rectangle returns that child's stable ID; preview and export must produce the same rectangles and identity mapping.
- Multi-selection is appropriate only when the selected nodes share the properties/operation being edited. The UI must show mixed values instead of silently choosing one node's value.
- Reordering is explicit and must preserve the node's stable identity.
- Hidden nodes remain in the project and hierarchy; locked nodes remain visible/selectable in the hierarchy but cannot be moved or edited accidentally in the viewport.
- Grouping creates a supported container/parent relationship. Ungrouping moves children to the former parent while preserving their order and effective layout wherever the constraints allow.
- Delete and destructive project operations require a recoverable undo command.

Do not add multi-selection merely as a check-box feature. It should support concrete tasks such as aligning several controls, applying a shared style, or moving a coherent group.

### 4.2 Clipboard, duplication, and undo/redo

Editing operations should use an explicit command/transaction boundary.

- A single user intent should normally create one undo step. Dragging a node, for example, should not record every pointer movement as a separate command.
- Undo and redo must restore node properties, order, parent relationships, visibility/lock state, and relevant asset references.
- A command that fails validation must not leave a partially mutated project.
- Duplicating nodes creates new stable IDs for the duplicated nodes and remaps references between the duplicated nodes. References to shared immutable project assets remain valid.
- Pasting inside the same project may reuse existing asset references.
- Pasting/importing into another project must either copy the referenced assets into the destination project or ask the user to resolve them. It must never leave a dangling reference to a source project's private path.
- Clipboard content should be versioned and validated as untrusted input. Unsupported clipboard versions should fail with an actionable message.
- The system clipboard should contain a safe representation of supported node data, not executable content or privileged host instructions.

The exact command API, serialization shape, and history storage strategy must follow the Phase 1 editor-state and project contracts. This document intentionally does not invent those interfaces.

### 4.3 Asset library

Assets remain external files referenced by stable project-owned IDs/paths, consistent with the project plan.

Required behavior:

- Import assets through a Studio-owned workflow; do not persist arbitrary absolute source paths as project references.
- Store imported assets under a project-owned asset root using safe relative paths or the approved asset identifier contract.
- Validate file type using file content as well as extension. Reject malformed files and unsupported types with a clear diagnostic.
- Detect duplicates by content hash where practical, without changing a stable public asset ID merely because a duplicate is found.
- Show asset usage and missing-reference diagnostics.
- Support safe rename/move operations that update references transactionally.
- Preserve required assets through project duplication, archive/export, import, and build/export.
- Never allow an imported archive path to escape the destination root (including traversal paths and symlink/reparse-point cases).
- Bound archive extraction by compressed package size, total uncompressed size, per-entry uncompressed size, entry count, compression ratio, archive nesting depth, path-component depth, and elapsed extraction time. Select and record concrete limits when the archive format/library is approved; do not leave a limit unbounded or rely only on archive metadata.
- Enforce limits while streaming extraction using actual byte and entry counters. When a limit is exceeded, cancel extraction, remove staged output, release temporary resources, and leave the destination project and its references unchanged.
- Canonicalize the destination root and each target path. Verify that each target remains inside the canonical destination immediately before every write; do not rely only on an earlier validation pass.
- Reject symlink, junction, and reparse-point archive entries, or handle them without following a link outside the destination root. Do not follow archive-provided links during extraction.
- Keep binary data out of the main project document.

The initial allowed asset formats and size/dimension limits must be agreed with the renderer and build owner. Do not claim SVG, animated media, remote assets, or arbitrary font formats as supported until the renderer has safe, tested handling for them. Imported font files must retain their license/attribution metadata where supplied; Studio must not imply that import grants redistribution rights.

### 4.4 Theme tokens and reusable style presets

Themes should be project data, not a second independent styling engine.

The minimum token categories to consider are:

- Color roles (surface, text, accent, border, state colors).
- Typography roles (family/reference, size, weight, line height).
- Spacing scale.
- Corner radii.
- Border width/style.
- Shadow/elevation presets, only where the renderer supports them.

Requirements:

- Tokens have stable identities and explicit types.
- Components may reference a token or use an allowed local override.
- Token references resolve through a documented fallback policy. Missing tokens must be diagnosed, not silently replaced with unrelated values.
- Theme edits update all linked components in the preview.
- Import/export of themes is versioned and validates token types, references, and unsupported renderer features.
- A project can override a shared theme without mutating the source preset.
- Style presets remain small and task-oriented. Do not turn the theme editor into a full graphic-design application.

Theme-token names, serialization, cascade/precedence, and migration behavior are shared-contract decisions and require approval before implementation.

### 4.5 Templates and project workflows

Ship only the three templates in the product plan:

1. **Single-game launcher:** one game entry, artwork/content area, and primary action.
2. **Multi-game studio launcher:** a small collection of game entries with consistent cards and a clear selected-game state.
3. **Minimal launcher:** a restrained layout focused on one title and one primary action.

Templates must be editable starting points, not locked pages. All visible content and layout must be changeable through the Studio UI.

Project-management workflows:

- Create, open, rename, duplicate, archive, restore, and delete a project.
- Import and export a complete project with its referenced assets.
- Show project schema/runtime compatibility and actionable migration or unsupported-feature messages.
- Preserve stable identities for the original project during a normal open/save round trip.
- Duplicating a project creates a new project identity and a clear policy for remapping project-local node/asset IDs.
- Archiving must not silently delete source data.
- Import must validate the complete package before replacing an existing project.
- Failed import must not partially overwrite the destination project.
- Existing MVP projects must open without silent schema or layout changes.
- A legacy fixture containing unsupported/unknown fields must preserve their semantic data through normal open/save and project export/import. Changes are allowed only through an explicit, versioned migration that reports what changed.

Templates should be versioned independently from project instances. Updating a built-in template must not silently overwrite projects previously created from it.

### 4.6 Stage 2.2 representative task suite

A user who is not editing project JSON should be able to:

1. Create a project from each of the three templates.
2. Change its title, artwork, primary action label, and basic layout in the Studio.
3. Add, remove, duplicate, group, reorder, hide, and lock supported components.
4. Undo and redo each supported edit without losing assets or stable IDs.
5. Import an image, use it in multiple components, and see missing/unused asset diagnostics.
6. Apply a theme preset, change a shared token, and override one component without changing the whole theme.
7. Duplicate a project and confirm the source project remains unchanged.
8. Export a project, import it into a clean workspace, and confirm its appearance and asset references are preserved.
9. Exercise normal open/save, project duplication, node duplication, cross-project asset reuse/copy, and successful export/import. Assert project, node, and asset identity plus reference remapping against the approved Phase 1 identity/asset-reference contracts. Verify that project duplication uses the approved new project identity, node duplication uses approved new node IDs and internal-reference remapping, and asset reuse/copy follows the approved cross-project policy. Add these assertions only after those Phase 1 contracts are approved; do not define a competing identity policy here.
10. Export/import a legacy fixture containing unsupported fields; compare its semantic data before and after the round trip and allow changes only through an explicit migration.
11. Attempt imports with a malformed package, a missing asset, a schema-version mismatch, and an existing destination project. Verify validation finishes before any replacement; each rejected import leaves the destination project and all its references unchanged.
12. Import adversarial and oversized archives containing traversal paths, symlink/junction/reparse-point entries, excessive compressed or uncompressed size, an oversized entry, too many entries, excessive archive/path nesting, or an extraction timeout. Verify limits are enforced during extraction, cancellation and staging cleanup occur, no link is followed outside the canonical destination root, and the destination project and references remain unchanged.
13. Open a Phase 1 MVP fixture and verify that it displays without an automatic destructive migration.

## 5. Stage 2.3 — Accessibility, localization, and beta validation

### 5.1 Keyboard and focus behavior

Every core authoring task must be possible without a pointer.

Minimum keyboard behavior:

- Predictable Tab/Shift+Tab traversal among major Studio regions and controls.
- Visible focus indicators at all supported themes and window scales.
- Logical arrow-key navigation within the component hierarchy.
- Enter/Space activation for focused controls where appropriate.
- Escape closes transient menus/dialogs or cancels the current interaction without committing a partial edit.
- Delete, duplicate, and other destructive shortcuts apply only to a clearly scoped selection and respect lock state.
- Undo/redo shortcuts are consistent and discoverable.
- Focus is restored to a sensible control after dialogs, import flows, deletion, and selection changes.
- Drag-only interactions must have keyboard alternatives for reorder, alignment, and supported sizing operations.

Shortcuts must not steal text-editing keys while the user is typing in an input or text field. Shortcut conflicts and platform conventions need tests.

### 5.2 Focus order and assistive technology

- All interactive controls expose an accessible name, role, state, and value where applicable.
- Icon-only actions require an accessible label.
- The component hierarchy exposes item labels, nesting, expanded/collapsed state, selection, hidden/locked state, and available actions to assistive technology.
- Selection and validation changes should be announced without flooding the user with repeated messages.
- Color is never the only indicator of selection, error, disabled, or success state.
- Tooltips must not be the only source of instructions or labels.
- Focus order follows the visible task flow, not incidental DOM/component creation order.
- Modal dialogs trap focus appropriately and return focus to their invoking control when closed.

### 5.3 Unicode and localization-ready content

- All project strings and labels must support Unicode end-to-end.
- Do not assume one-byte characters, Latin-only names, or a fixed text width.
- User-authored strings must remain separate from Studio UI copy.
- Avoid concatenating sentence fragments for translation. Prefer complete localization units with named placeholders.
- Locale-sensitive number/date formatting must use an explicit locale and must not change stored numeric/date values.
- Unknown or missing localized strings should resolve through a documented fallback locale and show a useful editor warning where the missing value affects authored output.
- Text measurement and truncation must be tested with mixed Arabic/Latin text, long strings, combining marks, and emoji as content (support for rendering emoji depends on system font coverage).

### 5.4 Right-to-left behavior

RTL is layout direction, not merely right-aligned text.

For supported controls:

- Direction must be explicit or inherited from the project/view locale according to one documented precedence rule.
- Horizontal layout order, navigation flow, and directional affordances should respect the active direction.
- Directional icons (back/forward, previous/next, disclosure/navigation arrows) should mirror when their meaning reverses.
- Non-directional icons (settings, close, image, play, brand marks) must not be mirrored.
- Text alignment should follow the component's explicit setting or the documented start/end rule; do not force every Arabic string to right alignment.
- Media/artwork and user-provided images must not be mirrored automatically.
- Mixed-direction text must preserve Unicode bidirectional behavior.
- Components outside the supported RTL set must report that limitation rather than claim full RTL support.

The initial supported RTL component set must be listed in the implementation's capability profile and covered by screenshots/tests before Studio beta is advertised as RTL-capable.

### 5.5 DPI and scaling

- Keep authored dimensions in logical UI units.
- Scale the editor chrome, hit targets, focus rings, and typography with the supported Windows DPI behavior.
- Avoid rounding intermediate layout calculations. Round only at the renderer/presentation boundary where necessary.
- Test moving the Studio window between monitors with different scale factors if the chosen host supports per-monitor DPI awareness.
- Verify that scaling does not change saved project geometry or produce duplicate undo entries.

### 5.6 Beta validation and compatibility

Run representative user tasks, not just unit tests. At minimum:

- Blank/template project to a customized, previewable launcher.
- Asset import, reuse, duplication, and project export/import.
- Theme change and per-component override.
- Keyboard-only authoring of a simple layout.
- Arabic/RTL authoring and mixed Arabic/Latin text.
- Open and re-save legacy Phase 1 MVP fixtures.
- Preview/export parity at the documented viewport/DPI matrix.

Record the environment, schema version, renderer version, task steps, completion result, defects, and any workaround. A task is not accepted when it succeeds only after manual JSON edits.

## 6. Shared contracts that must be supplied or approved

The following inputs are absent from the current repository. Phase 2 implementation must not fabricate them locally.

| Contract / artifact | Required from Phase 0/1 | Needed by | Required decision |
|---|---|---|---|
| Project schema v1 and migration policy | Frozen schema, version metadata, validation behavior, migration fixtures | All stages | How new layout/theme/template data is represented while preserving old projects |
| Stable node/component IDs | ID creation, duplication, identity guarantees | 2.1, 2.2, 2.3 | Which IDs are regenerated on duplicate/import and how references are remapped |
| Component contract | Property types/defaults/validation/events and supported child relationships | 2.1, 2.2 | Which nodes are containers and which properties are authorable |
| Renderer and capability profile | Selected renderer, measurement/layout behavior, supported fonts/media/input/RTL features | All stages | How preview and export prove parity and report unsupported behavior |
| Asset reference contract | Stable IDs/paths, project asset root, validation and packaging behavior | 2.2 | Import, move, dedupe, cross-project copy, and export semantics |
| Editor state/history API | Selection model, command boundaries, persistence/autosave behavior | 2.2, 2.3 | Transaction model and undo/redo compatibility |
| Theme/style contract | Whether tokens already exist; precedence and fallback rules | 2.2 | Token IDs, types, overrides, preset serialization, migrations |
| Test/build harness | Supported Windows baseline, commands, fixtures, CI checks | All stages | How to run parity, DPI, accessibility, import/export, and clean-checkout tests |

### Contract change procedure

Before implementation changes a shared contract, submit a small proposal containing:

1. Current contract version and exact affected fields/interfaces.
2. Why the existing contract cannot represent the required behavior.
3. Proposed compatible change and default behavior for old projects.
4. Migration and rollback implications.
5. Preview/export and fixture tests.
6. Exact owners/paths affected.

Wait for the integration owner to approve the proposal. Do not add a second competing project schema or renderer API to avoid that review.

## 7. Phase 2 acceptance checklist

### 2.1 — Layout foundations

- [ ] Documented primitives and sizing semantics exist in the implementation and user-facing help.
- [ ] Common layout operations are available through the inspector.
- [ ] Geometry is deterministic at the approved viewport and DPI matrix.
- [ ] Preview and exported Runtime pass the same layout fixtures.
- [ ] Invalid constraints produce actionable diagnostics.
- [ ] Existing MVP fixtures remain unchanged unless the user explicitly edits/migrates them.

### 2.2 — Editing, assets, themes, templates

- [ ] Selection, multi-selection, copy/paste, duplicate, grouping, visibility, locking, and undo/redo work for supported components.
- [ ] Asset import/library validates files and preserves stable references through duplicate/import/export.
- [ ] Theme token updates and component overrides behave predictably.
- [ ] All three starter templates are editable without project-file edits.
- [ ] Project duplicate/archive/import/export workflows are recoverable and preserve required assets.
- [ ] Identity and reference-remapping tests cover normal open/save, project and node duplication, cross-project asset reuse/copy, and successful export/import using only the approved Phase 1 identity and asset-reference contracts.
- [ ] Malformed-package, missing-asset, schema-mismatch, and existing-destination import failures are tested; validation occurs before replacement and rejected imports leave destination data and references unchanged.
- [ ] Adversarial archive fixtures with traversal and symlink/junction/reparse-point entries are rejected or handled without following links outside the canonical destination root; containment is checked immediately before every write.
- [ ] Archive imports enforce approved compressed/uncompressed size, per-entry size, entry-count, compression-ratio, nesting-depth, and extraction-time bounds, cancel and clean staged output on limit violations, and leave the destination unchanged.
- [ ] Legacy fixtures containing unsupported fields preserve semantic data through project export/import unless an explicit, versioned migration is applied.
- [ ] Compatibility view explains project/schema/runtime support and migration requirements.

### 2.3 — Accessibility, localization, beta

- [ ] Core authoring workflows are keyboard accessible with visible focus.
- [ ] Accessible names/roles/states are available for supported controls.
- [ ] Unicode and locale-aware text handling pass mixed-script tests.
- [ ] Supported RTL controls mirror only directional behavior.
- [ ] DPI/scaling does not alter saved logical geometry.
- [ ] Legacy Phase 1 projects, including fixtures with unsupported fields, preserve semantic data through normal open/re-save. Differences are allowed only through an explicit, versioned migration; this check belongs to 2.3, not the 2.1 layout gate.
- [ ] Representative user tasks pass without manual JSON/source edits.
- [ ] Limitations and unsupported components are documented.

## 8. Explicitly deferred

Do not expand Phase 2 into:

- General-purpose graphic/design tooling.
- Freeform canvas or arbitrary coordinate/constraint graph.
- Timeline animation, custom shaders, or 3D authoring.
- Public template/theme marketplace.
- Cloud collaboration, accounts, or shared workspaces.
- Arbitrary plugins or custom component code.
- Additional production renderers or non-Windows support.
- Remote asset hosting or data connections, which belong to the appropriate later phase.

## 9. Current handoff and next actions

### What this branch delivers

- A concrete behavior specification for 2.1, 2.2, and 2.3.
- A staged test matrix and representative authoring-task suite.
- A list of missing Phase 0/1 inputs and shared-contract decisions.
- An explicit boundary between proposed semantics and approved serialized/API contracts.

### What it does not deliver

- No Studio/editor or Runtime implementation.
- No project schema or component contract changes.
- No asset service, theme engine, template implementation, or migration code.
- No executable tests; the repository currently has no application code or test harness to run them against.

### Required next implementation sequence

1. Integration owner supplies/approves the Phase 1 project, node, component, renderer, asset, and editor-state contracts.
2. Implement **2.1** against those contracts and run the layout/parity/DPI suite. Obtain explicit exit-gate review.
3. Implement **2.2** using the accepted 2.1 layout semantics and frozen asset/theme/template interfaces. Obtain explicit exit-gate review.
4. Implement **2.3** against the integrated UI, then run the full regression and representative-user-task suite.
5. Close Issue #4 only after the Studio Beta acceptance checklist passes.

**Handoff status:** Documentation is ready for review. Phase 2 implementation and beta acceptance remain blocked by the absent application and Phase 1 contracts.
