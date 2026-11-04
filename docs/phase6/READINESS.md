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
- No open pull requests were present at the time of inspection.
- Phase 0–5 issues (#2–#7) are still open. Their described exit gates have not been demonstrated by merged code or test evidence in this repository state.
- The visible Phase 1/2/4/5 work branches point to the same commit as `main`; they do not provide landed implementation or review evidence.
- No project schema, migration implementation, renderer registry, Runtime API, security test suite, build/package pipeline, support matrix, or Phase 5 release implementation is present in the inspected tree.

A branch name or an open phase issue is not evidence that its deliverables are implemented or accepted. This document does not infer completion from those signals.

## Dependency assessment

| Phase 6 prerequisite | Evidence required to pass | Current assessment |
|---|---|---|
| Phase 0 architecture and security contracts | Reviewed stack/renderer decision, project schema, Runtime/build interfaces, threat model, fixtures | **Not evidenced** |
| Phase 1 project and Runtime contracts | Merged implementation, versioned project format, stable component/capability contract, preview/export parity tests | **Not evidenced** |
| Phase 2 compatibility surface | Stable asset/layout/theme semantics and tests showing existing projects remain unchanged | **Not evidenced** |
| Phase 3 data/action contracts | Approved binding/action API and security behavior with shared preview/Runtime fixtures | **Not evidenced** |
| Phase 4 game-operation contract | Approved manifest/lifecycle APIs and adversarial filesystem, integrity, and recovery results | **Not evidenced** |
| Phase 5 release readiness | Reproducible packaging, signed/update trust and recovery evidence, diagnostics, support boundaries, reviewed release gate | **Not evidenced** |
| Schema migrations | Versioned migration chain, fixtures for every supported source version, rollback/backup behavior | **Not present** |
| Named maintenance ownership | A named maintainer and operational responsibility for each proposed supported capability | **Not recorded** |
| User demand for an expansion | Specific recurring user workflow, requests/interviews/issues, and evidence that the proposed track materially helps | **Not recorded** |

The product plan's provisional Windows-first direction is not a verified Studio or exported Launcher support claim. The plan itself says the technology direction remains provisional pending Phase 0 evidence.

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

Until those artifacts exist, this readiness record is the Phase 6 deliverable. It intentionally adds no product feature, public API, schema, or platform-support promise.
