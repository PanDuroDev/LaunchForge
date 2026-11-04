# Launcher updater conformance and failure-injection matrix (Phase 5.2 proposal)

> **Status: PROPOSED TEST PLAN.** No production updater code or package transaction exists in the repository yet. This matrix is a required acceptance suite for the implementation selected after architecture approval.

## Metadata, signature and trust tests

| ID | Scenario | Expected result |
|---|---|---|
| TUF-001 | Valid metadata chain and correctly signed target | Accept target only after all role and target checks pass |
| TUF-002 | Missing signature, unknown key ID, unsupported algorithm | Reject; no target exposed |
| TUF-003 | Invalid signature or one bit altered in signed metadata | Reject; no trusted state advanced |
| TUF-004 | Duplicate signature entries from same key ID | Count that key at most once toward role threshold |
| TUF-005 | Threshold not reached | Reject role metadata |
| TUF-006 | Target signed only by a key supplied in untrusted metadata | Reject; untrusted metadata cannot add a trust anchor |
| TUF-007 | Root version jumps from N to N+2 | Reject; fetch/verify consecutive N+1 chain only |
| TUF-008 | Root N+1 signed by old threshold but not new threshold | Reject |
| TUF-009 | Root N+1 signed by new threshold but not old threshold | Reject |
| TUF-010 | Expired root/targets/snapshot/timestamp at fixed update start time | Reject; report expiry/freeze condition |
| TUF-011 | Timestamp version lower than trusted | Reject rollback |
| TUF-012 | Timestamp version equal but content differs | Reject inconsistency; unchanged version is not permission for changed bytes |
| TUF-013 | Snapshot points to changed/missing/wrong-version Targets metadata | Reject mix-and-match |
| TUF-014 | Targets length/hash differs from downloaded target bytes | Reject and delete temporary target |
| TUF-015 | Expired metadata replayed by stale mirror | Reject |
| TUF-016 | Repository withholds updates while returning stale timestamp | Expiry policy reports possible freeze; retain installed app |
| TUF-017 | TUF root changes timestamp/snapshot signer | Follow conformant key-rotation and cached-state reset behavior; no ad-hoc reset |
| TUF-018 | Multiple product/channel repositories share URLs but have distinct pinned roots | Never cross-accept metadata between repository identities |

## Release identity, channel and downgrade tests

| ID | Scenario | Expected result |
|---|---|---|
| REL-001 | Target product ID differs from installed launcher | Reject before download/staging |
| REL-002 | Target channel differs from explicitly pinned channel | Reject unless separate explicit migration policy is authorized |
| REL-003 | Target architecture/platform differs | Reject |
| REL-004 | Target requires a newer incompatible Runtime/bootstrapper | Reject with actionable compatibility error |
| REL-005 | Target application version is below installed version | Reject even if TUF signature/hash are valid |
| REL-006 | Target application version is below persisted highest accepted release | Reject |
| REL-007 | Beta/preview is offered to a stable installation | Do not silently switch channels |
| REL-008 | A previous stable release is republished under the same immutable identity with different bytes | Publishing gate rejects; client metadata version/content checks reject inconsistency |

## Source and resource-bound tests

| ID | Scenario | Expected result |
|---|---|---|
| NET-001 | Cleartext HTTP, invalid TLS certificate, or unknown repository origin | Reject |
| NET-002 | Redirect to another origin or unapproved host | Reject; no credentials forwarded |
| NET-003 | Oversized metadata body or target exceeding signed length/configured cap | Abort and clean temporary bytes |
| NET-004 | Content-Length mismatch, truncation, or unexpected content encoding | Abort |
| NET-005 | Timeout, cancellation, connection reset, or exhausted bounded retries | Preserve active version; cleanup partial data |
| NET-006 | Disk quota/storage limit reached | Abort before active-slot mutation |
| NET-007 | Filename/path contains traversal, drive, UNC, ADS, reserved device name, collision or reparse point | Reject before write |
| NET-008 | Same target URL returns different bytes after metadata acceptance | Target digest fails; do not stage |

## Transaction, interruption and recovery tests (Windows required)

Run with a clean supported Windows VM image and standard-user privileges. Inject a process termination and a power-loss-equivalent restart at every durable state transition.

| ID | Interruption point | Expected restart result |
|---|---|---|
| TXN-001 | During metadata fetch/verification | Current version remains active; untrusted metadata is not persisted |
| TXN-002 | During artifact download | Current version remains active; partial temp file is removed or safely discarded |
| TXN-003 | After target verification, before staging | Current version remains active; verified temporary data is not assumed committed |
| TXN-004 | During staging | Current version remains active; incomplete candidate is quarantined/removed |
| TXN-005 | After staging, before journal prepare | Current version remains active |
| TXN-006 | During durable journal prepare | Recovery resolves to old active slot; partial journal is rejected safely |
| TXN-007 | After journal prepare, before active-slot switch | Recovery resolves to old known-good slot |
| TXN-008 | During active-slot switch | Bootstrapper selects exactly one complete known-good slot |
| TXN-009 | Candidate starts but health check fails/times out | Roll back to previous known-good version |
| TXN-010 | Crash after health check, before journal finalization | Recovery is idempotent; either confirms the candidate from durable proof or restores old slot |
| TXN-011 | Repeated crash during rollback/recovery | Re-running recovery does not damage either slot or lose the last known-good one |
| TXN-012 | Old slot missing/corrupt | Enter explicit recovery path; never trust an incomplete candidate by default |
| TXN-013 | User launches while update helper is active | Serialize or reject concurrent transactions; no mixed files |
| TXN-014 | Standard-user permissions and locked/running files | No unnecessary elevation; helper handles Windows file locks through documented restart/slot design |

## Key lifecycle and incident tests

| ID | Scenario | Expected result |
|---|---|---|
| KEY-001 | Planned Root rotation via consecutive roots | Client verifies old and new thresholds for each root hop |
| KEY-002 | Timestamp-key compromise | Rotate through trusted Root; compromised online key cannot authorize target bytes alone |
| KEY-003 | Sub-threshold offline key compromise | Threshold remains unmet; no arbitrary targets accepted |
| KEY-004 | Root threshold compromise | Stop updates; recovery uses authenticated out-of-band trust reset |
| KEY-005 | Code-signing certificate revoked/expired | Follow explicit publisher policy; fail publisher identity verification where required |
| KEY-006 | Trust state missing, corrupt or rolled back | Do not learn new trust from repository; invoke documented recovery |

## Security release-gate evidence

The production gate must attach:

- selected TUF implementation/library version and its conformance results;
- exact trusted root bootstrap process and key-custody records (never private keys);
- tests for signature threshold, root rotation, expiry, rollback, fast-forward and mix-and-match;
- metadata/target resource-limit tests and hostile repository/redirect fixtures;
- package identity, target-binding, Authenticode and provenance verification;
- Windows clean-machine install/upgrade/uninstall test report;
- transaction failure-injection results for each state transition;
- rollback and recovery reports after repeated process/power interruption;
- sanitized logs/diagnostics from each failure class;
- an explicit list of accepted residual risks with named owners.

A passing metadata verifier alone is not a passing updater. The phase exit gate requires trusted metadata, target verification, real package apply, rollback/recovery and clean supported Windows evidence.
