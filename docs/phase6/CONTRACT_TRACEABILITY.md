# Phase 6.1 — Contract Traceability and Coverage Gaps

**Assessment date:** 2026-11-04  
**Status:** Proposed-contract mapping; not an approval or support claim  
**Purpose:** Connect the Phase 6 conformance inventory to the latest Phase 0–5 candidate contracts and identify what must be approved before executable product conformance begins.

## 1. Decision

Phase 0 has now produced a substantial candidate contract and a shared-renderer spike in PR #16. Phase 1 has added an architecture-neutral acceptance test plan in PR #9. Phase 2 has refined authoring semantics in PR #10 and a separate deterministic layout reference prototype in PR #13. Phase 5 has added publisher release QA in PR #14 and a TUF updater trust/recovery proposal in PR #15.

These are valuable inputs to 6.1, but the referenced pull requests remain open and unmerged. In particular, PR #16 labels its contracts as a frozen candidate for integration-owner review, not approved for Phase 1; its Windows host build and clean-machine evidence remain outstanding. The Phase 6 mapping below is therefore **provisional traceability**, not acceptance of upstream contracts.

Do not change catalog cases from `planned` to `implemented`, publish support, or enable a new expansion based only on these candidate branches.

## 2. Upstream evidence snapshot

| Input | Current evidence | What Phase 6 can consume now | Approval / unresolved boundary |
|---|---|---|---|
| [PR #16 — Phase 0](https://github.com/PanDuroDev/LaunchForge/pull/16) | Candidate stack/contract docs, Project Schema v1, threat model, shared DOM renderer POC, export hash/parity tests, Tauri shell and Windows workflow. Its PR reports 10 Node tests and export generation passing. | Candidate project fields, UUIDv4 identity, component/action allowlists, renderer/Runtime/build versioning, diagnostics, migration rules, security cases, and common-renderer parity model. | Open and unmerged; no submitted review recorded at inspection. Windows Tauri build still in progress; smoke test/package upload, clean-machine VM, real WebView2 parity, DPI/accessibility and performance measurements pending. |
| [PR #9 — Phase 1 readiness](https://github.com/PanDuroDev/LaunchForge/pull/9) | Readiness guide plus a P1-A–P1-F acceptance test plan. | P1 test IDs for project persistence, editor behavior, renderer parity, local process launch, build/export and clean-Windows flow. | Documentation/test design only; all Phase 1 tests in its plan are explicitly not run. No Studio, Runtime or production test harness. |
| [PR #10 — Phase 2 specification](https://github.com/PanDuroDev/LaunchForge/pull/10) | Layout, editing, assets/themes/templates, accessibility/localization and migration-preservation semantics; review fixes described in the PR. | Layout/RTL/scale cases, asset reference preservation, import/export recovery and unsupported-field preservation. | Specification only; requires accepted Phase 0/1 contracts and production Studio/renderer. |
| [PR #13 — Phase 2.1 layout reference](https://github.com/PanDuroDev/LaunchForge/pull/13) | Isolated Python geometry prototype. PR reports 22 tests in the branch, 4 focused regression checks and 10,000 seeded allocation property cases; the complete final 22-case suite was not re-run after the last edits. | Candidate expected semantics for stack/fill/constraints/RTL and future deterministic geometry fixtures. | Reference prototype only; not production layout engine, Studio or exported Runtime integration; no Windows DPI or preview/export parity evidence. |
| [PR #12 — Phase 4.1 manifest/downloader](https://github.com/PanDuroDev/LaunchForge/pull/12) | Proposed manifest contract and isolated Python downloader prototype; PR reports 28 passing tests using mocked transport. | Future game-delivery integrity/security test scenarios. | Draft, unmerged, not Runtime-integrated; no install-root transaction, reparse-point-safe install, rollback/recovery or live publisher endpoint. |
| [PR #14 — Phase 5.1 publisher release QA](https://github.com/PanDuroDev/LaunchForge/pull/14) | Publisher artifact inventory schema, standard-library validator, release workflow guide and 28 tests. | Artifact inventory structure, exact size/hash checks, path safety, release provenance and signing-status recording. | Open, unmerged. Inventory explicitly is not updater metadata or a trust statement; signature verification, real package pipeline, clean-machine install and Windows reparse-point coverage remain separate. |
| [PR #15 — Phase 5.2 updater trust proposal](https://github.com/PanDuroDev/LaunchForge/pull/15) | TUF-based trust/recovery design and a 54-scenario conformance matrix. | Candidate metadata/key rotation, rollback/replay, identity binding and transaction-recovery test cases. | Proposal only; no updater implementation, approved Runtime/package interface, Windows transaction/recovery evidence or recorded approval. |
| Phase 5.3 whole-product gate | No accepted Phase 5.3 security/diagnostics/release handoff was present in the reviewed PR set. | Nothing yet beyond the Phase 6 requirements already listed. | Required Phase 5 release/security/support gate remains unproven. |

All of the above are reviewable working branches, not merged `main` contracts. Open PRs and successful isolated prototypes do not independently satisfy Phase 6's stable-Phase-5 dependency.

## 3. Traceability from Phase 6 catalog to upstream contracts

The catalog contains 36 planned cases. The mapping below records current candidate sources; it does not redefine their acceptance criteria.

| Phase 6 case IDs | Candidate source / contract area | Current test evidence | Additional Phase 6 integration work after approval |
|---|---|---|---|
| `LF-COMPAT-001..006` | PR #16 Project Schema v1, semantic validator and compatibility/build capability rules; PR #9 P1-A tests A-01..A-10 | PR #16 reports schema validation and contract/renderer tests in its POC; P1 acceptance plan is design-only. | Add fixture-driven compatibility adapter for every supported schema/Runtime tuple; cover UUIDv4 uniqueness/stability, exact root/component limits, asset/game ID references, unknown fields/versions, and round-trip preservation. |
| `LF-MIG-001..006` | PR #16 versioning and migration policy (ordered N→N+1, stable IDs, recoverable original); PR #10 legacy semantic-preservation rules | No migration engine or migration fixture chain is present in accepted `main`. | Once the migration API and source-version range are approved, create one fixture per supported source version and prove deterministic migration, backup/restore and failure safety. |
| `LF-CAP-001..005` | PR #16 renderer contract, target capability declarations and build rejection; PR #9 P1-C/P1-E | POC describes unsupported-feature rejection; no production renderer registry or Runtime/build target adapter is present. | Bind the catalog to the accepted capability identifiers and target declarations; prove missing/unknown required capabilities block export before packaging. |
| `LF-PARITY-001..005` | PR #16 same renderer package in preview/export and SHA-256 parity fixture; PR #9 C-01..C-07; PR #10 layout/RTL/DPI specification; PR #13 geometry prototype | PR #16 reports hash/render-output checks for the browser-based POC; native WebView2 screenshot/interaction parity and DPI/accessibility are pending. | Add production-renderer tests comparing the approved shared package across Studio and exported Runtime, including layout, interaction, failure states, keyboard/focus, Unicode/RTL and supported DPI. |
| `LF-SEC-001..005` | PR #16 threat model (import, path containment, reparse points, process launch, credential scans, log redaction); PR #9 P1-D/P1-E/P1-F; PR #14 validator path/hash checks | POC has bounded project/schema and typed-action tests; production Rust path containment and Windows reparse-point tests remain pending. | Map security fixtures to the approved threat model and host commands; verify canonical containment, no shell/generic process bridge, final-package secret scan and sanitized logs on supported Windows. |
| `LF-PKG-001..005` | PR #14 publisher artifact inventory/release workflow; PR #15 TUF updater/recovery proposal; PR #16 BuildResultV1 portable output candidate | PR #14's validator tests and PR #15's 54 proposed scenarios are isolated from a production package/updater. | Once package and trust interfaces are approved, run clean-machine install/upgrade/uninstall, artifact verification, fault-injected update and last-known-good recovery tests. |
| `LF-PERF-001..003` | PR #16 Phase 0 measurement protocol | The protocol explicitly says startup, memory, CPU, package/build time, clean-machine deployment, native parity and accessibility/DPI metrics are not yet measured. | Record comparable baselines and thresholds only after the Windows environment, sample project and toolchain are fixed; attach raw measurements to each target tuple. |
| `LF-OPS-001` | PR #16 CI/measurement process, PR #9 P1 clean-checkout test record, PR #14/15 evidence-retention guidance | Isolated POC workflows exist on unmerged branches; Phase 6 catalog workflow passes on this PR. | Establish one accepted cross-product fixture/version policy and reproducible run records consumed by Studio, build, Runtime and release gates. |

## 4. Specific gaps to add after upstream contracts are accepted

The following are **coverage gaps to reconcile**, not new contract definitions:

1. **Project identity and references:** test duplicate UUIDv4s across project/assets/games/components, stable IDs through rename/reorder, invalid game/asset references, and preservation of asset identity across export.
2. **Schema bounds:** test top-level project shape, the single root component, component-tree depth/count, text/description limits, window bounds, asset/game count limits and exact enum/property allowlists as defined by the accepted Schema v1.
3. **Typed actions and Runtime authorization:** verify navigation target allowlists, `launchGame(gameId)` resolution on the host, denial of arbitrary executable paths/shell/argument injection, and that imported projects do not silently authorize launch targets.
4. **Renderer versioning and capability profile:** test contractVersion mismatch, target/runtime version range mismatch, capability removal, and required-vs-optional capability semantics.
5. **Import/migration recovery:** test malformed archives, missing assets, existing destination projects, backup preservation, reparse-point races and failure before source/destination replacement.
6. **Release inventory vs updater trust:** ensure publisher inventory hashes are never mistaken for authenticated updater metadata. TUF trust-root, role thresholds, freshness, anti-rollback and transaction recovery must be tested by the updater owner, not inferred from an inventory validator passing.
7. **Clean-machine and performance:** test actual WebView2 host, standard-user permissions, packaged prerequisites, 100/150/200% DPI, accessibility, process-tree resource use, first usable frame and package bytes on the accepted Windows baseline.

These gaps should become concrete case records only when the corresponding contract fields, fixture shape, owner and expected failure behavior are approved. Avoid hardcoding provisional v1 field names or API signatures in the Phase 6 catalog before then.

## 5. Current status and entry decision

| Gate | Current status | Evidence still required |
|---|---|---|
| Phase 0 candidate contracts | **Proposed / review pending** | Integration-owner approval of PR #16; completed Windows Tauri build and smoke test; clean supported Windows VM and actual WebView2 parity/accessibility/DPI evidence; reviewed residual risks and ownership. |
| Phase 1 implementation contracts | **Candidate only** | Accepted project/component/renderer/Runtime/build contracts; project persistence and migration implementation; supported Windows baseline; named integration owner. |
| Phase 2 compatibility surface | **Specification/prototype only** | Accepted 2.1 semantics and production layout/asset/RTL/DPI behavior in Studio and exported Runtime. |
| Phase 3 data/action contract | **No accepted deliverable found** | Approved network/binding/action/credential/export policy and shared preview/Runtime fixtures if these features are in supported projects. |
| Phase 4 distribution/runtime contract | **Proposed prototype only** | Approved manifest/filesystem/lifecycle boundaries and adversarial install transaction/recovery tests. |
| Phase 5 production release | **Partial 5.1 / 5.2 proposals** | Accepted packaging contract, trusted updater implementation, whole-product security/diagnostics review, clean-machine install/update/rollback evidence, and named support owner. |
| Phase 6 maintenance owner | **Not recorded** | Named maintainer accepts support matrix, migration, compatibility triage and deprecation responsibility. |
| Expansion demand | **Not evidenced** | Dated user workflows/requests and one track decision with support-cost justification. |

**Decision:** Keep executable product conformance, 6.2 selection and 6.3 support blocked. Continue 6.1 preparation by maintaining this traceability map and reconciling the catalog after PR #16 and the dependent Phase 1–5 contracts are formally accepted. Do not mark Phase 6 complete or publish a new platform/renderer/extension support claim from this evidence alone.
