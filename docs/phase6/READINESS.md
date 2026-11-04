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
- Phase 0–5 issues (#2–#7) are still open. Their described exit gates have not been demonstrated by merged code or test evidence in this repository state.
- At the initial baseline inspection, visible Phase 1/2/4/5 work branches pointed to the same commit as `main`. A later audit found branch advances, which are recorded separately below; those unmerged branches still do not establish accepted contracts or landed implementation.
- No project schema, migration implementation, renderer registry, Runtime API, security test suite, build/package pipeline, support matrix, or Phase 5 release implementation is present in the inspected tree.

A branch name or an open phase issue is not evidence that its deliverables are implemented or accepted. This document does not infer completion from those signals.


## Follow-up evidence review

A follow-up review of the active work branches and pull requests on 2026-11-04 found additional preparation, but no accepted prerequisite:

| Work item | Newly visible evidence | Phase 6 impact |
|---|---|---|
| PR #9 — Phase 1 readiness | Documentation mapping Phase 1 dependencies and exit evidence; no application implementation | Helpful handoff, but project schema, Runtime and renderer contracts remain unapproved |
| PR #10 — Phase 2 authoring specification | Detailed authoring/layout/accessibility specification; no Studio or Runtime implementation | Defines future compatibility cases, but consumes Phase 0/1 contracts that are still absent |
| PR #12 — Phase 4.1 prototype | Proposed manifest contract and isolated Python downloader prototype; PR body reports 28 tests passing | Useful candidate fixture/contract input only; draft, unmerged, not Runtime-integrated, and explicitly not approved |
| Phase 5.1 branch | One publisher artifact-inventory JSON Schema | Inventory is for publisher release QA; it explicitly is not an updater manifest or trust statement. No completed release process is evidenced |
| PR #11 — this Phase 6 readiness handoff | Draft documentation PR; CodeRabbit noted that draft PRs are not automatically reviewed | Awaiting human/integration-owner review; no approval has been recorded |

The Phase 4.1 prototype reports deterministic mocked transport tests, not a live publisher integration or install/update recovery test. The proposed manifest contract defers reparse-point protection, secure install-root writes, key lifecycle, durable anti-rollback state, and Runtime lifecycle integration to later approved contracts. These gaps prevent treating Phase 4 as a stable dependency.

The Phase 5.1 artifact inventory records build provenance, package metadata, hashes, and signing status. It does not itself implement or prove clean-machine installation, publisher release publication, signed launcher update metadata, trust bootstrap/rotation/revocation, rollback, or recovery. It is also on an unmerged branch, so it is not part of the current baseline.

**Updated gate decision:** continue with contract-neutral 6.1 preparation (this conformance protocol and the support-matrix requirements), but keep executable conformance, 6.2 track selection, and 6.3 support work blocked. Do not reinterpret work-in-progress branches or draft PRs as reviewed/accepted contracts.

## Dependency assessment

| Phase 6 prerequisite | Evidence required to pass | Current assessment |
|---|---|---|
| Phase 0 architecture and security contracts | Reviewed stack/renderer decision, project schema, Runtime/build interfaces, threat model, fixtures | **Not evidenced** |
| Phase 1 project and Runtime contracts | Merged implementation, versioned project format, stable component/capability contract, preview/export parity tests | **Not evidenced** |
| Phase 2 compatibility surface | Stable asset/layout/theme semantics and tests showing existing projects remain unchanged | **Not evidenced** |
| Phase 3 data/action contracts | Approved binding/action API and security behavior with shared preview/Runtime fixtures | **Not evidenced** |
| Phase 4 game-operation contract | Approved manifest/lifecycle APIs and adversarial filesystem, integrity, and recovery results | **Proposal/prototype only (PR #12); not approved or Runtime-integrated** |
| Phase 5 release readiness | Reproducible packaging, signed/update trust and recovery evidence, diagnostics, support boundaries, reviewed release gate | **Not evidenced; unmerged branch contains artifact-inventory schema only** |
| Schema migrations | Versioned migration chain, fixtures for every supported source version, rollback/backup behavior | **Not present** |
| Named maintenance ownership | A named maintainer and operational responsibility for each proposed supported capability | **Not recorded** |
| User demand for an expansion | Specific recurring user workflow, requests/interviews/issues, and evidence that the proposed track materially helps | **Not recorded** |

The product plan's provisional Windows-first direction is not a verified Studio or exported Launcher support claim. The plan itself says the technology direction remains provisional pending Phase 0 evidence.

## 6.1 catalog preparation update

The follow-up implementation now adds a machine-readable catalog and a dependency-free metadata validator:

- `conformance/phase6-catalog.json`: 36 planned cases across eight conformance areas. Every case includes surfaces, prerequisite-area labels, expected behavior, and required evidence. All cases remain `planned`; none is represented as executed. Its canonical `dependency_registry` contains 38 unique prerequisite-area labels, and every case reference is registered exactly once.
- `tools/validate_conformance_catalog.py`: standard-library CLI that validates exact catalog/case field sets, stable ID format/uniqueness, prefix/category consistency, product surfaces, dependency-label grammar, registry uniqueness/references, evidence fields, and types.
- `tests/test_phase6_catalog.py`: 13 unit tests for the validator and catalog expectations.
- `conformance/README.md`: reproducible commands and a clear distinction between catalog validation and actual product conformance.
- `.github/workflows/phase6-catalog.yml`: pull-request/push workflow that checks the committed catalog, runs the 13 unit tests, and compiles the Python files with Python 3.12.

The actual JSON catalog was fetched from the feature branch and independently checked for valid JSON, 36 unique IDs, all eight expected categories, 38 unique registry IDs matching the complete case-reference set, populated evidence fields, allowed surfaces, boolean mandatory flags, and planned lifecycle states; no structural errors were found. Following CodeRabbit feedback, duplicated/plural dependency aliases were normalized and the registry became the single source of truth for prerequisite labels. The validator and 13 unit tests initially passed locally against a generated 36-case fixture matching the committed catalog structure and test-family distribution; compileall succeeded, and AST inspection found docstrings on all 19 functions in the validator and test modules. The direct container clone attempt failed because DNS resolution was unavailable, so a repository-native GitHub Actions workflow was added to run the commands against the PR checkout itself. On commit `5523ee1e94df3a0c5ca063a49e07332655a722a2`, Actions run [41918666776](https://github.com/PanDuroDev/LaunchForge/actions/runs/41918666776) passed: catalog validator succeeded (36 cases / 8 categories), all 13 unit tests passed, and `compileall` succeeded. An earlier workflow attempt failed before tests because `actions/setup-python` was incorrectly configured with `cache: false`; that unsupported setting was removed and the subsequent run passed.

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

The contract-neutral conformance protocol is now documented in `docs/phase6/CONFORMANCE_PLAN.md`. Until the required contracts, fixtures, implementations, and reviews exist, the Phase 6 deliverable remains a readiness/protocol handoff. It intentionally adds no product feature, public API, project schema, or platform-support promise.
