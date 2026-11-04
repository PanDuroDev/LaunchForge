# Phase 1 Acceptance Test Plan

> **Status:** Test design — not executable until the Phase 0 contracts and Phase 1 implementation exist.
> **Parent:** Issue #3 — Phase 1: Prove the Product.
> **Owner:** Phase 1 integration owner (must be named before P1-F execution).
> **Applies to:** P1-A through P1-F.

## 1. Purpose and constraints

This plan converts the Phase 1 acceptance criteria into observable test scenarios. It is intentionally independent of the selected programming language, UI framework, project serialization details, renderer API, and packaging tool.

It does not define:
- Project JSON field names or schema shape.
- Stable ID encoding.
- Component property names or renderer methods.
- Runtime API function signatures.
- Build command flags or package layout.
- Secret patterns that have not been approved by the security owner.

Those values must come from approved Phase 0 contracts. Tests should bind to the approved interfaces rather than duplicate or invent them.

A test is not considered passed merely because a module compiles. The release gate is the complete first-user journey on a clean supported Windows environment.

## 2. Test environments

### 2.1 Required environments

| Environment | Purpose | Required evidence |
|---|---|---|
| Developer environment | Fast unit, component, and integration feedback | Exact commands, toolchain versions, pass/fail summary |
| CI environment | Repeatable automated checks on every relevant change | Workflow run and test artifact/report |
| Clean Windows environment | Verify exported launcher has no undeclared Studio/developer dependency | Windows version/build, architecture, installed prerequisites, package hash, execution log |
| Security test environment | Exercise path, process-launch, import, and secret-scan rejection cases | Test fixture IDs, expected rejection, observed diagnostic |

The supported Windows version/build and architecture must be selected in Phase 0. Do not use a developer machine as the only clean-machine evidence.

### 2.2 Clean-machine rules

The clean-machine environment must:
- Be provisioned from a documented baseline image or repeatable setup procedure.
- Not contain the Studio development toolchain unless that toolchain is explicitly part of the supported end-user prerequisites.
- Not rely on a developer-local directory, environment variable, cached asset, or globally installed package.
- Start from a clean user profile and a documented working directory.
- Record all installed prerequisites and distinguish them from dependencies bundled in the export.
- Be reset between tests that modify installed files or machine state.

The integration owner must record whether the supported clean environment is a VM, physical machine, or both. A clean VM is useful evidence but does not automatically prove every physical-device behavior.

## 3. Test fixture requirements

Fixtures are test inputs, not product contracts. Their serialized shape must use the approved schema when it becomes available.

| Fixture ID | Required content | Used by |
|---|---|---|
| F-STARTER | Smallest valid starter Launcher Project with one configured local game entry | P1-A, P1-B, P1-C, P1-F |
| F-COMPONENTS | One instance of each supported MVP component: container, text, image, button, and game entry | P1-B, P1-C |
| F-ASSET-OK | Small deterministic local image asset referenced by the starter/project | P1-A, P1-C, P1-E |
| F-ASSET-MISSING | Project reference to an asset removed after authoring | P1-A, P1-C, P1-E |
| F-PROJECT-INVALID | A project invalid under the approved schema/validation rules | P1-A, P1-E |
| F-PROJECT-UNSUPPORTED | Syntactically valid project containing a capability unsupported by the selected target | P1-C, P1-E |
| F-GAME-OK | Minimal, harmless test executable built for the supported Windows architecture; writes a test marker and exits | P1-D, P1-F |
| F-GAME-MISSING | Approved test fixture path whose executable is absent | P1-D, P1-F |
| F-GAME-UNAUTHORIZED | Executable path outside the approved launch target or imported-project approval boundary | P1-D |
| F-SECRET | Synthetic, non-production secret sentinel matching an approved test scanner rule | P1-E |
| F-LOG-REDACTION | Synthetic credential/token values passed through error and logging paths | P1-D, P1-E, P1-F |

### 3.1 Test executable provisioning

The local game test executable must be built or installed by the test harness from tracked fixture source, or supplied as a versioned test artifact with a recorded hash. It must not be assumed to exist at a developer-specific path.

The test executable should do only the following:
- Write a known test marker to a harness-owned temporary location.
- Record the received argument vector without reinterpreting it as a command.
- Record the working directory.
- Exit with a configurable test exit code.

It must not invoke a shell, access unrelated files, modify system state, or download content. The fixture path is resolved by the test harness and passed through the approved Runtime configuration process.

The test harness must distinguish:
1. The configured executable path.
2. The executable path resolved by the Runtime.
3. The executable actually observed by the test fixture.

A mismatch is a failure even if some process happened to start.

## 4. Project foundation — P1-A

| ID | Scenario | Expected result |
|---|---|---|
| A-01 | Create a project from the approved starter | A valid project is created and can be opened immediately |
| A-02 | Save, close, and reopen F-STARTER | The reopened project is semantically equivalent to the saved project |
| A-03 | Repeat save without edits | No unintended semantic changes or unstable ID churn occur |
| A-04 | Add a supported node and save/reopen | The node and its stable identity persist |
| A-05 | Reorder or edit a node and save/reopen | Identity is preserved; only intended data changes |
| A-06 | Open F-PROJECT-INVALID | Loading fails safely with a useful validation diagnostic |
| A-07 | Open a project with unsupported schema version | The project is not silently reinterpreted or overwritten |
| A-08 | Open F-ASSET-MISSING | The missing reference is reported with enough context to locate the problem |
| A-09 | Resolve an asset path that attempts to escape the project root | Resolution is rejected according to the approved path policy |
| A-10 | Open a valid project with optional fields omitted | Approved defaults are applied without silently rewriting authored data |

Round-trip equivalence must be defined at the semantic project-model level. Byte-for-byte formatting equality is not required unless the approved schema/serializer contract explicitly promises canonical serialization.

## 5. Editor workflow — P1-B

| ID | Scenario | Expected result |
|---|---|---|
| B-01 | Open F-STARTER in Studio | The hierarchy, viewport, and inspector load without editing source files |
| B-02 | Select a node in the hierarchy | The same stable node is selected in the viewport and inspector |
| B-03 | Select a node in the viewport | The hierarchy selection updates to the same stable node |
| B-04 | Edit a supported property in the inspector | The project model and preview reflect the committed edit |
| B-05 | Add each supported MVP component | The component appears in the tree, project model, and preview |
| B-06 | Remove a selected component | The intended component is removed; unrelated nodes remain unchanged |
| B-07 | Reorder siblings | Visual order and serialized child order agree |
| B-08 | Undo an edit | The prior project state and preview are restored |
| B-09 | Redo an edit | The edited state and preview are restored |
| B-10 | Attempt an invalid property value | The editor rejects it or presents the approved deterministic fallback and diagnostic; it does not corrupt the project |
| B-11 | Save, close, and reopen after a sequence of edits | The final authored state is preserved |

Undo/redo tests must assert project data and visible preview state, not only the history control's enabled/disabled state.

## 6. Shared renderer and preview — P1-C

| ID | Scenario | Expected result |
|---|---|---|
| C-01 | Render F-COMPONENTS in Studio preview | All supported MVP components render from the approved project model |
| C-02 | Change text, image reference, and supported visual properties | Preview updates from the same project state without requiring manual refresh unless explicitly designed |
| C-03 | Use F-ASSET-MISSING | The image failure is visible and diagnosable; Studio does not crash |
| C-04 | Use F-PROJECT-UNSUPPORTED | Unsupported capability is reported and cannot silently degrade during export |
| C-05 | Render the same fixture in preview and exported Runtime | Equivalent component behavior and appearance are observed |
| C-06 | Exercise the basic navigation action | The action produces the same supported result in preview and exported Runtime |
| C-07 | Repeat a fixture at the same viewport and scale inputs | Layout and component output are deterministic within the approved comparison tolerance |

Preview/export parity must use the same component implementation wherever the architecture promises reuse. Where a comparison requires visual snapshots, the Phase 0 renderer owner must approve capture settings and tolerances. Do not invent a pixel-difference threshold before the PoC establishes one.

## 7. Runtime and local game launch — P1-D

| ID | Scenario | Expected result |
|---|---|---|
| D-01 | Start the exported Runtime with F-STARTER | Runtime loads the project without Studio |
| D-02 | Launch F-GAME-OK through the configured game action | Only the configured test executable starts |
| D-03 | Pass arguments containing spaces and shell metacharacters as individual arguments | The fixture receives the exact argument vector; no shell interpretation occurs |
| D-04 | Launch F-GAME-MISSING | Runtime returns an actionable missing-executable diagnostic |
| D-05 | Configure an executable outside the approved project/user-selected trust boundary | Launch is denied or requires the explicit approval flow defined by policy |
| D-06 | Import a project containing a launch target | Import does not silently authorize execution; the approved trust/confirmation step is enforced |
| D-07 | Attempt a shell command, script, or URL-handler target | Runtime rejects the target; no shell/handler execution occurs |
| D-08 | Supply an invalid working directory | Launch fails safely with a diagnostic |
| D-09 | Force the test executable to exit non-zero | Runtime surfaces the process failure without crashing |
| D-10 | Inspect logs after success and failure | No credential or prohibited sensitive value is exposed |

The test must verify the resolved executable identity and actual argument vector. A test that merely checks that a process started is insufficient.

## 8. Build and export — P1-E

| ID | Scenario | Expected result |
|---|---|---|
| E-01 | Export F-STARTER using the documented build interface | One supported portable Windows package is produced |
| E-02 | Build the same inputs twice under the documented reproducible conditions | Package contents and build metadata are equivalent under the approved determinism definition |
| E-03 | Inspect the exported package | The compatible Runtime, project data, and required assets are included |
| E-04 | Remove a required asset and export | Export fails with a diagnostic identifying the unresolved asset |
| E-05 | Export F-PROJECT-INVALID | Export is blocked before producing a usable package |
| E-06 | Export F-PROJECT-UNSUPPORTED | Export is blocked or uses only an explicitly approved fallback |
| E-07 | Export with F-SECRET | The secret scanner blocks export and identifies the source without disclosing the sentinel |
| E-08 | Inspect package contents for configured prohibited secret patterns | No prohibited credential is present in any shipped file |
| E-09 | Inspect application metadata | Name, version, icon, and other supported metadata match project/build settings |
| E-10 | Launch the exported package from a different directory | Runtime and assets resolve without a developer-local path dependency |

The exact output format, dependency inventory, and deterministic-build definition must come from the Phase 0 build decision. Do not make an unsupported claim of byte-identical builds if the selected toolchain embeds timestamps or nondeterministic metadata.

## 9. End-to-end and clean-machine gate — P1-F

| ID | Scenario | Expected result |
|---|---|---|
| F-01 | Start from a clean checkout and follow the documented first-user procedure | A new user can create the sample without manually editing project JSON/source |
| F-02 | Preview the edited sample | The expected components and game entry are visible |
| F-03 | Export the sample | The documented portable package is produced with no unresolved build errors |
| F-04 | Copy the package to the clean Windows environment | Package starts without Studio or undeclared developer dependencies |
| F-05 | Invoke the configured game action | F-GAME-OK is launched and the harness records the expected executable, arguments, and working directory |
| F-06 | Run missing-asset, invalid-project, and unsupported-feature cases | Each is reported with actionable diagnostics and does not produce a silently broken launcher |
| F-07 | Run secret-scan rejection case | Export is blocked and the diagnostic does not reveal the secret sentinel |
| F-08 | Review Runtime logs and diagnostics | Logs identify failures while redacting configured secrets and sensitive values |
| F-09 | Repeat the clean-machine workflow from a reset baseline | Results are reproducible using the documented setup |

**Release gate:** F-01 through F-09 and all applicable upstream package tests must pass on the supported Windows baseline. A partial pass, successful compilation, or developer-machine-only execution is not completion of Phase 1.

## 10. Diagnostic quality checks

Every failure-path test should verify more than a non-zero exit code or generic error dialog.

A useful diagnostic should:
- Identify the failing operation or project element.
- Explain what condition failed in user-facing language.
- Identify the relevant node/asset/action/build stage where safe.
- Suggest a specific corrective action where possible.
- Avoid exposing secret values, access tokens, or unnecessary private paths.
- Be available in the supported Studio/Runtime diagnostic surface and recorded in structured logs where appropriate.

Exact diagnostic codes and field names must follow the approved Runtime/build contract.

## 11. Execution record template

The integration owner should copy this table into the Phase 1 handoff and fill it with actual results. Do not mark a test passed without a reproducible command or documented manual procedure.

| Field | Value |
|---|---|
| Test ID(s) | |
| Commit / PR | |
| Environment and Windows build | |
| Toolchain and dependency versions | |
| Fixture version/hash | |
| Exact command or manual steps | |
| Expected result | |
| Actual result | |
| Pass / Fail / Blocked | |
| Logs/artifact links | |
| Known limitation or follow-up issue | |

## 12. Current execution status

All cases in this document are **Not run**. They require application code, approved Phase 0 contracts, fixtures, and a Windows test environment that are not present in the current repository baseline.

The first executable test work should be added alongside P1-A only after schema v1 and its fixtures are accepted. P1-F test automation should consume the same fixtures and contracts rather than create another representation of project data.

This plan is a Phase 1 test-design deliverable. It does not claim that P1-A, P1-B, P1-C, P1-D, P1-E, P1-F, or the Phase 1 MVP has been implemented.
