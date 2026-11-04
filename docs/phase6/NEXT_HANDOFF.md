# Phase 6 next-step handoff

**Assessment date:** 2026-11-04  
**Current Phase 6 status:** 6.1 preparation merged; executable product conformance blocked; 6.2 and 6.3 not started  
**Related parent:** Issue #8

## Why Phase 6 cannot advance to product conformance yet

The Phase 6 catalog workflow is green, but it validates only the 36-case catalog, its metadata validator, 13 unit tests and Python compilation. It does not validate LaunchForge Studio, exported Runtime, project migration, packaging, game installation or launcher updates.

The current upstream evidence has explicit blockers:

1. **Phase 0 / PR #16:** the initial Windows run failed because `poc/src-tauri/icons/icon.ico` was missing; that was fixed and run [#41919850333](https://github.com/PanDuroDev/LaunchForge/actions/runs/41919850333) then passed contract/renderer tests, renderer export, Rust lockfile generation/build, host smoke test, portable package and artifact upload. The latest head run [#41920824672](https://github.com/PanDuroDev/LaunchForge/actions/runs/41920824672) now fails 12/13 tests at the new ICO truncation negative fixture (`poc/tests/phase0.test.mjs:53`): it removes the final byte of the whole file, which may not truncate a declared image payload. Correct the fixture and rerun. The PR remains open/unmerged, has no submitted review, and its current tree still lacks a tracked `poc/src-tauri/Cargo.lock`; clean-machine/WebView2 parity/DPI/accessibility/performance evidence and architecture approval remain pending.
2. **Phase 1 / PR #9:** the readiness and acceptance plans exist. A Rust P1.1 implementation has been reported as in development against the candidate schema, but it is not yet merged into main. Before contract acceptance, resolve the schema/semantic-validator UUID casing mismatch and retain the required `window.iconAssetId` → `applicationIcon` mapping. The full Studio/Runtime/export journey and clean-Windows gate are not demonstrated.
3. **Phase 2 / PRs #10 and #13:** PR #13's deterministic Python layout reference is now merged into main and passes CI on Python 3.10–3.13. It remains a geometry prototype, not a production layout engine, Studio or exported Runtime. PR #10 is still an authoring specification.
4. **Phase 4 / PRs #12 and #17:** #12 is a proposed manifest/downloader with mocked transport; #17 is a POSIX transaction prototype that explicitly has no Windows backend. Neither provides an approved Windows Runtime game-lifecycle contract.
5. **Phase 5 / PRs #14, #15 and #18:** #14 is publisher inventory QA, not updater trust; #15 is TUF design only; #18's own security/release conclusion is **FAIL / NO-GO** pending an accepted Runtime/package, Windows baseline, updater, clean-machine install/recovery and Runtime diagnostics integration.

The unmerged PRs are useful engineering work, but they are not approved contracts or completed phase gates. A Phase 6 adapter must not consume them as stable APIs yet.

## Ordered next actions

These actions belong to the named upstream owners/integration owner. Phase 6 should consume the accepted outputs; it must not create parallel versions of the contracts.

| Order | Owner / prerequisite | Required exit evidence | Phase 6 action after acceptance |
|---|---|---|---|
| 1 | Phase 0 owner — PR #16 | Correct the ICO negative fixture so it truncates within a declared image payload; rerun contract tests, renderer export, Tauri host build, standalone smoke test, portable package build/validation and artifact upload. Commit/review `Cargo.lock`; align UUID schema/semantic-validator casing; then record fresh-user Windows VM, WebView2 preview/export, DPI/accessibility and measurement evidence; obtain explicit architecture approval. | Freeze the exact supported contract versions and map the 36 case IDs to approved schema/capability/diagnostic identifiers. |
| 2 | Phase 1 owner — Issue #3 / PR #9 | Implement project create/open/save and schema validation; establish versioned fixtures, stable IDs/assets and a real Studio/Runtime/renderer/build boundary; pass preview/export and clean-Windows first-user journey. | Implement Phase 6 compatibility adapters for supported project/runtime tuples, then make format, capability and parity cases executable. |
| 3 | Phase 2/3 owners — Issues #4/#5 | Accept layout/assets/RTL/localization semantics and the data/action/credential contracts actually included in supported projects; demonstrate existing-project preservation. | Implement the corresponding layout, accessibility, data/action and migration fixtures/adapters. |
| 4 | Phase 4 owner — Issue #6 / PRs #12/#17 | Approve the manifest and lifecycle boundary; implement a Windows-safe filesystem transaction backend, NTFS reparse-point protections and native Runtime integration; pass Windows interruption, recovery, integrity and launch tests. | Activate the game-delivery and filesystem/security cases only against accepted Windows behavior. |
| 5 | Phase 5 owner — Issue #7 / PRs #14/#15/#18 | Resolve the documented FAIL / NO-GO findings; accept package/release/trust contracts; integrate diagnostics with Runtime; implement updater and recovery; pass clean-machine install/upgrade/uninstall/update/rollback tests on the supported Windows baseline; assign a release authority. | Activate package, updater, trust, diagnostics and recovery conformance cases and publish a separately evidenced Studio/Launcher support matrix. |
| 6 | Phase 6 integration owner | Confirm the accepted artifacts above, fixture owner, exact target tuple, architecture owner and maintainer. | Run the full applicable 6.1 suite. Only after a reviewed 6.1 exit decision may 6.2 select exactly one evidence-backed track. |

## Phase 6 work remaining after prerequisites

### 6.1 — Execute conformance

- Map every catalog planning dependency to the accepted upstream contract/version. Do not silently rename approved identifiers.
- Add executable adapters to the actual schema validator, migration engine, renderer capability registry, Studio preview, exported Runtime, build pipeline and package/updater paths.
- Keep all currently planned cases marked `planned` until the actual behavior has a repeatable test and retained result.
- Run positive, negative, migration, parity, security, recovery and performance cases using the same immutable fixture revision across applicable product surfaces.
- Publish separate support results for Studio and exported Launcher. A CI green status on this documentation/catalog PR is not a product support result.

### 6.2 — Select one expansion only

Do not select P6-A through P6-E until a specific recurring developer/publisher workflow is evidenced by dated user requests, interviews, support cases or observed usage. Record exactly one selected track, security/compatibility impact, expected maintenance cost, rollback/deprecation plan and named maintainer.

### 6.3 — Validate and support

The selected capability must pass its security, migration, accessibility, packaging, update/recovery and performance gates for each claimed target. Publish limitations and support versions, assign issue triage/deprecation ownership, and retain the reproducible evidence with the release.

## Current decision

Continue to hold executable product conformance, 6.2 selection and 6.3 support. The next blocker-removal action is Phase 0 PR #16's Windows Tauri build failure and integration-owner approval; Phase 4/5 platform and release gates must then be completed in their own reviewed stages. Do not use another prototype or a green catalog workflow as a waiver.
