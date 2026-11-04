# Phase 5 security and reliability review

> **Assessment: NOT READY FOR PRODUCTION.** This is an evidence-bounded review of the current public repository baseline and the open implementation/design branches surfaced for Phase 5 review. It is not a penetration test or a completed whole-product security audit: the integrated Studio, Runtime, packaging and updater do not exist in the accepted mainline baseline.

## 1. Review scope and evidence

Reviewed:

- \`docs/PROJECT_PLAN.md\` and Phase 5 issue #7 security/release acceptance criteria.
- Mainline baseline at \`3d24d286118892b948424c547f91db3d1ce7ed84\`.
- PR #9 Phase 1 readiness and acceptance-plan documents.
- PR #10 Phase 2 authoring specification and PR #13 isolated layout reference prototype.
- PR #12 / branch \`ai5/phase4-1-manifest-download-prototype\`: proposed game manifest and bounded HTTPS downloader code, README, and game distribution contract.
- PR #14 Phase 5.1 publisher artifact inventory, validator, release workflow and its automated review findings.
- PR #15 Phase 5.2 TUF trust proposal and conformance matrix.

The referenced phase PRs are separate open proposals/prototypes, not approved integrated product code. The baseline main branch remains documentation-only. No production Windows package or Runtime binary was available for dynamic testing.

## 2. Findings

| ID | Severity | Finding | Evidence / impact | Required owner and exit evidence |
|---|---|---|---|---|
| LF-SEC-001 | **Blocker** | No approved integrated Runtime, export/package contract or supported Windows baseline | Phase 1 readiness states the app source, renderer, Runtime, build scripts and Windows package configuration are absent. Install/update behavior cannot be verified against a real executable. | Phase 0/1 integration owner: accepted stack, Runtime/build contract, package, supported OS baseline and clean-checkout build. |
| LF-SEC-002 | **Blocker** | No production launcher self-updater or trusted root bootstrap | PR #15 is a design proposal only. No TUF client, pinned Root in a signed package, durable role state, target-to-product binding, update helper or rollback implementation is integrated. | Architecture/security owner: approved TUF library and bootstrap format, key-custody plan, conformance tests, clean Windows update and recovery proof. |
| LF-SEC-003 | **Blocker** | No clean-machine install/upgrade/uninstall/recovery evidence | The release workflow describes a test plan, but no approved installer or portable package exists to run it against. | Packaging owner: standard-user VM matrix, interrupted install/upgrade, repair/reinstall and uninstall/data-retention reports. |
| LF-SEC-004 | **High** | Game-delivery prototype is not a launcher updater or a production installer | Phase 4.1 prototype verifies a game manifest and bounded downloads to a temporary file. Its README/contract exclude extraction, install-root writes, transactional commit, persistent anti-rollback and Runtime lifecycle integration. | Phase 4 owner: accepted filesystem/path semantics, install-root containment/reparse-point tests, transaction and recovery evidence. Keep game and launcher update channels separate. |
| LF-SEC-005 | **High** | No integrated diagnostics or crash-reporting implementation | This PR adds a safe reference exporter and policy, but no Runtime/Studio logger or diagnostic export API consumes them. There is no proven end-to-end redaction at event creation. | Runtime/security owner: typed logger integration, secret/PII fixtures, sanitized support export, and opt-in crash-reporting verification. |
| LF-SEC-006 | **High** | Publisher signing inventory is not cryptographic signature verification | PR #14's validator checks metadata, path, file size and digest. A \`signed\` value remains a publisher assertion; the tool does not perform Authenticode chain/publisher/timestamp verification or provenance attestation. | Release engineering owner: independently verify Authenticode identity/timestamp and provenance in the publishing pipeline; bind the verification evidence to the exact uploaded bytes. |
| LF-SEC-007 | **Medium** | Stable release signing-status exemption and malformed JSON failure path found in PR #14 review | Automated review identified that \`not-applicable\` could pass for stable artifacts and an extreme malformed JSON number could escape the validator's expected error path. Fixes and regression tests were committed to the Phase 5.1 branch; they still require tests on that exact branch and reviewer re-check before acceptance. | Phase 5.1 owner: rerun all inventory tests and ask for review of the new head; retain the stable-only-signed schema rule. |
| LF-SEC-008 | **High** | Phase 5.2 trust/recovery contract remains unapproved | TUF v1.0.37 is proposed in PR #15, but key thresholds/custodians, root bootstrap, per-channel repository identity, local-admin rollback boundary, active-slot model and health-check API are unresolved. | Integration/security owner: approve those decisions and freeze interfaces before implementation. |

No finding is marked accepted or production-ready. The reference diagnostics utility does not close LF-SEC-005.

## 3. Review of current prototype boundaries

### Publisher release validator (PR #14)

Positive controls present in the proposed branch include exact-field validation, duplicate JSON-key rejection, SemVer/channel checks, restrictive relative paths, Windows path checks, symlink/reparse-point checks as observed by the process, and byte length/SHA-256 recomputation.

Limitations remain: the digest does not authenticate publisher identity; Authenticode/provenance checks are separate; the validator assumes an isolated release workspace and does not provide a race-free snapshot binding to subsequent publication; and the package type/real Windows installer lifecycle are not integrated.

The automated review's stable \`not-applicable\` signing exemption and malformed numeric input issue have been patched in the PR #14 branch with additional tests. Because those changes are still unreviewed in this assessment, treat them as **pending verification**, not resolved release evidence.

### Game delivery (PR #12)

The 4.1 prototype provides a proposed Ed25519-signed game manifest and bounded HTTPS downloads. Its own contract says a caller-provided temporary directory must already be private and that it validates path names rather than writing to an install root. It excludes installation, extraction, repair, persistent downgrade protection and rollback. Do not reuse its game manifest as launcher update metadata.

### Studio/layout (PR #9, #10, #13)

PR #9 and PR #10 are readiness/specification documents, not an implemented Studio/Runtime. PR #13 is an isolated Python layout reference with unit tests, not the exported renderer or an OS privilege boundary. These artifacts cannot establish import safety, project secret scanning, process-launch safety, credential handling or runtime log redaction.

## 4. Release-blocking security requirements

Before production release, provide evidence for every item:

- Approved supported Windows baseline, per-user install model and privilege boundary.
- Reproducible build inputs, dependency lock/inventory, SBOM, vulnerability and license review, provenance and retained build artifacts.
- Publisher identity and Authenticode signature/timestamp verification on exact release assets.
- Secret scanning of resolved build inputs and final package, failing closed without printing secret values.
- Approved Runtime permissions, process-launch policy, HTTPS/TLS/redirect/size limits and project/import path protections.
- TUF-conformant launcher updater with out-of-band Root bootstrap, rotation/revocation, expiry, replay/rollback and target binding.
- Staged apply, durable recovery journal, health check and last-known-good rollback on clean supported Windows VMs.
- Diagnostics redaction tests at logging and export boundaries; crash reporting disabled unless individually opted into.
- Migration compatibility, support boundaries, documented recovery and incident response.
- All high/blocker findings fixed or given an explicit named owner, rationale and expiry/mitigation approved by the release authority.

## 5. Current gate decision

**FAIL / NO-GO.** Do not distribute a production launcher package, enable self-updates, or claim Phase 5 complete based on these proposals.

This result is not a judgment that the architecture is inherently unsafe. It means the integrated system and required evidence do not yet exist. Re-run this review after Phases 0–4 and the accepted 5.1/5.2 implementations are integrated. A new review must include code-level tests, dependency review, Windows clean-machine and interruption testing, and a verified sanitized diagnostics export.
