# Production release gate checklist

**Current decision: NO-GO.** This checklist is the required evidence record for a release candidate. A checked code/documentation item is not a substitute for a passing executable test.

## Release identity

- [ ] Product ID, publisher identity, SemVer version and release channel are immutable and documented.
- [ ] Runtime, project schema, package format, platform/architecture and compatibility range are recorded.
- [ ] Launcher application release metadata is distinct from game-content manifests and versions.
- [ ] Stable releases cannot contain unsigned or signing-exempt launcher artifacts.
- [ ] Re-publishing different bytes under an existing immutable release identity is rejected.

## Build and supply chain

- [ ] Build starts from a clean, immutable source revision with pinned runner/toolchain/SDK/packaging dependencies.
- [ ] Dependency lockfiles and direct/transitive dependency inventory are retained.
- [ ] SPDX or CycloneDX SBOM is generated for the actual package contents and reviewed.
- [ ] Known vulnerabilities and licenses are reviewed; release-blocking findings are fixed or formally accepted.
- [ ] Resolved build inputs and final package are scanned for prohibited secrets; export/publish fails closed without exposing secret values.
- [ ] Provenance/attestation is generated and verified against the exact artifact source/build.
- [ ] A second clean build has been compared before claiming reproducibility.

## Publisher signing and publication

- [ ] Authenticode verification checks chain, publisher identity, code-signing EKU, timestamp and policy on each applicable PE binary/installer.
- [ ] Signing keys are held in controlled signing infrastructure; no private key enters source, project, package or logs.
- [ ] Final signed bytes are hashed; uploaded files are downloaded back and size/hash/signature rechecked.
- [ ] Assets are immutable and published through a publisher-controlled origin.
- [ ] Release channel promotion is explicit and cannot introduce a downgrade.

## Trusted launcher updater (only after explicit publisher opt-in)

- [ ] TUF implementation/spec version and algorithm policy are approved.
- [ ] Fresh-install Root is provisioned through an independently authenticated package/bootstrap path.
- [ ] Root, Targets, Snapshot and Timestamp keys/thresholds have separate custody, rotation and incident procedures.
- [ ] Expired, invalid, replayed, rollback, mix-and-match, wrong-product, wrong-channel and wrong-platform metadata is rejected.
- [ ] Artifact length and digest are verified before staging; no hash-only or unsigned fallback exists.
- [ ] Trusted metadata/version state is durably persisted and corruption does not silently reset trust.
- [ ] Staged apply never overwrites the running executable in place.
- [ ] Interrupted apply, disk-full, permission failure, process crash and failed health-check preserve or restore a known-good version.
- [ ] Update behavior is opt-in according to publisher/product policy; no silent update default.

## Windows installation and recovery

- [ ] Clean supported Windows VM install succeeds as a standard user.
- [ ] Upgrade from every supported prior package version preserves approved user data.
- [ ] Cancellation/interruption at every installer/update transaction boundary is tested.
- [ ] Uninstall removes application files and preserves user data according to explicit choices.
- [ ] Repair/reinstall and old-version recovery are tested.
- [ ] No undeclared framework/runtime dependency is assumed.
- [ ] Windows reparse points, junctions, symlinks, locked files, ACLs and path containment receive adversarial tests.
- [ ] VM image, OS build, architecture, privilege level and raw test result are retained.

## Diagnostics, privacy and support

- [ ] Runtime and Studio emit only typed, documented, allow-listed diagnostic fields.
- [ ] Unknown/free-form fields, stack traces, URLs, paths, environment variables, tokens, PII and project/game payloads are excluded from exports.
- [ ] Tests prove secret and personal-data exclusion at both event creation and export.
- [ ] Standard crash reporting is disabled by default; any future submission is individually opt-in with payload preview.
- [ ] Diagnostic retention, deletion, destination and support handling are documented before an endpoint is operated.
- [ ] Support matrix names the OS/package/runtime versions actually tested.
- [ ] Migration notes list supported old schema/runtime versions, explicit migrations, backup/rollback and unsupported versions.
- [ ] No silent project rewrite or loss of unknown legacy fields occurs.
- [ ] Support boundaries and escalation/recovery instructions are published.

## Security sign-off

- [ ] All Blocker/High findings from the latest security review are closed.
- [ ] Any residual accepted finding has a named accountable owner, rationale, mitigation, expiry/review date and release-authority approval.
- [ ] Security incident/key compromise response has been rehearsed.
- [ ] CI and manual clean-machine evidence are linked to this exact immutable release candidate.
- [ ] A reviewer independent of the implementation owner has approved the complete release evidence.

## Status record

At the current repository baseline, the following are **not demonstrated**: integrated Runtime/package, supported Windows baseline, real installer, clean-machine install/upgrade/uninstall, updater, key bootstrap/rotation, transactional rollback, Runtime diagnostics integration, full SBOM/provenance, and whole-product penetration/security review.

Therefore the production release gate remains **NO-GO** until the above evidence is attached and approved.
