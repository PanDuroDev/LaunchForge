# Phase 4 delivery threat model (prototype)

## Protected assets

Publisher identity and trusted public keys; signed release metadata; downloaded game bytes; the current working installation; user-selected install root; process-launch configuration; user data stored separately from program files.

## Trust boundaries

1. Publisher release service / CDN to launcher: all manifest and file bytes are untrusted until manifest signature and per-file hashes verify.
2. Download temp area to transaction engine: caller-supplied paths are untrusted; source files are reopened without symlink following and rehashed while copying.
3. Transaction engine to filesystem: install parent, path hierarchy, reparse points, directory entries and transaction journal are security-sensitive.
4. Runtime to OS process manager: executable identity, arguments, working directory and process lifetime require an approved native adapter.

## Threats and prototype mitigations

| Threat | Prototype control | Residual blocker |
|---|---|---|
| Forged or substituted manifest | Ed25519 signature with out-of-band trust key in 4.1 | Bootstrap, rotation, revocation and durable anti-rollback policy |
| Artifact corruption / CDN substitution | Signed size + SHA-256; rehash during staging and after commit | Production key lifecycle, CDN integration and Windows validation |
| Path traversal / Windows device/ADS names | Strict cross-platform relative path validation | Must share one approved filesystem path policy |
| Symlink/junction/reparse-point escape | 4.2 POSIX O_NOFOLLOW + dirfd walk; Windows fails closed | Production Win32 handle-relative backend is mandatory |
| Concurrent install/update | Per-install flock lock and recovery before new operation | Windows cross-process lock implementation and deadlock UX |
| Interrupted update | Durable sibling journal, same-parent rename, old backup kept until verified | Power-loss testing on supported Windows filesystems |
| Disk exhaustion | Release byte quota, free-space reserve, write errors abort staging | Quota accounting across concurrent games/downloads and Windows storage semantics |
| Malicious extra file/DLL planted in install tree | Exact manifest-tree verification rejects extras/symlinks/special files | Runtime must defend launch-time races and DLL search behavior |
| Unlisted executable launch | Lifecycle layer only permits manifest-declared executable | Native process API must re-open/verify by handle immediately before launch |
| Malicious local user modifying same-user files | Parent ownership/private-mode checks; no-follow operations | Same-user malware is outside this prototype's isolation boundary; ACL policy needed |

## Assumptions

The publisher signing key is provisioned out-of-band; the install parent is selected by the user and owned by that user; install directories contain immutable program files only; save/configuration data is stored separately; downloaded artifacts are individual files rather than archive extraction payloads.

## Release-blocking findings

- The transaction implementation is a POSIX prototype, not a supported Windows reparse-point-safe implementation.
- No native Runtime process adapter is implemented; tests use a fake adapter.
- Phase 0 filesystem/security and Phase 1 Runtime/build contracts are not on main at the time of this handoff.
- No production tests have been run on Windows, NTFS, Defender/antivirus, real CDN or a real publisher trust store.

Do not distribute Phase 4 managed installs until these blockers are resolved and the complete adversarial suite passes on the supported Windows baseline.
