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


## 2026-11-05 continuation update

This update supersedes the older blocker chronology above where it refers to the latest Phase 0 Windows workflow.

### Phase 6 status

- The catalog now contains **41 planned cases**, 40 unique dependency labels and 16 metadata unit tests. New coverage tracks UUID/schema agreement, application-icon packaging, typed data mappings, host-enforced network egress and portable Windows package verification.
- Every case remains `planned`. The catalog workflow validates metadata only; it does not establish product support.
- PR #11 (catalog foundation) and PR #19 (handoff refresh) are already merged. No further Phase 6 PR has been merged by this continuation.

### What changed upstream

1. **Phase 0 PR #16:** the latest Windows workflow [#41924747295](https://github.com/PanDuroDev/LaunchForge/actions/runs/41924747295) passed every step, including Tauri build, host smoke, portable ZIP packaging and upload. This supersedes the earlier ICO-fixture failure note. PR #16 is still open/unmerged and its candidate contracts are not approved. The run does not cover fresh-user VM acceptance, actual WebView2 preview/export parity, DPI/accessibility/RTL, or performance.
2. **Phase 0 verifier PR #23:** an earlier hosted fixture run passed, but the latest PR-head run [#41926599380](https://github.com/PanDuroDev/LaunchForge/actions/runs/41926599380) failed in the verifier test step. Review findings remain open. Resolve the current test/procedure findings and rerun on the current head before treating hosted validation as green. Fresh-user clean-VM acceptance remains separate.
3. **Phase 1 PR #22:** remains a draft. The Rust P1-A test suite has not been run; its successful Phase 0 workflow is not evidence that the new Rust crate compiles or passes.
4. **Phase 3 PR #21:** Stage 3.1 is merged. It is still a renderer-neutral transport/mapping prototype, not integrated Studio/Runtime behavior and not a DNS/IP egress defense.
5. **Phase 4 PR #25:** the current transaction/lifecycle prototype is POSIX-only. A Windows/NTFS backend, reparse-point tests and native Runtime integration remain necessary.
6. **Phase 5:** PRs #14 and #18 are merged; PR #18 continues to declare production **FAIL / NO-GO**. PR #15 is still a TUF design proposal, not an updater.

### Ordered next actions

| Order | Owner | Required exit evidence before Phase 6 consumes the result |
|---|---|---|
| 1 | Phase 0 / integration owner | Review/approve PR #16 contracts and ADR; complete fresh-user Windows x64/WebView2 validation, preview/export interaction parity, 100/150/200% DPI, keyboard/focus, Unicode/RTL, accessibility and reproducible performance measurements. |
| 2 | Phase 0 verifier owner | Resolve PR #23's outstanding review findings, pass the latest-head verifier workflow, verify the outer artifact/inner package extraction procedure, and retain a fresh standard-user Windows VM report. |
| 3 | Phase 1 owner | Run the P1-A Rust tests on the selected toolchain; integrate project persistence against the approved schema and demonstrate a supported Studio/Runtime/build path. |
| 4 | Phase 2/3 owners | Accept the layout/data/action/credential semantics actually used by supported projects; add host DNS/IP egress enforcement and Preview/Runtime fixture evidence where data capabilities are included. |
| 5 | Phase 4 owner | Approve manifest/lifecycle boundaries; provide a Windows-safe transaction backend, NTFS reparse-point protections, native Runtime integration and Windows interruption/recovery evidence. |
| 6 | Phase 5 owner | Clear the documented FAIL / NO-GO findings; accept package/release/trust interfaces, implement and test the updater/recovery path, integrate diagnostics with Runtime, and assign release authority. |
| 7 | Phase 6 integration owner | Confirm fixture ownership, exact supported tuples, reviewed contracts, evidence retention and a named maintainer. Then execute 6.1. Only after a reviewed 6.1 exit may one evidence-backed 6.2 track be selected. |

No expansion track is selected. No user-demand record or maintenance owner is present. Keep 6.2 and 6.3 deferred; do not invent an expansion to fill the schedule.
