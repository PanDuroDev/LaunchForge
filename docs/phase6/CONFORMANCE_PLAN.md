# Phase 6.1 — Compatibility and Conformance Protocol

**Status:** Protocol specification only. The executable runner and product adapters are blocked on approved Phase 0/1 contracts and the later phase contracts they consume.

## Purpose

Define one repeatable way to decide whether a particular Studio build, exported Launcher Runtime, project format, renderer, and target environment are compatible.

This document is deliberately contract-neutral. It does not define a project JSON schema, public API, renderer interface, migration function signature, or test-runner technology. Those must be consumed from reviewed Phase 0/1 decisions. Do not turn examples in this document into shared API names without architecture-owner approval.

A compatibility result is always scoped to an exact tuple:

- Product surface: **Studio** or **exported Launcher**.
- Product build/version and, when applicable, Runtime version.
- Project-format/schema version.
- Renderer ID and version, where applicable.
- Target OS, architecture, and supported baseline.
- Required capability set and the capability set declared by the target.

Studio compatibility and exported Launcher compatibility are separate results. Passing one must never imply the other.

## 1. Conformance result vocabulary

Every individual test and every support-matrix entry uses one of these outcomes:

| Outcome | Meaning |
|---|---|
| **PASS** | The test completed and all contract-defined expectations were met. |
| **FAIL** | The test completed and one or more expectations were violated. |
| **BLOCKED** | The test could not be run because a prerequisite contract, fixture, environment, or artifact is unavailable. This is not a pass. |
| **NOT APPLICABLE** | The test does not apply to the declared product surface/target; record the reason. |

Do not collapse BLOCKED into PASS, or describe an untested target as supported. A release-level support result is PASS only when all mandatory tests for that exact target tuple pass and no unresolved release-blocking finding remains.

## 2. Fixture organization

Once the schema and fixture ownership are approved, keep fixtures versioned and immutable. A proposed layout (not a required repository path until the integration owner approves it):

```text
compatibility/
  fixtures/
    projects/
      valid/
      invalid/
      legacy/
      capability-requirements/
    assets/
      valid/
      missing/
      unsafe-reference/
    renderer/
      shared-visual-cases/
      interaction-cases/
    migrations/
      <source-format-version>/
        input/
        expected/
  expectations/
    compatibility-cases.yaml
  results/
    <tool>-<version>/
      <target-tuple>/
        summary.json
        diagnostics/
        screenshots-or-traces/
```

Each fixture must have a stable ID, declared source format version, purpose, expected outcome, and ownership. Expected outputs must be reviewed alongside the contract they test. Do not place secrets, private user data, copyrighted publisher assets without permission, or machine-specific absolute paths in shared fixtures.

## 3. Test inventory

The identifiers below are stable planning IDs, not executable test names. The integration owner may map them to the chosen test framework after the relevant interface is frozen.

### A. Project-format and round-trip compatibility

| Test ID | Scenario | Expected result |
|---|---|---|
| LF-COMPAT-001 | Open a valid project whose format version is declared supported by the target Studio/Runtime | Open succeeds; the tool reports the correct format/runtime tuple. |
| LF-COMPAT-002 | Open a malformed project or a project missing a required contract field | Fail closed with a stable, actionable diagnostic; do not partially overwrite the source. |
| LF-COMPAT-003 | Open a project with an unknown format major version | Do not guess, silently coerce, or discard fields; report unsupported format/version. |
| LF-COMPAT-004 | Save and reopen each supported fixture without semantic edits | Stable IDs, references, properties, and required data retain contract-defined meaning. |
| LF-COMPAT-005 | Open a project containing an unsupported optional feature | Follow the approved preservation/diagnostic policy; never silently remove data. |
| LF-COMPAT-006 | Open a project containing an unknown required capability | Block build/export and identify the unsupported requirement. |

Round-trip comparisons must use a schema-aware semantic comparison approved with the project contract. Byte-for-byte JSON equality is not required unless the serialization contract explicitly requires it.

### B. Migration compatibility

| Test ID | Scenario | Expected result |
|---|---|---|
| LF-MIG-001 | Migrate each supported source format version to a target format version | A deterministic approved migration path exists and output validates against the target schema. |
| LF-MIG-002 | Migrate a fixture with assets, stable IDs, bindings, actions, and optional fields | Every supported semantic value and reference remains correct; any unsupported value is explicitly diagnosed. |
| LF-MIG-003 | Force a migration failure midway | Original source remains recoverable; no partially migrated project is presented as successful. |
| LF-MIG-004 | Re-run the migration check on an already-current project | No repeated destructive transformation; report that no migration is needed. |
| LF-MIG-005 | Encounter a source version for which no migration path is approved | Stop with the source preserved and identify the unsupported version/path. |
| LF-MIG-006 | Migrate a project with missing or invalid asset references | Preserve source data and report each invalid reference according to the approved migration policy. |

The migration owner must specify backup/restore mechanics, atomicity, downgrade policy, and whether migration is opt-in or automatic before tests are implemented. This protocol does not select those semantics.

### C. Renderer and capability conformance

| Test ID | Scenario | Expected result |
|---|---|---|
| LF-CAP-001 | Compare a project's required capability set with the selected renderer's declared set | Validation produces a deterministic supported/unsupported report. |
| LF-CAP-002 | A required component or capability is absent from the target declaration | Build/export is blocked before packaging; diagnostics identify the exact requirement. |
| LF-CAP-003 | A capability identifier or version is unknown to the target | Fail closed unless the approved compatibility policy explicitly classifies it as optional. |
| LF-CAP-004 | A renderer changes or removes a capability between versions | Compatibility assessment reports the change and runs affected regression fixtures. |
| LF-CAP-005 | Two renderers claim the same capability contract | Both pass the same shared behavior fixtures before the capability is treated as portable. |

A capability declaration is not evidence by itself. The behavior behind every claimed capability must pass the associated conformance fixtures.

### D. Studio preview and exported Runtime parity

| Test ID | Scenario | Expected result |
|---|---|---|
| LF-PARITY-001 | Render the same supported visual fixture in Studio preview and exported Launcher | Contract-defined geometry, visible content, states, and interaction outcomes match within agreed tolerances. |
| LF-PARITY-002 | Exercise supported interactions/actions with deterministic test data | Event results and observable state changes match across preview and exported Runtime. |
| LF-PARITY-003 | Use missing assets, offline data, malformed content, or action failures | Both surfaces produce the contract-defined fallback and diagnostic behavior. |
| LF-PARITY-004 | Resize supported window sizes and DPI/scaling configurations | Both surfaces follow the approved layout and scaling rules. |
| LF-PARITY-005 | Run keyboard, focus, Unicode, and supported RTL fixtures | Both surfaces meet the accessibility/localization contract for the declared feature set. |

The project plan prefers a shared renderer implementation. If preview and export use different execution paths, the owner must document the deliberate difference and provide equivalent test evidence.

### E. Security and import-boundary conformance

| Test ID | Scenario | Expected result |
|---|---|---|
| LF-SEC-001 | Import malformed, oversized, or structurally invalid project input | Reject safely with bounded resource use and actionable diagnostics. |
| LF-SEC-002 | Import an asset reference that escapes the authorized project asset root | Reject according to the approved path policy; no outside file is read or modified. |
| LF-SEC-003 | Scan project/export artifacts containing prohibited credentials | Export gate blocks and reports a sanitized finding; secret value is not echoed. |
| LF-SEC-004 | Exercise actions not present in the approved allowlist | Deny the action; no arbitrary process, shell, or filesystem behavior occurs. |
| LF-SEC-005 | Produce diagnostic output after a credential-bearing failure fixture | Logs and bundles redact secrets and private values per the approved policy. |

Security tests must be based on the Phase 0 threat model and the approved Runtime permission boundary. This list does not replace adversarial testing owned by Phases 3–5.

### F. Packaging, update, and recovery conformance

| Test ID | Scenario | Expected result |
|---|---|---|
| LF-PKG-001 | Install the declared package on a clean supported environment | Installation succeeds with only documented prerequisites. |
| LF-PKG-002 | Upgrade from each declared supported prior package version | User projects/configuration are preserved according to the migration and release contracts. |
| LF-PKG-003 | Verify an exported artifact against its release inventory and trust policy | Integrity and signing status are accurately reported; unsigned artifacts are not represented as trusted. |
| LF-PKG-004 | Interrupt or fail an application update at each documented stage | Previous working version remains usable or the documented recovery procedure succeeds. |
| LF-PKG-005 | Uninstall and reinstall the package | Behavior matches the documented data-retention and cleanup policy. |

These cases become runnable only when Phase 5 provides reviewed package, update, trust, and recovery contracts. A publisher artifact inventory alone is not an updater or trust protocol.

### G. Performance and operational evidence

| Test ID | Scenario | Expected result |
|---|---|---|
| LF-PERF-001 | Open and validate the agreed representative project | Measurements are reproducible and compared with architecture-owner-approved thresholds. |
| LF-PERF-002 | Render the representative project in preview/export | Startup, idle resource use, memory, and rendering behavior are recorded for the exact target tuple. |
| LF-PERF-003 | Run the agreed repeated workflow | Detect regressions against a retained, comparable baseline. |
| LF-OPS-001 | Re-run the complete conformance set from a clean checkout/environment | Results are reproducible; toolchain and fixture versions are recorded. |

Do not set numerical thresholds in this document. Thresholds must be accepted based on Phase 0 measurements and the declared supported environment.

## 4. Required test-result record

Every run must produce a machine-readable summary plus retained logs/traces. Exact field names and serialization format remain pending approval, but the record must capture:

| Field | Required information |
|---|---|
| Run identity | Unique run ID, UTC timestamp, CI/job reference |
| Source identity | Commit SHA, dirty/clean state, dependency/toolchain versions |
| Fixture identity | Fixture-set revision and per-fixture IDs |
| Product identity | Studio/Launcher surface, product version, Runtime version |
| Target identity | OS, architecture, baseline, renderer ID/version |
| Project identity | Project-format version and migration path, when relevant |
| Capability identity | Required and declared capability sets |
| Results | Pass/fail/blocked/not-applicable counts and individual outcomes |
| Diagnostics | Sanitized error IDs, logs, screenshots/traces where useful |
| Ownership | Test owner, release/integration reviewer, unresolved exceptions |

A result without exact source, fixture, and target identity is not evidence for a support claim.

## 5. Support matrix publication rule

Publish separate support entries for Studio and exported Launcher. At minimum, each entry must identify:

- Product surface and release version.
- OS, architecture, and minimum supported OS baseline.
- Project-format version range accepted by that surface.
- Runtime and renderer versions, where applicable.
- Declared capabilities and known unsupported capabilities.
- Package/install/update status for exported Launcher.
- Conformance-run reference and result.
- Known limitations, migration requirements, and deprecation dates.
- Named maintenance owner and date last verified.

Use explicit states such as **supported**, **preview/experimental**, **not evaluated**, and **unsupported**. A support statement must link to the passing conformance evidence for the exact tuple. Studio support never implies exported Launcher support.

## 6. Execution order and current blockers

Do not run these tests against guessed interfaces. The implementation sequence is:

1. Approve Phase 0 stack, threat model, project format, component/renderer contract, Runtime/build boundary, and baseline measurement protocol.
2. Accept Phase 1 schema, fixture, migration metadata, and preview/export behavior contracts.
3. Accept the Phase 2 layout/assets/localization contracts and Phase 3 binding/action/security contracts that affect project compatibility.
4. Accept the Phase 4 manifest/filesystem/lifecycle contracts and Phase 5 package/update/trust/recovery contracts.
5. Implement the harness and adapters against the approved APIs, then run the inventory above on each claimed target tuple.
6. Publish the support matrix only after evidence review by the architecture/integration owner and named maintainer.

### Current repository findings (2026-11-04)

- `main` now contains the Phase 6 catalog/metadata validator and the merged Phase 2.1 Python layout reference with multi-version CI. It still has no production Studio application, exported Runtime, production renderer integration, migration engine, or Windows package lifecycle.
- PR #9 is a Phase 1 readiness document, not implementation; it remains open and unmerged.
- PR #10 is a Phase 2 authoring specification, not production Studio implementation; it remains open and unmerged.
- PR #13's Phase 2.1 layout reference was merged into main. Its Python CI passed on 3.10–3.13, but it remains a reference prototype, not a production renderer/Studio integration.
- PR #12 proposes a Phase 4.1 distribution manifest and Python downloader prototype. Its contract is proposed/prototype-only and not approved for Runtime integration. Its PR reports 28 passing tests, but transport is mocked and install transactions, Runtime APIs, and recovery are not implemented. The PR remains open and unmerged.
- PR #17 adds POSIX-only install/update/repair/verify/recovery and lifecycle reference code; it explicitly has no Windows backend or native Runtime integration.
- PR #14 adds publisher artifact-inventory validation, but the inventory is explicitly not a launcher updater manifest or trust statement. PR #15 proposes TUF updater trust/recovery but does not implement an updater. PR #18 adds diagnostics/security/release-gate materials and explicitly records production **FAIL / NO-GO** until Runtime/package, Windows baseline, updater, clean install/recovery and Runtime diagnostics integration are proven.

Therefore all executable conformance cases in this document are currently **BLOCKED**. This is an accurate result, not a failure of the proposed test design.

## Exit gate for 6.1

6.1 is ready for implementation only when the contracts in step 1–4 are reviewed and accepted, fixtures have a named owner, and an integration owner approves the harness boundary.

6.1 is complete only when:

- All mandatory test cases for the declared support tuples are executable.
- Every existing supported project fixture receives a deterministic compatibility result.
- Unsupported components/capabilities are diagnosed before export.
- Migration success/failure paths preserve source projects and report actionable diagnostics.
- Studio/Launcher parity and packaging/update evidence passes for each claimed support tuple.
- The support matrix links to reproducible evidence and has a named maintainer.

Until then, this protocol is a specification/handoff artifact and does not announce any added platform, renderer, extension API, or production support.


## 7. Machine-readable catalog and metadata validation

The planned cases are mirrored in `conformance/phase6-catalog.json`. Each entry records its stable test ID, category, scenario, expected behavior, applicable product surfaces, prerequisite-area labels, required evidence, mandatory flag, and lifecycle state. The catalog also has one canonical `dependency_registry`; every case dependency must match one registered identifier and the registry must not contain duplicate identifiers.

All 38 entries currently use `lifecycle: planned`. The 38 registered dependency strings are planning labels only and are not approved API names or proof that the dependencies exist. Keep each prerequisite area under one canonical label; do not introduce spelling/plural aliases.

Validate the catalog structure from the repository root:

```sh
python tools/validate_conformance_catalog.py
python -m unittest discover -s tests -p "test_phase6_catalog.py" -v
```

The standard-library validator checks catalog metadata, not LaunchForge behavior. The unit tests cover valid catalog structure, all protocol families, duplicate IDs, category/ID consistency, missing dependencies, invalid surfaces, field types, and invalid roots. A successful catalog check must never be reported as a passing product conformance run.


## 8. CI gate for catalog maintenance

The repository workflow `.github/workflows/phase6-catalog.yml` runs on relevant pull requests and pushes to `main` / the Phase 6 working branch. It uses Python 3.12 and runs, in order:

1. `python tools/validate_conformance_catalog.py`
2. `python -m unittest discover -s tests -p "test_phase6_catalog.py" -v`
3. `python -m compileall -q tools/validate_conformance_catalog.py tests/test_phase6_catalog.py`

A passing workflow demonstrates catalog metadata/test-harness health only. It is not a substitute for product-level migration, renderer, Runtime, packaging, security, or support-matrix conformance. The initial workflow attempt exposed an invalid `actions/setup-python` `cache: false` setting; the setting was removed, and the subsequent run passed on the exact PR checkout (the earlier baseline of 36 catalog cases, 13 unit tests, compileall).

## 9. Upstream contract traceability

The current candidate contract and evidence mapping is maintained in `docs/phase6/CONTRACT_TRACEABILITY.md`. Consult it before translating a planned case into an executable adapter. It distinguishes PR-branch proposals from accepted interfaces, maps Phase 6 case groups to Phase 0/1/2/4/5 candidate artifacts, and records coverage gaps that must be reconciled after the integration owner approves those artifacts.

The traceability map is provisional. Do not encode candidate schema/API details into the stable conformance catalog or mark tests implemented until the referenced upstream contract is accepted.

## 10. Latest prerequisite blockers (2026-11-04)

- Phase 0 PR #16's first Tauri run [#41919048099](https://github.com/PanDuroDev/LaunchForge/actions/runs/41919048099) failed because `poc/src-tauri/icons/icon.ico` was missing. That was fixed: the subsequent Windows run [#41919850333](https://github.com/PanDuroDev/LaunchForge/actions/runs/41919850333) passed contract/renderer tests, renderer export, Rust lockfile generation/build, host smoke test, portable packaging and artifact upload. However, the latest head [#41920824672](https://github.com/PanDuroDev/LaunchForge/actions/runs/41920824672) fails 12/13 tests at `poc/tests/phase0.test.mjs:53`: the ICO negative fixture truncates the last file byte, which may be outside declared image payload ranges. Correct the fixture and rerun. The current Phase 0 tree still has no tracked `poc/src-tauri/Cargo.lock`; commit/review it. Clean-machine/WebView2, DPI/accessibility and performance evidence remain outstanding.
- Phase 4 PR #17 is POSIX-only and explicitly has no Windows backend. Its 40 local tests do not demonstrate Windows/NTFS path safety, reparse-point handling, real host process launch or power-loss recovery.
- Phase 0's candidate JSON Schema accepts uppercase and lowercase UUIDv4 hex, while the semantic validator regex accepts lowercase only. The integration owner must choose and test one canonical rule before Phase 1 freezes the schema.
- Phase 5 PR #18 records **FAIL / NO-GO** because the accepted Runtime/package, supported Windows baseline, updater, clean-machine install/recovery evidence and Runtime diagnostics integration are absent. PRs #14 and #15 remain unmerged QA/design contributions, not a production updater.

These failures and boundaries keep executable Phase 6 product conformance, 6.2 expansion selection, and 6.3 support blocked. Do not lower the gate because isolated test suites pass on another OS or a reference prototype passes.

## 11. Newly tracked project-format cases

- `LF-COMPAT-007` requires the approved UUID canonicalization rule to be implemented identically by the project JSON Schema and semantic validator, including stable-ID uniqueness for case variants.
- `LF-COMPAT-008` requires the approved application-icon reference to validate and the complete declared ICO payload to be bounded and embedded byte-for-byte in the package.

Both remain planned until Phase 0/1 approves the source contracts and supplies runnable fixtures. The catalog does not choose UUID casing or add schema fields.
