# Phase 1 Implementation Readiness

> **Status:** Preparation only — Phase 1 implementation has not started.
> **Scope:** LaunchForge Phase 1 / Issue #3.
> **Branch:** `ai2/phase1-readiness`
> **Baseline:** `main` at `3d24d286118892b948424c547f91db3d1ce7ed84`.

## Purpose

This document records what can safely be prepared for Phase 1 while Phase 0 work proceeds independently. It does not select technologies, define shared interfaces, approve contracts, or replace the Phase 0 decision records.

The parallel-work instruction permits preparation and independent Phase 0 work. It does not remove the technical dependencies inside the Phase 1 critical path:

`Phase 0 contracts → P1-A project foundation → P1-C renderer/component contract → P1-D Runtime → P1-E export → P1-F end-to-end gate`

P1-B may be developed against fixtures after the schema and component contracts are frozen. The ordered Phase 1 stages in Issue #3 remain separate reviewed handoffs.

## Repository baseline

At the baseline commit, the repository contains:

- `README.md`
- `docs/PROJECT_PLAN.md`

There is no application source tree, dependency manifest, test project, build script, renderer implementation, Runtime, sample project, CI workflow, or Windows packaging configuration yet.

Consequently, no application test or build command can currently be run from this checkout. This PR adds readiness documentation only; it does not claim that any MVP behavior has been implemented or tested.

## Phase 0 inputs required by Phase 1

The following artifacts are required before their dependent implementation is safe. Phase 1 should consume the approved versions rather than independently defining substitutes.

| Required artifact | Minimum information Phase 1 needs | Consumed by |
|---|---|---|
| Stack decision record | Selected Studio host/UI, Runtime/core technology, renderer, toolchain versions, fallback, and evidence from the Phase 0 PoC | All implementation packages |
| Project schema v1 | Version field, project metadata, stable ID rules, node tree, typed component properties, layout semantics, asset references, compatibility policy, validation errors, and migration rules | P1-A, P1-B, P1-C, P1-D, P1-E |
| Schema fixtures | Valid starter project, invalid project examples, missing-asset case, and round-trip expectations | P1-A, P1-B, P1-F |
| Component contract | Component identifiers, defaults, editable properties, validation, events/actions in MVP scope, supported states, and versioning | P1-B, P1-C |
| Renderer contract | Adapter lifecycle, supported components, capability declaration, preview integration, and export/runtime integration | P1-C, P1-D, P1-E |
| Runtime API contract | Project loading, diagnostics, capability permissions, window settings, configured game launch, and structured failure results | P1-D, P1-E, P1-F |
| Process-launch policy | Canonical executable-path validation, structured argument handling, working-directory policy, imported-project approval, and explicit rejection of shell/URL-handler launches | P1-D, P1-F |
| Build interface | Deterministic input/output contract, selected renderer/runtime versions, asset resolution, app metadata, portable output format, and build diagnostics | P1-E, P1-F |
| Security and test baseline | Secret classes/pattern configuration, export scan rules, logging redaction, supported Windows baseline, clean-machine provisioning, and test strategy | P1-D, P1-E, P1-F |
| Phase 1 ownership map | Named integration owner, owned/forbidden paths, interface owners, test fixtures, and review gates | All packages |

A prose technology preference in the product plan is not a substitute for the Phase 0 decision record. Likewise, a draft schema or an unreviewed prototype API is not an approved contract.

## Latest Phase 0 candidate snapshot (2026-11-04)

A Phase 0 candidate is now available on the separate branch `phase0/de-risk-architecture` in [PR #16](https://github.com/PanDuroDev/LaunchForge/pull/16). These artifacts are useful implementation inputs, but their own status says they are **not approved for Phase 1 until integration-owner review**. They are not present on `main`.

| Candidate artifact | Current location | Phase 1 use |
|---|---|---|
| ADR-0001 stack decision | `docs/phase-0/ADR-0001-stack-selection.md` | Tauri v2 + Rust host + TypeScript/React; WebView2 + .NET fallback |
| Schema v1 | `poc/contracts/project-v1.schema.json` | Normative proposed project shape |
| Semantic validator | `poc/shared/contract.mjs` | Cross-field and project-specific validation beyond JSON Schema |
| Shared renderer | `poc/shared/renderer.mjs` | Host-neutral DOM renderer for preview/export |
| Contract/security definition | `docs/phase-0/contracts-v1.md`, `docs/phase-0/threat-model.md` | Renderer, Runtime, build, trust, diagnostics, and migration boundaries |
| Ownership map | `docs/phase-0/phase-1-handoff.md` | Proposed P1 paths, inputs, and package ownership |

### Proposed v1 facts to consume, not redefine

- Project documents use `format: "launchforge.project"` and `schemaVersion: 1`; `projectId` and all entity IDs are UUIDv4 strings unique across the document.
- Top-level sections are `name`, `window`, `theme`, `assets`, `games`, and `components`, in addition to the format/version/ID fields.
- Component types are `container`, `text`, `image`, `button`, and `gameCard`. Only containers have children; v1 has one root container, with bounded children and depth.
- Asset references use stable IDs. Paths are project-relative and restricted to one file name under `assets/`; schema validation is not a substitute for canonicalized host-side containment and reparse-point checks.
- Button actions are typed `navigate(target)` and `launchGame(gameId)`. The renderer never chooses an executable path or creates a process. The host resolves the game ID to a configured trusted launch target.
- Preview and export are required to consume the same host-neutral renderer implementation. No arbitrary HTML/CSS/JS, remote data, generic network bridge, shell command, or unrestricted filesystem/process API is in the MVP.
- The proposed build request selects target `windows-tauri-webview2` and `distribution: "portable"`; the result records schema/runtime/renderer versions, asset-manifest hash, artifact path, and diagnostics.

These details are transcribed from the Phase 0 candidate contract. If the integration owner changes or rejects that proposal, Phase 1 must follow the accepted contract instead.

### Phase 0.3 evidence status

The first Windows Actions run for PR #16 is **failed**, not passed:

- Workflow run: [#41918881904](https://github.com/PanDuroDev/LaunchForge/actions/runs/41918881904).
- Job: `windows-build`.
- Contract/renderer tests: **9 passed, 1 failed**.
- The failing assertion is the SHA-256 comparison for the source sample project versus its exported copy in `poc/tests/phase0.test.mjs`.
- Export, Tauri Windows build, main-window smoke test, and artifact upload were skipped after the failing test step.
- The clean Windows VM, WebView2 parity, DPI/accessibility, and performance measurements remain outstanding.

A report was posted to PR #16 with the exact failing run and job. Until the Windows workflow is repaired and the required clean-machine evidence is accepted (or explicitly waived by the integration owner), the candidate stack/contracts remain provisional.


## Phase 1 package readiness

### P1-A — Project foundation

**Outcome:** Create, open, save, validate, and round-trip a Launcher Project with stable IDs, asset references, and compatibility metadata.

**Required inputs:**
- Approved schema v1 and machine-readable validation rules.
- Stable ID generation and persistence requirements.
- Asset-reference resolution and path policy.
- Version compatibility and migration behavior.
- Valid and invalid fixtures with expected diagnostics.

**Implementation boundary:** Implement the approved project model and persistence behavior. Do not add fields, change ID formats, or redefine asset semantics locally.

**Exit evidence:**
- Create/open/save round-trip tests pass against the approved fixtures.
- Invalid schema/version/property values fail with actionable diagnostics.
- Missing or escaping asset references are rejected according to the approved path policy.
- Stable IDs remain stable across save/reopen and supported edits.

**Candidate contract mapping:** PR #16 proposes schema v1 at `poc/contracts/project-v1.schema.json`, with semantic checks in `poc/shared/contract.mjs`. P1-A should load and save the exact v1 shape, preserve UUIDv4 IDs, reject unknown schema versions/fields and malformed or oversized documents, validate references between component/game/asset IDs, and retain asset identity across round trips. Do not copy the schema or semantic rules into a second definition.

**Status:** Candidate inputs exist on the Phase 0 branch; implementation acceptance remains blocked on integration-owner approval and Phase 0.3 evidence.

### P1-B — Minimal editor

**Outcome:** Provide the minimum component tree, selection, inspector, add/remove/reorder, basic layout editing, and undo/redo workflow.

**Required inputs:**
- P1-A project model and frozen schema fixture.
- Approved component/property definitions.
- Selected Studio UI stack and host bridge boundary.
- Undo/redo semantics for supported editing operations.

**Implementation boundary:** Keep editor state and commands separate from the serialized project representation. Do not create editor-only fields in the shared schema without an approved contract change.

**Exit evidence:**
- A user can create and edit the starter project without editing JSON/source.
- Tree selection and inspector values stay synchronized.
- Add/remove/reorder/property edits serialize and reopen correctly.
- Undo/redo restores both editor state and project data for supported operations.

**Candidate contract mapping:** The editor consumes the v1 component types `container`, `text`, `image`, `button`, and `gameCard`. The current contract has one root container and no general-purpose absolute positioning. UI actions remain typed navigation or `launchGame(gameId)`; executable paths and command strings are not editor properties.

**Status:** Candidate stack and component definitions exist on the Phase 0 branch; implementation acceptance remains blocked on the approved schema and integration owner.

### P1-C — Shared renderer and preview

**Outcome:** Render container, text, image, button, and game-entry components in the editor preview using the same implementation intended for export.

**Required inputs:**
- Frozen component contract and property defaults.
- Renderer adapter contract and one selected production renderer.
- Asset loading/reference behavior.
- Capability profile and supported preview sizes.
- Phase 0 preview/export PoC source or conformance fixtures.

**Implementation boundary:** There must not be a separate mock renderer whose behavior differs from the exported Runtime. Renderer-specific behavior must remain behind the approved adapter.

**Exit evidence:**
- Every MVP component renders from the project model.
- Property changes update preview output.
- Missing/unsupported component and asset cases are diagnosable.
- Preview and exported output pass the same defined component fixtures and parity checks.

**Candidate contract mapping:** PR #16 proposes `RendererAdapter` with `id`, `contractVersion: 1`, `validate(project)`, and `render(project, mount, context)`. The renderer package must remain host-neutral; host privileges are represented only by typed actions/diagnostics in its context.

**Status:** A DOM proof-of-concept exists on the Phase 0 branch, but the Windows preview/export and native-host proof has not passed.

### P1-D — Standalone Runtime and local game launch

**Outcome:** Run the project outside Studio and launch only its explicitly configured local game executable through a narrow Runtime API.

**Required inputs:**
- Runtime host/API and permission contract.
- Process-launch policy and canonical path rules.
- Imported-project trust/approval behavior.
- Window settings contract.
- Runtime logging and structured error contract.

**Implementation boundary:** Do not expose shell commands, arbitrary process creation, unrestricted filesystem access, or arbitrary scripts to project-authored UI. Launch must use direct process creation with a validated executable path and structured arguments, not shell interpretation.

**Exit evidence:**
- Runtime starts independently of Studio.
- The Runtime applies the approved window title, icon, default/minimum size, and resize behavior.
- Valid project configuration starts the configured test executable.
- Invalid paths, unavailable executables, denied permissions, and invalid arguments fail safely with actionable diagnostics.
- The Runtime does not execute a different target through shell or URL-handler behavior.

**Candidate contract mapping:** The renderer emits only `launchGame(gameId)`; the Rust host resolves that ID to a preconfigured trusted executable and arguments. The UI must not supply executable paths or arbitrary command lines. Window settings are limited to the validated title, default/minimum dimensions, and resizable flag.

**Status:** The host boundary is documented in the Phase 0 candidate, but the actual Runtime resolver, first-run target configuration, canonical path/reparse-point enforcement, and Windows tests do not exist yet.

### P1-E — Deterministic build/export

**Outcome:** Produce one portable Windows launcher package with its compatible Runtime, project data, required assets, and application metadata.

**Required inputs:**
- Approved build interface and one selected output format.
- Runtime/renderer version compatibility rules.
- Asset inclusion and path-resolution rules.
- Window/app metadata contract.
- Secret scanning rules and failure behavior.
- Reproducible build inputs and supported Windows baseline.

**Implementation boundary:** Do not choose an installer/portable format, invent build flags, or hard-code dependency versions before the Phase 0 build contract is approved.

**Exit evidence:**
- Repeated builds from identical inputs produce equivalent package contents and recorded build metadata.
- Required Runtime and assets are bundled.
- Missing assets, unsupported capabilities, and build failures block export with useful diagnostics.
- The export scan checks resolved build inputs and the final package for known secret-bearing fields and configured secret patterns.
- The export scan fails closed when it detects a secret. Its diagnostics identify the offending configuration without printing the secret value.
- The output launches without Studio or undeclared development dependencies.

**Candidate contract mapping:** PR #16 proposes `BuildRequestV1` with `projectPath`, target `windows-tauri-webview2`, `outputDirectory`, and `distribution: "portable"`. The corresponding result includes build ID, artifact path, project schema version, Runtime version, renderer ID/contract version, asset-manifest SHA-256, and diagnostics.

**Status:** The portable format is a proposed choice, but the actual native package has not built or passed clean-machine deployment. Secret scanning and deterministic packaging are not implemented by the Phase 0 browser-only spike.

### P1-F — Integration and end-to-end release gate

**Outcome:** Prove the complete first-user workflow from project creation to standalone launcher and local game launch.

**Required inputs:**
- Accepted P1-A through P1-E handoffs.
- Named integration owner and supported Windows baseline.
- Starter project and launch-test executable provisioning procedure.
- Preview/export parity fixtures.
- Clean-machine setup and diagnostics/secret-scan test cases.

**Integration boundary:** The local test executable must be provisioned through a documented test fixture or harness. Tests must not depend on a developer-specific absolute path. The Runtime resolves the configured target using the approved project/path contract.

**Exit evidence:**
- A clean checkout can run the documented test/build procedure.
- A first-time user completes the workflow without editing project JSON or source.
- Preview/export parity passes.
- The exported package runs outside Studio on a clean supported Windows environment.
- The configured local executable launches through the documented Runtime API.
- Invalid projects, missing assets, unsupported features, build errors, and prohibited secrets produce actionable blocking diagnostics.
- Logs and diagnostic bundles redact tokens, credentials, personal data, and sensitive filesystem paths.

**Current evidence:** The first PR #16 Windows workflow failed in the sample-project source/export hash assertion (9/10 tests passed); all native build/smoke/package steps were skipped. No clean Windows VM result or accepted integration owner/waiver is recorded.

**Status:** Blocked on the integration owner, accepted contracts, repaired Windows CI, all prior package handoffs, and clean-machine test infrastructure.

## Suggested ownership boundaries

These are proposed module boundaries for the Phase 1 ownership map, not a decision about repository layout. The integration owner should map them to concrete paths after reviewing the Phase 0 stack and repository structure.

| Responsibility | Proposed owner | Shared surfaces that must not be changed independently |
|---|---|---|
| Project persistence and validation | P1-A | Schema v1, ID rules, migrations, asset references |
| Editor interaction and history | P1-B | Component property contract, serialized project model |
| Renderer and preview | P1-C | Renderer adapter, component registry, capability profile |
| Runtime and process launch | P1-D | Runtime API, permission model, process-launch policy |
| Build and packaging | P1-E | Build CLI contract, target format, runtime compatibility |
| End-to-end integration | P1-F / named integration owner | Test fixtures, parity contract, clean-machine gate |

No two agents should independently modify the same schema, renderer registry, Runtime API, or build pipeline. A shared-contract change requires a written proposal, compatibility impact, migration note, and approval from the integration owner.

## Work that is safe to do before the contracts arrive

- Maintain the Phase 1 acceptance checklist and requirement traceability.
- Prepare test scenarios from Issue #3 without binding them to a guessed schema/API.
- Identify clean-machine test requirements and how the local test executable will be provisioned.
- Review the Phase 0 PoC and map its proven interfaces to the Phase 1 packages once those artifacts exist.

The following are **not** safe to implement against assumptions: project serialization, shared component types, renderer adapter interfaces, Runtime process APIs, build flags/package layout, or secret scanning rules.

## Execution sequence and handoff

1. **1.1 — Project foundation:** P1-A implementation and fixture-based round-trip/validation review.
2. **1.2 — Minimal editor and shared renderer:** P1-B and P1-C consume the accepted schema/component/renderer contracts. Review editor behavior and preview parity before handoff.
3. **1.3 — Runtime, export, and end-to-end MVP:** P1-D and P1-E integrate through the approved Runtime/build interfaces; P1-F owns the complete workflow and clean-machine gate.

Each handoff must report changed paths, contract changes (or explicitly state none), exact test commands/results, known limitations, and remaining risks. A stage is not complete because it compiles in isolation.

## Current conclusion

This PR is a readiness/documentation contribution only. It does not complete Issue #3, and it intentionally does not introduce a provisional implementation stack or shared contract. Implementation can begin package-by-package as soon as the corresponding Phase 0 artifacts are published and reviewed. The remaining Phase 1 work is tracked above rather than being represented as completed.
