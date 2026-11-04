# Phase 2.1 Shared Layout Contract Proposal

- **Status:** Non-binding RFC for integration-owner review.
- **Owner:** Phase 2 / AI 3 (P2-A).
- **Parent:** [Issue #4 — Phase 2: Make Authoring Practical](https://github.com/PanDuroDev/LaunchForge/issues/4).
- **Depends on:** Accepted Phase 0 project/renderer contracts and accepted Phase 1 project/component foundation.
- **Implementation status:** None. This document does not change the project schema, renderer, Runtime, or Phase 2 reference prototype.

## 1. Decision requested

Phase 2.1 needs layout data that the current Phase 0 candidate schema cannot represent. The candidate v1 container currently stores `axis`, integer `gap`, scalar `padding`, and a theme background. The Phase 2.1 behavior specification additionally requires fixed/fit/fill sizing, min/max constraints, main-axis distribution, cross-axis alignment, overlay placement, direction-aware ordering, and deterministic overflow behavior.

Because the candidate v1 schema rejects unknown fields, adding those fields to v1 would make projects unreadable by existing v1 validators. The recommendation in this RFC is therefore:

1. Keep Project Schema v1 unchanged.
2. Add the layout model in a new Project Schema v2 with an explicit v1-to-v2 migration.
3. Version the renderer layout contract independently and require the same implementation/version in Studio preview and exported Runtime.
4. Define one logical layout unit as exactly one CSS pixel in the renderer's CSS coordinate system. Device-pixel scaling remains a renderer/presentation concern.

This RFC is a proposal only. The integration owner must approve the shape, versioning, and migration before any implementation changes a shared contract.

## 2. Unit and viewport semantics

Use **logical layout units (LU)** for authored geometry, with the explicit conversion:

`1 LU = 1 CSS px`

A CSS pixel is a logical renderer unit, not a physical monitor pixel. The renderer receives a viewport in CSS pixels. Windows DPI/device scale converts those logical coordinates to physical display pixels only at the presentation boundary.

Normative consequences proposed here:

- Widths, heights, gaps, padding, minimums, maximums, intrinsic measurements, and resolved rectangles use LU.
- Fractional finite values are allowed in Schema v2; values are not rounded during layout solving.
- No authored geometry stores physical-pixel values or a monitor-specific scale factor.
- When the presentation layer must snap to physical pixels, it rounds shared cumulative edges using one documented deterministic policy. It must not independently round each child's width and position.
- Preview and exported Runtime receive equivalent logical viewport inputs for parity tests. A DPI change may alter physical rasterization, but must not mutate saved geometry.

This reconciles the current v1 phrase "CSS pixels at the renderer's CSS-pixel coordinate system" with the Phase 2 specification's "logical UI units". The missing point is the explicit 1:1 definition and permission for fractional values in the new layout contract.

## 3. Proposed Schema v2 shape

The names below are proposed wire-format names, not approved identifiers.

### 3.1 Container layout

Move the container's layout behavior into one discriminated `props.layout` object. This avoids keeping `axis`, `gap`, and `padding` as competing sources of truth.

Stack example:

```json
{
  "type": "container",
  "props": {
    "background": "surface",
    "layout": {
      "kind": "stack",
      "axis": "vertical",
      "gap": 12.5,
      "padding": {
        "top": 16,
        "right": 20,
        "bottom": 16,
        "left": 20
      },
      "justify": "start",
      "alignItems": "stretch",
      "direction": "inherit",
      "overflow": "visible"
    }
  },
  "children": []
}
```

Proposed `stack` fields:

| Field | Type | Proposed semantics |
|---|---|---|
| `kind` | `"stack"` | Selects stack layout. |
| `axis` | `"horizontal" | "vertical"` | Main axis. |
| `gap` | finite non-negative LU number | Base space between logical siblings. Default 0. |
| `padding` | four finite non-negative LU numbers | Content insets. Default 0 on each edge. |
| `justify` | `start | center | end | space-between` | Main-axis distribution of remaining space. Default `start`. |
| `alignItems` | `start | center | end | stretch` | Cross-axis alignment. Default `stretch`. |
| `direction` | `inherit | ltr | rtl` | Direction used by logical start/end and horizontal placement. Default `inherit`. |
| `overflow` | `visible | clip` | Explicit initial overflow policy. Default `visible`. |

`scroll` is intentionally excluded from the initial contract. It requires a separately defined scroll container, input, focus, and Runtime behavior; adding the string before those capabilities exist would be decorative schema.

Overlay example:

```json
{
  "type": "container",
  "props": {
    "background": "surface",
    "layout": {
      "kind": "overlay",
      "padding": {
        "top": 8,
        "right": 8,
        "bottom": 8,
        "left": 8
      },
      "direction": "inherit",
      "overflow": "clip"
    }
  },
  "children": []
}
```

Overlay has no axis, gap, or main-axis distribution. Every direct child is independently placed in the same padded content rectangle.

### 3.2 Child sizing and placement

Schema v2 should add a common `layout` member to each non-root component node. The root component continues to receive the renderer viewport as its bounds and does not need a parent-relative size.

```json
{
  "id": "22222222-2222-4222-8222-222222222222",
  "type": "image",
  "props": {
    "assetId": "33333333-3333-4333-8333-333333333333",
    "alt": "Game artwork",
    "fit": "cover"
  },
  "layout": {
    "width": { "mode": "fixed", "value": 160, "min": 120, "max": 240 },
    "height": { "mode": "fit", "min": 0, "max": 180 }
  }
}
```

Proposed dimension union:

| Mode | Required field | Resolution |
|---|---|---|
| `fixed` | `value` | Use the requested LU size, clamped to `min`/`max`. |
| `fit` | none | Use the component's intrinsic size, clamped to `min`/`max`. |
| `fill` | `weight` | Participate in weighted allocation on a stack main axis; fill the available cross-axis/overlay extent when applicable, subject to bounds. |

All modes accept optional finite non-negative `min` (default 0) and optional finite non-negative `max`; when both exist, `max >= min` is required. Fixed `value` is finite and non-negative. Fill `weight` is finite and strictly positive; the default weight is 1 if the owner chooses to omit it.

For overlay children, the same `layout` object additionally accepts `alignX` and `alignY`, each one of `start | center | end | stretch`. These fields are valid only when the direct parent uses `kind: "overlay"`; the semantic validator must reject them under a stack. Stack children use their parent's `alignItems` value.

Schema validation should enforce the structural union. Cross-field and parent/child rules (positive fill weight, min/max ordering, overlay-only alignment, component references, and global numeric finiteness as represented by the host language) remain semantic-validator responsibilities.

## 4. Layout resolution rules

The following behavior carries forward the approved Phase 2 authoring specification and the existing reference prototype. It is still subject to integration-owner approval.

### 4.1 Stack sizing

1. Compute the inner content rectangle after subtracting all four padding insets.
2. Resolve fixed and fit children on the main axis and clamp them to their bounds.
3. Subtract those sizes and the base gaps from the available main-axis extent.
4. Divide the remaining non-negative extent among fill children by positive weight.
5. Resolve min/max violations iteratively. Freeze the bound family that drives the aggregate violation, then redistribute the remaining space among active fill children. Preserve minimums if they cannot all fit and report overflow.
6. If maximums leave unused space, apply `justify` to the remaining extent. `space-between` adds equal space between logical siblings; it does not replace the authored base gap.
7. Resolve the cross axis using each child's sizing mode and `alignItems`. A stretched/fill child remains subject to its maximum; a capped child keeps its requested start/center/end alignment.

Invalid sizes, non-finite values, negative gap/padding, invalid weights, and `min > max` must produce deterministic diagnostics and must not crash preview or export.

### 4.2 Logical order and RTL

The serialized child array is the stable logical order. Hierarchy order, keyboard traversal, accessibility reading order, and identity are derived from that array.

For a horizontal RTL stack, the first logical child is placed on the right and later children proceed left. RTL does not reverse the serialized array or accessible reading order. For vertical stacks, logical horizontal start/end alignment follows the active direction. Overlay start/end alignment follows direction on the horizontal axis only.

Only directional affordances are mirrored. Artwork, non-directional icons, and user media are not mirrored by layout direction.

### 4.3 Overlay, painting, and hit testing

- Every overlay child is resolved independently within the same padded content rectangle.
- Serialized child order remains stable; later siblings paint above earlier siblings.
- At an overlap, the topmost interactive child receives the hit.
- A non-interactive top child is hit-test transparent, so hit testing continues to the next lower interactive child.
- Preview and exported Runtime must return the same stable component identity for the same pointer location and logical geometry.

### 4.4 Overflow

Minimum constraints are never silently violated to hide overflow. A layout result reports overflow by axis. Initial `visible` and `clip` policies must have matching preview/export behavior. Scroll is deferred as stated above.

## 5. Intrinsic measurement and renderer contract

The Phase 2 reference accepts intrinsic width/height as inputs. Production needs a normative source for those values; otherwise FIT depends on unspoken browser defaults.

The renderer contract proposal must define an intrinsic measurement operation (or an equivalent deterministic adapter contract) with:

- A component type and validated component properties.
- The available logical constraints on each axis.
- The active theme/font and relevant asset metadata.
- A finite logical size result or a structured diagnostic.
- A documented rule for text wrapping, line height, image aspect ratio, and nested-container measurement.

Measurement must use the same renderer package and font/resource policy in Studio preview and exported Runtime. Repeated measurement with identical inputs must be deterministic. Layout resolution must not depend on whichever browser happens to host the editor.

The current `RendererAdapter` v1 shape exposes `validate` and `render`, but does not name intrinsic measurement. The integration owner should either version the renderer contract to include this responsibility or approve a versioned capability that the same renderer implementation exposes to both preview and export. Do not add a second renderer implementation just for layout.

## 6. Versioning and v1 compatibility

The candidate Project Schema v1 is strict (`additionalProperties: false`) and its renderer semantics do not include the new layout model. This proposal therefore does not add optional v2-looking fields to a v1 document.

Recommended migration path:

1. A project using `schemaVersion: 1` is migrated explicitly to schema v2 using a versioned, deterministic `1 -> 2` migration.
2. Preserve project, component, game, and asset IDs; preserve all references and non-layout authored values.
3. Map v1 `axis` to stack `axis`, and scalar `padding` to four equal insets. Preserve `gap` and theme background.
4. Preserve the v1 renderer's actual default child sizing/alignment behavior. Do **not** blindly map every old child to `fit`: the current CSS renderer uses browser flex defaults and component-specific styles, which are not proven equivalent to the Python reference's sizing modes.
5. Before choosing a direct conversion, compare every accepted Phase 1 fixture at the same logical viewport in the v1 and v2 renderers. If exact conversion cannot be demonstrated, use an explicit migration-only legacy layout compatibility mode until the user edits that container; editing converts it to explicit v2 stack properties.
6. Never rewrite the source project simply because it was opened. Migration writes a new/backup-protected copy only after successful validation, according to the accepted ProjectStore migration policy.

The Phase 1 project foundation currently rejects non-v1 versions and does not implement migration. Its owner must accept the migration interface and fixture expectations before Phase 2 implementation depends on it.

## 7. Preview/export and acceptance tests

The existing Python reference remains a behavior prototype, not a production contract or renderer. Once the owner approves the proposal, the implementation should consume the same conformance fixtures in Studio preview and exported Runtime.

Minimum fixture groups:

| Group | Required checks |
|---|---|
| Schema/migration | v1 fixture opens unchanged; explicit v1-to-v2 migration preserves IDs/references and semantic data; unknown future versions fail safely. |
| Units | Fractional LU, logical viewport input, and 100/125/150/200% DPI presentation do not mutate saved geometry. |
| Stack | Horizontal/vertical, fixed/fit/fill, weighted allocation, min/max redistribution, padding, gap, all main/cross alignments, and overflow. |
| Overlay | Independent alignment, paint order, topmost hit, non-interactive pass-through, and stable component identity. |
| RTL | Logical order remains unchanged while horizontal visual placement and start/end alignment are direction-aware. |
| Measurement | Text wrapping, image intrinsic dimensions, nested FIT containers, unavailable fonts/assets, and deterministic repeated measurement. |
| Parity | The same fixtures and logical viewport inputs produce equivalent geometry and hit targets in preview and exported Runtime. |

Use the viewport/DPI matrix already documented in the Phase 2 specification. The owner must confirm the supported Windows baseline before the matrix becomes a product-support promise.

## 8. Ownership and approval checklist

This RFC is ready for review as a proposal, but it is not an implementation authorization.

| Decision | Recommendation | Owner decision |
|---|---|---|
| Project schema version | Add Schema v2; leave strict v1 unchanged. | Pending |
| Unit definition | 1 LU = 1 CSS px; DPI conversion only at presentation. | Pending |
| Container serialization | Discriminated `props.layout` with `stack` and `overlay` variants. | Pending |
| Child sizing | Common non-root `layout.width`/`layout.height` dimension unions. | Pending |
| Intrinsic measurement | Add a renderer-v2 operation or a versioned capability shared by preview/export. | Pending |
| v1 defaults | Prove direct migration against fixtures; otherwise keep an explicit migration-only compatibility mode. | Pending |
| Overflow | Ship `visible` and `clip`; defer scroll. | Pending |
| Renderer parity | One renderer package/version and one conformance fixture set. | Pending |

### Required upstream gates

- PR #16 (Phase 0) must be accepted, including the final schema/renderer contract and Windows/clean-machine decisions.
- P1-A (Phase 1.1) must be accepted against that exact contract, including its test and migration ownership.
- The integration owner must approve this RFC's field names, schema/renderer versioning, unit semantics, and migration strategy.
- Only then may P2-A implement the approved contract and integrate the layout reference into Studio/Runtime.

No Phase 2.2 work is authorized by this proposal. The 2.1 exit gate still requires production integration, deterministic layout, Preview/Export parity, and Windows DPI evidence.
