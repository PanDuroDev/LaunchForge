# Launcher updater trust and recovery design proposal (Phase 5.2)

> **Status: DESIGN PROPOSAL — NOT AN APPROVED CONTRACT OR PRODUCTION UPDATER.**
>
> This proposal is a parallel architecture/research handoff. It does not enable self-updates, define a frozen Runtime API, or claim that Phase 5.1 has passed review. Adopt it only after the integration owner reviews the trust format and the 5.1 package/recovery boundary.

## 1. Decision summary

Use **The Update Framework (TUF), specification v1.0.36**, as the protocol baseline for launcher application update metadata. Prefer a maintained, specification-conformant implementation in the language selected by Phase 0 over a custom signature envelope or a hand-written partial TUF client.

TUF defines four required top-level metadata roles — Root, Targets, Snapshot and Timestamp — plus optional delegated Targets roles. Different roles use different keys and responsibilities; metadata has version and expiry; Targets binds artifact hashes and sizes; Snapshot binds the metadata set; Timestamp helps detect stale repository views. See the official [TUF specification](https://theupdateframework.github.io/specification/v1.0.36/) and [roles overview](https://theupdateframework.org/docs/metadata/).

TUF secures acquisition and verification of target bytes. It does **not** choose a package format, bootstrap trust for an arbitrary first install, apply the update, or guarantee application recovery. LaunchForge must provide those application-specific layers separately.

### Decisions proposed for architecture-owner approval

1. Adopt TUF v1.0.36 semantics and a conformant library; do not create a LaunchForge-specific signature format.
2. Give each launcher product and release channel a separately provisioned repository identity/trusted root. Channel changes require explicit publisher/user policy and are never an implicit fallback.
3. Bootstrap the initial TUF root out-of-band in the publisher-authenticated installer/package. The manifest/repository must never be allowed to introduce its own first trust anchor.
4. Keep Root, Targets and Snapshot signing keys offline and protected; use a separate narrowly scoped online Timestamp key. Select threshold sizes only after the publisher's key custody/availability model is known.
5. Treat update installation as a separate transactional subsystem that stages a verified payload and keeps the prior version usable until a health-checked commit is complete.
6. Do not enable automatic or silent self-update by default. Publisher opt-in and the product's user-consent/update policy must be explicit.

These are proposals, not frozen interface choices.

## 2. Scope and distinct trust domains

The updater distributes **launcher application/runtime packages** only. It must not consume the Phase 4 game distribution manifest or share the game update lifecycle. The Phase 4.1 manifest prototype explicitly has no durable anti-rollback state, root rotation, or install transaction and describes game file delivery; it is not a substitute for the launcher repository trust model.

The publisher artifact inventory in Phase 5.1 is publisher-side release QA metadata only. It is not downloaded by the launcher and is not an updater manifest.

Separate identities and state by at least:

- publisher / launcher product identifier;
- repository trust-root identity;
- release channel (stable, beta, preview);
- platform and architecture;
- installed product identity and compatible Runtime/package generation.

A URL, channel name, project file or remote manifest field must never be allowed to change the client's pinned repository identity or trusted root. A launcher must not silently fall back to another channel or product when an update source is unavailable.

## 3. Trust bootstrap and key roles

### Initial installation

TUF assumes the client begins with a trusted copy of Root metadata provisioned out-of-band. For LaunchForge, the candidate bootstrap is:

1. The publisher builds the launcher package with its initial TUF Root metadata/trust-root identity embedded as public data.
2. The package itself is signed through the publisher's Windows code-signing process and distributed through a publisher-controlled channel.
3. The install/bootstrap path verifies the package's expected publisher identity using the separately trusted installation path (for example, Windows Authenticode policy plus the publisher identity shown to the user).
4. Only then is the embedded TUF Root accepted as the initial update trust anchor.

A TUF repository cannot authenticate the initial installer that contains its own trust anchor. A fresh install must not download an untrusted root and then use that downloaded root to validate itself. If a publisher cannot provide an independently authenticated installation/bootstrap path, production self-update remains disabled.

The exact embedded root representation, Authenticode subject/publisher identity policy, installer interaction, and supported per-user install layout require approval with the Phase 0/1 package contract.

### Roles and custody

| TUF role | Proposed responsibility | Key custody proposal |
|---|---|---|
| Root | Defines trusted role keys, thresholds, algorithms and repository policy; authorizes role-key rotation | Offline, hardware-backed or otherwise strongly protected; multiple custodians |
| Targets | Authorizes exact launcher targets: filename, length, digest and application-specific product/channel/platform/version/compatibility data | Offline; separate from CI and online repository hosting |
| Snapshot | Binds a mutually consistent set of Targets/delegated metadata versions and hashes | Offline; separate from Timestamp |
| Timestamp | Short-lived freshness statement binding the latest Snapshot | Online automation with least privilege, isolated from target bytes and Root/Targets/Snapshot keys |

Root, Targets and Snapshot must not share one long-lived online private key. A compromised Timestamp key must not be sufficient to authorize arbitrary application bytes. Thresholds (for example, 2-of-3) are publisher policy and must not be copied as arbitrary constants without an operational custody plan.

### Rotation and revocation

- Root rotation must follow TUF's sequential root update procedure. A candidate root version N+1 must satisfy the previous trusted root's threshold **and** the new root's threshold; it must be exactly the next root version. Do not jump versions or trust an unbroken download from the current repository.
- Role-key changes are authorized by Root metadata. Targets delegations can be replaced/revoked by their trusted parent role.
- Timestamp rotation is not a substitute for Root rotation. Keep cached trusted metadata and persisted role versions consistent with the TUF implementation's documented rotation behavior.
- Compromise of a sub-threshold offline signer must not permit signing. If Root threshold is compromised, treat the repository as untrusted: stop updates and recover through a newly authenticated installer/out-of-band trust reset. Do not let the compromised root authorize its own replacement.
- Revoke/reissue affected publisher code-signing certificates through the certificate authority as appropriate, stop releases, assess the exposure interval, and communicate affected versions. Code-signing PKI and TUF repository keys are separate systems with separate lifecycles.

The TUF client workflow requires intermediate root metadata and previous/new root thresholds; see the [root update and rollback rules](https://github.com/theupdateframework/specification/blob/master/tuf-spec.md#update-root).

## 4. Metadata validation and anti-attack policy

A production client should use a TUF-conformant verifier and its exact parsing/canonicalization rules. Do not hand-roll canonical JSON, signature counting, key IDs, or role traversal.

Required behavior:

- **Signature authenticity:** verify the correct role's threshold of distinct trusted key IDs, using only algorithms and keys authorized by the trusted Root metadata. Duplicate signatures from one key do not satisfy multiple threshold slots.
- **Root continuity:** bootstrap from the package-provisioned root and process every consecutive root version. Each new root is signed by both the prior and new root thresholds.
- **Expiry/freeze resistance:** reject expired Timestamp, Snapshot and Targets metadata against the fixed update-cycle start time; never reset that time to extend validity during one cycle. Root follows TUF's special rotation workflow: the out-of-band trusted Root's expiry is ignored while attempting rotation, and expiry checks for intermediate Root versions are deferred until the consecutive-root walk finishes. Check the final trusted Root against the fixed update-cycle start time; abort and report a possible freeze if that final Root is expired. Timestamp expiry and publisher refresh cadence make repository freeze detectable.
- **Metadata rollback resistance:** persist trusted role metadata/version state. Reject lower versions; same-version metadata with changed content is not a valid update. Do not reset trusted versions just because the network source or channel changes.
- **Fast-forward recovery:** handle role-key rotation and repository compromise/recovery exactly as the chosen TUF implementation specifies; do not simply clear counters after verification failure.
- **Mix-and-match resistance:** verify Snapshot bindings to Targets metadata and all target metadata against the accepted Snapshot. Do not combine files from different repository states.
- **Artifact binding:** verify the downloaded target's exact length and cryptographic digest from trusted Targets metadata before the artifact is exposed to the installer. Keep the target filename independent of untrusted metadata until validated.
- **Product binding:** check exact product ID, release channel, Windows architecture, package type, minimum updater/bootstrapper version and Runtime compatibility before staging.
- **Network policy:** require HTTPS, platform certificate validation and bounded metadata/target sizes, deadlines and retry behavior. Prefer no redirects for metadata and target fetches; otherwise a future approved policy must revalidate every redirect destination against the pinned origin/allowlist and never forward credentials cross-origin.
- **Fail closed:** malformed metadata, unsupported algorithms/schema, unknown publisher/repository identity, invalid signatures, expired metadata, rollback, snapshot mismatch, invalid target path, excessive sizes or failed artifact verification abort the update. No unsigned or hash-only fallback is allowed.

A digest alone is not publisher authentication. TUF's role signatures authenticate target metadata and bind artifact hashes/sizes to a trusted role. TLS protects the transport but does not replace signed metadata.

The TUF specification's client workflow requires monotonically increasing metadata versions, expiry checks, threshold signature verification, and Targets/Snapshot hash binding. See the [pinned TUF v1.0.36 specification](https://theupdateframework.github.io/specification/v1.0.36/).

### Application-specific target metadata (POUF proposal)

TUF's Targets role signs the target metadata, including its opaque application-defined `custom` object. The framework does not interpret those custom fields; LaunchForge must define and validate them as its POUF before implementation. The proposed namespace is `custom.launchforge` with this minimum identity contract:

```json
{
  "schema_version": 1,
  "product_id": "com.example.launcher",
  "channel": "stable",
  "application_version": "1.2.3",
  "platform": "windows",
  "architecture": "x64",
  "package_type": "installer",
  "minimum_bootstrapper_version": "1.0.0",
  "runtime_compatibility": {
    "minimum": "1.0.0",
    "maximum_exclusive": "2.0.0"
  },
  "release_id": "com.example.launcher/stable/windows-x64/1.2.3"
}
```

This is an illustrative proposal, not a frozen schema. The approved POUF must define exact required/optional fields, SemVer and range semantics, supported enum values, unknown-field behavior, platform/architecture mapping, and migration rules. The client must validate this signed identity against the locally pinned installation before downloading or staging. It must additionally bind each accepted release identity to the exact TUF target path, length and digest; a `release_id` does not replace that byte-level binding. Do not trust identity fields from an unsigned sidecar, URL, filename, or game-delivery manifest.

The custom object and the TUF target's path/length/hash are both covered by the trusted Targets metadata. The client must use the selected TUF library's canonicalization and signature-verification implementation rather than parsing or re-signing these fields itself. See the [TUF v1.0.36 Targets format](https://theupdateframework.github.io/specification/v1.0.36/).

## 5. Version and channel policy

The launcher application version is distinct from game-content release versions and metadata role version counters.

- Use SemVer for publisher-facing launcher application releases.
- Use TUF integer versions for each metadata role; never reuse the application version as a metadata version.
- Store the installed launcher version and highest accepted release version for each (product, channel, platform, architecture) identity, together with the exact trusted Targets target identifier/path, length and SHA-256 digest for that accepted release.
- Reject any target whose product, channel, architecture, or compatibility identity does not match the locally pinned installation policy.
- Bind each accepted application version immutably to its exact target length and digest (and retain the target identifier/path for audit). If later, otherwise-valid Targets metadata reuses an already accepted product/channel/platform/architecture/version identity with a different length or digest, reject it; a higher Targets metadata version or fresh valid signatures do not authorize changing the bytes for an existing application release identity.
- Reject a target release lower than the currently installed release or the highest accepted release for that identity, even if its signatures and hashes are valid.
- Stable must not accept beta/preview by lexical comparison. Prerelease promotion is explicit publisher policy, not an implicit channel precedence.
- A channel migration or rollback recovery must require an explicit authenticated policy/action and must not clear metadata version state as a side effect.

Persist the accepted version-to-target binding atomically with the highest-accepted-version state, before allowing the release to become eligible for installation. Corrupt or missing binding state must fail closed and use the documented out-of-band re-bootstrap path; never reconstruct historical bindings from the current remote repository.

The local state model must acknowledge its threat boundary: local administrators or the same user controlling a per-user installation may be able to restore or replace local files. DPAPI/ACL protection helps protect state from other principals and accidental edits but does not create a hardware monotonic counter against the local owner. The threat model must state whether local-administrator rollback is in scope and whether TPM-backed anti-rollback is required/available. Do not overclaim protection from deleting/restoring local state.

## 6. Staged apply, commit and recovery

TUF verifies that a target is trusted. It does not install it. Runtime/installer ownership and Windows file locking must be resolved before coding this transaction.

Proposed application-level update lifecycle:

1. **Check:** obtain and verify TUF metadata; no active installation files change.
2. **Download:** write to a private, bounded temporary workspace. Do not execute or extract any unverified bytes.
3. **Verify:** confirm exact signed target length/hash and, where the target contains PE binaries, publisher Authenticode signature/identity. TUF target verification remains mandatory even when Authenticode succeeds.
4. **Stage:** assemble a new versioned slot beside the current installation (same volume where atomic rename semantics are needed). Enforce the approved install-root containment and Windows reparse-point policy.
5. **Prepare journal:** durably record the old active slot, candidate slot, metadata versions and transaction state before switching. Persist state using atomic replacement/flush semantics supplied by the platform abstraction.
6. **Commit:** a minimal trusted bootstrapper/helper switches the active version only after all validation is complete. Never overwrite the currently running executable in place. The helper must have a narrow, explicit permission boundary and must not accept arbitrary shell commands or caller-supplied install paths.
7. **Health check:** launch the candidate and require a bounded startup/health confirmation. The definition of healthy must be tied to the actual Runtime contract, not merely process creation.
8. **Finalize:** mark the candidate active, retain the previous known-good slot for the documented recovery window, and only then remove older staged data under the retention policy.

If power/process termination occurs during a transaction, the next bootstrapper run must consult the durable journal and select the last known-good slot. It must never infer that an incomplete candidate is valid merely because a directory exists.

**Candidate state transitions**

Idle → MetadataVerified → ArtifactVerified → Staged → CommitPending → CandidateActive → HealthConfirmed → Committed

Any pre-commit failure returns to Idle after safe cleanup. Any failure after CommitPending must recover deterministically to either the old known-good slot or a fully health-confirmed candidate. Recovery must be idempotent and safe when run repeatedly.

This is a proposed state model only. The active-slot representation, bootstrapper boundary, journal format, atomicity/flush guarantees, health-check API and retention rules require Phase 1 package/Runtime approval.

## 7. Failure policy

| Failure | Required behavior |
|---|---|
| Network unavailable / timeout / cancellation | Keep current application running; no active files or trusted metadata are partially committed |
| Missing, malformed, oversized or duplicate-key metadata | Abort; do not attempt weaker/unsigned fallback |
| Invalid signature / key ID / threshold | Abort; do not persist untrusted metadata or advance trusted version state |
| Expired timestamp / snapshot / targets | Abort and report stale/freeze condition; do not reset the fixed cycle start time |
| Lower metadata version / same version with changed bytes | Reject as rollback or metadata inconsistency |
| Wrong product/channel/platform/runtime compatibility | Reject before artifact download or staging |
| Cross-origin redirect / unapproved host | Reject; never forward credentials |
| Artifact length/hash mismatch | Delete temporary artifact; retain old version |
| Disk full / permissions / path escape / reparse point | Abort and clean staging safely; do not touch active slot |
| Process crash/power loss before commit | Recover old slot; remove or resume only according to a documented validated journal state |
| Crash during/after activation before health confirmation | Bootstrapper selects old slot and marks candidate failed |
| Health-check timeout or candidate startup failure | Roll back to old slot and report sanitized error |
| Old slot unavailable/corrupt | Enter explicit recovery mode; never mark unverified candidate healthy |

## 8. Durable state and diagnostics

Persist, per repository identity, the trusted Root and TUF role metadata/version state, the accepted repository identity, and the highest accepted launcher release version and immutable target binding for each product/channel/platform/architecture tuple. Persist update journal state separately from trusted metadata state.

State writes must be atomic and corruption-detecting. If state is missing, malformed, inconsistent, or cannot be authenticated, do not silently recreate it from remote metadata. Require a documented re-bootstrap/recovery route using the original trusted installer or another out-of-band approved channel. A reset is a security-sensitive action and must be auditable.

Diagnostics should emit stable error codes and safe context such as role name, metadata version, product ID, stage and recovery outcome. Never log private keys, access tokens, signatures containing sensitive metadata, raw request headers, user data, full local paths, or credential-bearing URLs. Diagnostic export must redact by default and be opt-in when it contains machine/environment data.

## 9. Security conformance and adversarial test plan

See [LAUNCHER_UPDATE_CONFORMANCE_MATRIX.md](LAUNCHER_UPDATE_CONFORMANCE_MATRIX.md). Before production enablement, run the full TUF implementation conformance suite appropriate to the selected library plus LaunchForge-specific package, Windows transaction, failure-injection and clean-machine tests.

## 10. Required integration decisions before implementation

| Decision / interface | Owner that must approve | Why it blocks production updater code |
|---|---|---|
| Runtime/build/package format, version/architecture fields, bundled bootstrapper layout | Phase 0/1 architecture and build owners | Target selection and staged replacement depend on real package structure |
| Windows baseline, per-user install root, ACL/reparse-point policy | Phase 0 filesystem/security owner | Determines safe storage, helper permissions and path checks |
| TUF library/language and supported algorithms/spec version | Phase 0 architecture owner | Avoids an unreviewed cryptographic/parser implementation |
| Targets custom metadata schema and POUF (product/channel/version/platform/architecture/package/runtime compatibility/release ID) | Phase 0/1 architecture and updater integration owners | Defines the signed application identity the client must validate before download/staging |
| Root bootstrap distribution and publisher identity validation | Security/integration owner | Defines initial trust and first-install authenticity |
| Role thresholds, custodians, HSM/key service and revocation response | Publisher/security owner | Threshold values must match real key operations and recovery |
| Product/channel identity and SemVer/metadata version state | Product/integration owner | Prevents cross-channel substitution and downgrade ambiguity |
| Persistent anti-rollback state and local-admin threat boundary | Security/Runtime owner | Defines what local state can and cannot protect |
| Active-slot transaction/journal and health-check interface | Runtime/package owner | Required for safe apply, restart and rollback |
| User consent and update opt-in policy | Product owner | Silent auto-update is explicitly out of scope without publisher opt-in |

Until these are approved, the updater must remain disabled. This proposal does not authorize code to fetch or install executable updates.
