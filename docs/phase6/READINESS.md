# Phase 6 Readiness and Expansion Gate

**Assessment date:** 2026-11-04  
**Status:** BLOCKED — prerequisite contracts and release evidence are not present on `main`  
**Scope:** Phase 6 only (6.1 compatibility/conformance, 6.2 one expansion, 6.3 support validation)

## Decision

Do not begin a production expansion or claim compatibility support yet.

No expansion track is selected in this assessment. The repository contains no recorded user-demand evidence, validated project/runtime contracts, or named maintainer commitment for any candidate track. Selecting extensions, another renderer, another operating system, or an integration now would be speculative and would conflict with the Phase 6 acceptance criteria.

This is a deliberate gate decision, not a rejection of future expansion. Re-open the decision after the prerequisites and evidence below are reviewed. Candidate selection must choose exactly one track.

## Repository evidence

The assessment is based on the GitHub repository state inspected on 2026-11-04:

- `main` points to `3d24d286118892b948424c547f91db3d1ce7ed84`.
- The root contains only `README.md` and `docs/`; `docs/` contains only `PROJECT_PLAN.md`.
- The README contains only the repository heading.
- The only merged pull request is PR #1, which adds the product plan and explicitly describes itself as documentation-only.
- At the time of the initial assessment, no open pull requests were present; a subsequent audit found the unmerged work listed below.
- Phase issues #2–#7 remain open, although partial preparation has now merged: the Phase 2.1 geometry reference (PR #13), Phase 5.1 publisher artifact inventory validator (PR #14), and Phase 6.1 catalog/readiness baseline (PR #11). None of those partial slices completes its parent phase gate.
- At the initial baseline inspection, visible Phase 1/2/4/5 work branches pointed to the same commit as `main`. A later audit found branch advances, which are recorded separately below; those unmerged branches still do not establish accepted contracts or landed implementation.
- No production Studio, exported Runtime, migration engine, production renderer registry, integrated updater, or clean-machine Windows release gate is present in the inspected tree. Phase 5.1 now has merged publisher-side inventory validation, but that is not an installed launcher package or updater.

A branch name or an open phase issue is not evidence that its deliverables are implemented or accepted. This document does not infer completion from those signals.


## Follow-up evidence review

The audit on 2026-11-04 now includes merged prototype work and newer Windows validation results. Working-branch contracts remain proposals until reviewed and accepted by the integration owner.

| Work item | Current evidence | Phase 6 impact and remaining gate |
|---|---|---|
| [PR #16 — Phase 0](https://github.com/PanDuroDev/LaunchForge/pull/16) | Candidate Tauri v2/Rust + TypeScript/React stack, Project Schema v1, renderer/Runtime/build/security contracts, shared renderer/export POC, and application-icon asset reference. | PR remains open/unmerged with no submitted review. An earlier Windows run [#41919850333](https://github.com/PanDuroDev/LaunchForge/actions/runs/41919850333) passed contract/renderer tests, standalone export, Rust lockfile generation/build, host smoke-test, portable package creation and artifact upload. The **latest head** run [#41920824672](https://github.com/PanDuroDev/LaunchForge/actions/runs/41920824672) fails 12/13 contract tests at the negative ICO test: it removes the final byte of the whole file and expects an exception, but that byte may be outside all declared image payloads. The current failure blocks the workflow; it does not yet prove the validator accepts a truncated declared image payload. Fix the fixture to truncate within the final declared image range (or extend its declared byte count beyond the buffer) and rerun. The current PR tree still has no tracked `poc/src-tauri/Cargo.lock`; review/commit the generated lockfile. Fresh-user Windows VM, WebView2 parity, DPI/accessibility and performance evidence remain outstanding. |
| [PR #9 — Phase 1 readiness](https://github.com/PanDuroDev/LaunchForge/pull/9) | Readiness guide and P1-A–P1-F acceptance test plan. | Documentation/test design only; no Studio/Runtime MVP implementation. |
| [PR #22 — Phase 1.1 project foundation](https://github.com/PanDuroDev/LaunchForge/pull/22) | Draft Rust project persistence/validation implementation, 24 authored test cases, consumes lowercase UUID and application-icon candidate rules. | Still Draft and stacked on open PR #16; the 24 Rust tests have not been run. Not on main or an approved Phase 1 contract. |
| [PR #10 — Phase 2 authoring specification](https://github.com/PanDuroDev/LaunchForge/pull/10) | Refined layout, editing, assets, import/export, accessibility, localization and compatibility requirements. | Specification only; production Studio/renderer integration and accepted Phase 1 contracts remain prerequisites. |
| [PR #13 — Phase 2.1 layout reference](https://github.com/PanDuroDev/LaunchForge/pull/13) | **Merged into main** at [commit c696227](https://github.com/PanDuroDev/LaunchForge/commit/c69622778a2a11329940de4a7e7d51d527d743f6). Its four Python CI jobs (3.10, 3.11, 3.12, 3.13) all passed in [run #41920391630](https://github.com/PanDuroDev/LaunchForge/actions/runs/41920391630). | Useful executable geometry reference and regression suite now live in main. It remains a Python prototype, not the production Studio layout engine or shared renderer; no Windows DPI or preview/export parity evidence is included. |
| [PR #12 — Phase 4.1 manifest/downloader](https://github.com/PanDuroDev/LaunchForge/pull/12) | Draft Python prototype and proposed game-distribution manifest; PR reports 28 tests using mocked transport. | Useful future game-delivery cases only. Not approved or Runtime-integrated; no secure install-root transactions, Windows reparse-point installation, rollback or recovery. |
| [PR #17 — Phase 4.2/4.3 transactions/lifecycle](https://github.com/PanDuroDev/LaunchForge/pull/17) | POSIX transactional install/update/repair/verify/recovery prototype and lifecycle adapter; PR reports 40 local tests. | Open and ready for review, but POSIX-only; deliberately refuses Windows and has no Win32/NTFS reparse-point backend or Phase 1 Runtime/process integration. |
| [PR #18 — Phase 5.3 security/diagnostics](https://github.com/PanDuroDev/LaunchForge/pull/18) | Diagnostic-event schema, allowlist sanitizer, release checklist, security review and support/migration policy; PR reports 20 tests in a local mirror. | Open/unmerged. Its documented production gate is **FAIL / NO-GO** until an accepted Runtime/package, supported Windows baseline, updater, clean-machine install/recovery evidence and Runtime diagnostics integration exist. |
| [PR #14 — Phase 5.1 release QA](https://github.com/PanDuroDev/LaunchForge/pull/14) | Merged into main at [commit 6405f27](https://github.com/PanDuroDev/LaunchForge/commit/6405f27cd842c49570803c8323f1d6db0ae524dc); adds publisher artifact-inventory schema, standard-library validator, release workflow and 28 tests. | Useful publisher QA foundation, but explicitly not updater trust metadata and does not prove launcher package install/update/recovery or clean-machine release readiness. |
| [PR #15 — Phase 5.2 updater proposal](https://github.com/PanDuroDev/LaunchForge/pull/15) | TUF trust/recovery architecture proposal and 54-scenario conformance matrix. | Documentation-only; no updater implementation or approved package/Runtime interface. Open/unmerged. |
| [PR #11 — Phase 6.1 baseline](https://github.com/PanDuroDev/LaunchForge/pull/11) | Merged into main; initial baseline added the catalog, metadata validator, 13 tests, CI workflow, readiness and conformance plan. This follow-up adds two planned contract-edge cases (38 total) and two catalog tests (15 total). | Catalog/harness validation is reproducible. It does not execute product-level compatibility behavior; all catalog cases remain planned. |

The first Phase 0 Windows failure [#41919048099](https://github.com/PanDuroDev/LaunchForge/actions/runs/41919048099) was caused by the missing `poc/src-tauri/icons/icon.ico`; the resource was subsequently added. The ICO truncation fixture was corrected, and run #41922565161 completed the Tauri build and smoke-test, then failed only when pushing the generated Cargo.lock after another branch update caused a non-fast-forward rejection. The current rerun #41923627391 has passed all contract/renderer/export/icon steps and is in the locked Tauri build step. The next gate is to persist the verified lockfile on the branch and finish smoke/package/upload.

The Phase 0 owner has now explicitly resolved the UUID policy in the candidate: project, asset, game and component IDs are canonical lowercase UUIDv4 strings, and both the JSON Schema and JS semantic validator reject uppercase spellings. The validator also enforces a single container root, case-insensitive asset-path uniqueness, `minWidth <= width` / `minHeight <= height`, portable filenames and a typed application-icon reference. Phase 1.1 has been refreshed as Draft PR #22; it now also enforces canonical lowercase UUIDv4 and consumes the application-icon reference. Its 24 Rust tests have not yet been executed, and it remains stacked on the unapproved Phase 0 candidate. The candidate contracts remain unapproved.

PR #17 remains a POSIX-only reference and not a Windows game lifecycle implementation. PR #14's inventory is a publisher QA record, not a client updater manifest. PR #15 is an updater design proposal. PR #18's Phase 5.3 review still records **FAIL / NO-GO**.

**Updated gate decision:** continue 6.1 preparation and contract traceability. Do not activate product-level conformance, select 6.2, or publish 6.3 support until the latest Phase 0 workflow is green, Phase 0/1 contracts are reviewed and accepted, Windows/clean-machine evidence is complete, Phase 4 has a Windows-native backend, Phase 5 closes its NO-GO findings, and a maintainer is named.

PR #21 is an open Phase 3.1 prototype: its latest content-data workflow [#41923553906](https://github.com/PanDuroDev/LaunchForge/actions/runs/41923553906) passed `npm run typecheck` and fixture-only `npm test`, but CodeRabbit review is still in progress and this does not prove DNS/IP egress security, Studio/Runtime integration, serialized binding semantics, or preview/export parity. The new `LF-CAP-006` and `LF-SEC-006` cases remain planned until those contracts are accepted.

## Dependency assessment

| Phase 6 prerequisite | Evidence required to pass | Current assessment |
|---|---|---|
| Phase 0 architecture and security contracts | Reviewed stack/renderer decision, aligned project schema and semantic validator, Runtime/build interfaces, threat model, fixtures, successful current Windows workflow and clean-machine gates | **Latest run #41923627391 has passed contract/renderer, measurement-script, export and icon checks; locked Tauri build is in progress. Prior run #41922565161 passed build/smoke but failed to push Cargo.lock after a non-fast-forward update. The Phase 0 candidate is lowercase-only UUID; current P1.1 PR #22 aligns but its Rust tests are unrun. No tracked Cargo.lock yet; clean-machine evidence and approval remain pending.** |
| Phase 1 project and Runtime contracts | Accepted schema/component/renderer/Runtime/build contracts and implementation; versioned project format; preview/export parity tests | **Draft PR #22 adds Rust project persistence/validation against the lowercase-only candidate, but its 24 tests have not run. It is stacked on PR #16 and is not yet integrated or accepted.** |
| Phase 2 compatibility surface | Stable asset/layout/theme semantics and production tests showing existing projects remain unchanged | **PR #13 reference prototype merged to main and passes Python 3.10–3.13 CI; production Studio/renderer integration, Windows DPI and preview/export evidence are absent.** |
| [PR #21 — Phase 3.1 data adapter](https://github.com/PanDuroDev/LaunchForge/pull/21) | Standalone HTTPS JSON GET adapter, typed JSON Pointer field mapping, optional/default values, safe transformation allowlist and bounded response inspection; CI run [#41923174067](https://github.com/PanDuroDev/LaunchForge/actions/runs/41923174067) passed typecheck and fixture tests. | Open/unmerged; renderer-neutral prototype only. No DNS/IP egress protection, Studio/Runtime integration, approved serialized binding contract, credentials, actions or preview/export parity. Phase 3.2/3.3 remain gated. |
| Phase 4 game-operation contract | Approved manifest/lifecycle APIs and adversarial filesystem, integrity and recovery results | **Proposals/prototypes only (PR #12 and #17); #17 is POSIX-only and has no Windows backend or native Runtime integration.** |
| Phase 5 release readiness | Reproducible packaging, signed/update trust and recovery evidence, diagnostics, support boundaries, reviewed release gate | **PR #14 publisher inventory validator is merged; PR #15 updater proposal and PR #18 Phase 5.3 gate remain open. #18 records production FAIL / NO-GO; no accepted installed package/updater or clean-machine recovery evidence.** |
| Schema migrations | Versioned migration engine and supported migration chain, fixtures for every supported source version, rollback/backup behavior | **Policy proposed in PR #16; implementation and fixtures absent.** |
| Named maintenance ownership | A named maintainer and operational responsibility for each proposed supported capability | **Not recorded.** |
| User demand for an expansion | Specific recurring user workflow, requests/interviews/issues, and evidence the proposed track materially helps | **Not recorded.** |

The product plan's Windows-first direction and PR #16's target candidate are not yet a verified Studio or exported Launcher support commitment. Studio and exported Launcher support must be assessed separately.

## 6.1 catalog preparation update

The follow-up implementation now adds a machine-readable catalog and a dependency-free metadata validator:

- `conformance/phase6-catalog.json`: 40 planned cases across eight conformance areas. Every case includes surfaces, prerequisite-area labels, expected behavior, and required evidence. All cases remain `planned`; none is represented as executed. Its canonical `dependency_registry` contains 40 unique prerequisite-area labels, and every case reference is registered exactly once.
- `tools/validate_conformance_catalog.py`: standard-library CLI that validates exact catalog/case field sets, stable ID format/uniqueness, prefix/category consistency, product surfaces, dependency-label grammar, registry uniqueness/references, evidence fields, and types.
- `tests/test_phase6_catalog.py`: 15 unit tests for the validator and catalog expectations.
- `conformance/README.md`: reproducible commands and a clear distinction between catalog validation and actual product conformance.
- `.github/workflows/phase6-catalog.yml`: pull-request/push workflow that checks the committed catalog, runs the 15 unit tests, and compiles the Python files with Python 3.12.

The actual JSON catalog was fetched from the feature branch and independently checked for valid JSON, 36 unique IDs, all eight expected categories, 38 unique registry IDs matching the complete case-reference set, populated evidence fields, allowed surfaces, boolean mandatory flags, and planned lifecycle states; no structural errors were found. Following CodeRabbit feedback, duplicated/plural dependency aliases were normalized and the registry became the single source of truth for prerequisite labels. The validator and 13 unit tests initially passed locally against a generated 36-case fixture matching the committed catalog structure and test-family distribution; compileall succeeded, and AST inspection found docstrings on all 19 functions in the validator and test modules. The direct container clone attempt failed because DNS resolution was unavailable, so a repository-native GitHub Actions workflow was added to run the commands against the PR checkout itself. On commit `5523ee1e94df3a0c5ca063a49e07332655a722a2`, Actions run [41918666776](https://github.com/PanDuroDev/LaunchForge/actions/runs/41918666776) passed: catalog validator succeeded (36 cases / 8 categories), all 13 unit tests passed, and `compileall` succeeded. An earlier workflow attempt failed before tests because `actions/setup-python` was incorrectly configured with `cache: false`; that unsupported setting was removed and the subsequent runs passed. The latest complete run on the current PR head, commit `1161736a616d9a6eeb686d89deda6f13c94b30dd`, is [Actions run 41918815533](https://github.com/PanDuroDev/LaunchForge/actions/runs/41918815533): catalog validation, all 13 unit tests, and compileall completed successfully.

This remains 6.1 preparation only. The successful CI run validates the exact PR checkout's catalog and validator tests; it does not load Launcher Projects or exercise Studio, Runtime, renderer, migrations, packaging, or security behavior. Those product tests remain blocked until their Phase 0–5 contracts and fixtures are approved.

## 6.1 — Compatibility and conformance foundation

### Exit gate

6.1 may be implemented only after the Phase 0–5 contracts consumed by the compatibility layer are approved. It exits only when existing projects can be assessed deterministically and unsupported requirements are reported before build/export.

### Required contract inputs

The integration owner must identify and approve:

1. The project-format/schema version and its compatibility policy.
2. Stable component IDs, component property semantics, asset references, and capability identifiers.
3. The Runtime API version and the supported project-format range for each Runtime release.
4. Renderer identity, version, declared capabilities, and build-time target selection semantics.
5. The migration interface, ordering, failure behavior, backup/restore policy, and diagnostic format.
6. The shared fixture set used by Studio validation, preview, build, and exported Runtime.

Do not create a parallel schema or guess fields while those contracts are unsettled. Any shared-contract change requires an architecture-owner review, compatibility impact statement, migration note, and approval.

### Conformance suite required before support claims

The suite should use the same versioned fixtures across all applicable tools and include:

- **Format validation:** valid, invalid, unknown-version, missing-field, and malformed project documents.
- **Open/save stability:** supported projects round-trip without unexplained loss or semantic drift.
- **Migration:** every supported source version migrates through an explicit chain; failures preserve the original and provide actionable diagnostics.
- **Capability assessment:** Studio compares project requirements with the selected renderer/Runtime declarations and identifies each unsupported component or capability before export.
- **Preview/export parity:** equivalent fixtures produce equivalent supported behavior in preview and the exported Launcher.
- **Negative compatibility:** unknown required capabilities, incompatible Runtime ranges, missing assets, and unsupported actions fail closed rather than silently degrading.
- **Security:** imported project and asset validation, trust boundaries, credential redaction, and relevant Runtime permission tests.
- **Accessibility and localization:** keyboard/focus, scaling, Unicode, and RTL behavior for the actually supported feature set.
- **Packaging and update:** clean-environment install/upgrade, artifact integrity, update failure/recovery, and rollback checks on every claimed target.
- **Performance:** reproducible measurements against a documented sample project and agreed thresholds; do not invent thresholds or publish unmeasured claims.

Each test result must record the fixture version, tool/Runtime version, target OS, expected result, actual result, and diagnostic output. A demo or manually successful happy path is not conformance evidence.

### Support-matrix format

Maintain separate rows for Studio and exported Launcher. Never infer one from the other.

| Product surface | OS / environment | Project format range | Runtime / renderer | Status | Limitations and evidence |
|---|---|---|---|---|---|
| Studio | Windows (planned initial target) | Not established | Not established | **Not verified** | Await Phase 0–5 contracts and clean-environment validation |
| Exported Launcher | Windows (planned initial target) | Not established | Not established | **Not verified** | Await packaging, Runtime, update, and migration conformance |
| Studio | macOS | Not evaluated | Not evaluated | **Not supported / not evaluated** | Separate feasibility and packaging evaluation required |
| Exported Launcher | macOS | Not evaluated | Not evaluated | **Not supported / not evaluated** | Separate Runtime, renderer, update, and packaging evaluation required |
| Studio | Linux | Not evaluated | Not evaluated | **Not supported / not evaluated** | Separate feasibility and packaging evaluation required |
| Exported Launcher | Linux | Not evaluated | Not evaluated | **Not supported / not evaluated** | Separate Runtime, renderer, update, and packaging evaluation required |

Replace a status only when the matching conformance evidence is attached to the release/decision record. “Planned” and “not evaluated” must never be presented as “supported”.

## 6.2 — One evidence-backed expansion track

**Current decision: defer selection; no track is justified by the repository evidence.**

The candidate list in issue #8 remains open, but the repository presently has no observed user workflow data, product implementation, stable API surface, or per-track maintainer commitment. There is therefore no defensible evidence to rank one candidate over the others.

After 6.1 is approved, the integration owner should record exactly one selected track using this decision record:

| Required field | Evidence to record |
|---|---|
| Candidate track | Exactly one of P6-A through P6-E |
| User problem | Specific developer/publisher workflow that is currently blocked or costly |
| Demand evidence | Dated requests, interviews, support cases, or observed workflow frequency; distinguish facts from assumptions |
| Compatibility impact | Project-format, Runtime API, renderer, OS, data, and package effects |
| Security/privacy impact | New trust boundary, permissions, data exposure, and threat-model changes |
| Conformance plan | Existing fixtures reused, new cases added, and measurable pass criteria |
| Maintenance owner | Named individual/team accepting issue triage, compatibility, and release responsibility |
| Cost and rollback | Dependencies, ongoing support burden, and removal/deprecation plan |

A high-level preference, a prototype, or a single unverified request is not enough to announce support. If the evidence does not identify one justified track and a maintainer, keep all tracks deferred.

## 6.3 — Validate, document, and support the selected expansion

No 6.3 implementation or support claim can begin until a 6.2 decision has been approved. For the selected track, require all applicable gates:

- Contract and threat-model review completed before implementation.
- Positive and negative conformance tests pass against the same versioned fixtures as the existing supported product.
- Existing projects either remain compatible or receive an explicit, tested migration/unsupported-feature diagnostic.
- Accessibility, packaging, update, recovery, and performance tests pass for every claimed product surface and OS.
- Documentation states supported versions, unsupported capabilities, limitations, and migration behavior.
- A named maintainer accepts ownership and a support/deprecation policy is recorded.
- Release evidence is reviewed by the integration owner; a demo alone does not close the gate.

## Required handoff before Phase 6 implementation

The integration owner should attach or link the following reviewed artifacts before reopening implementation:

1. Accepted Phase 0–5 exit-gate records and merged implementation references.
2. The approved project/schema, migration, renderer/capability, Runtime, and build contracts.
3. The shared conformance fixtures and baseline test results.
4. The Phase 5 release/security/support record.
5. A named architecture owner and named maintenance ownership for the proposed capability.
6. User evidence supporting exactly one Phase 6 candidate track.

The contract-neutral conformance protocol is documented in `docs/phase6/CONFORMANCE_PLAN.md`, the case-to-candidate-contract mapping in `docs/phase6/CONTRACT_TRACEABILITY.md`, and the ordered prerequisite work in `docs/phase6/NEXT_HANDOFF.md`. Until the required contracts, fixtures, implementations, and reviews exist, the Phase 6 deliverable remains a readiness/protocol handoff. It intentionally adds no product feature, public API, project schema, or platform-support promise.


The current follow-up adds four contract-neutral `planned` cases for UUID schema/semantic-validator agreement, application-icon asset/ICO payloads, typed Phase 3.1 data mapping and privileged-host DNS/IP egress policy. The registry uses existing broad Phase 0/1 prerequisite labels; it does not prescribe a UUID casing rule or silently approve the candidate icon contract. The focused catalog test confirms both additions remain planned and retain their prerequisite labels.
