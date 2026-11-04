# Publisher release workflow (Phase 5.1)

**Status:** Proposal and publisher-side prototype; not an approved Runtime, installer, or updater contract.

This Windows-first release procedure defines publisher-side checks without selecting MSI versus EXE, an installer framework, a build system, or an update backend. Those choices must consume the accepted Phase 0/1 package interfaces rather than invent parallel ones.

## Trust boundary

`publisher-artifacts.v1.json` is a **publisher-side artifact inventory** used by the release job to validate local files before publishing them. It is not downloaded by launcher clients, is not a signed update manifest, and must never authorize a client update.

A SHA-256 digest detects byte mismatch only when the expected digest is already trusted. An attacker who can replace both artifact and digest can produce a matching pair. Release authenticity depends on publisher signing and provenance. The Phase 5.2 updater must define its own approved signed metadata, client trust anchor, artifact binding, freshness/replay policy, monotonic version policy, and key lifecycle. None of those properties is implied by this inventory.

Launcher application releases and game-content releases are separate products and channels. Do not reuse game manifests as launcher update metadata.

## Versioning and channels

Use Semantic Versioning (`MAJOR.MINOR.PATCH`) and immutable release identities. Never replace an already-published artifact under the same product/version/channel identity.

- `stable`: SemVer without a prerelease suffix; unsigned artifacts are forbidden.
- `beta`: SemVer prerelease, for example `2.1.0-beta.2`.
- `preview`: SemVer prerelease, for example `2.1.0-preview.4`.

Channels are publisher labels, not security boundaries. A client must not switch channels or accept a downgrade based only on the channel name. Stable promotion must be explicit, preserve the exact tested bytes, and compare against the highest previously published stable version. The inventory validator does not query release history or enforce monotonic promotion.

## Inventory and validator

The machine-readable contract is in [publisher-artifact-inventory-v1.schema.json](../schemas/publisher-artifact-inventory-v1.schema.json). The executable validator additionally rejects duplicate JSON keys, unsafe relative paths, traversal, Windows alternate-stream syntax, symlinks/reparse points, incorrect sizes, and SHA-256 mismatches.

It records product/version/channel, source revision, CI workflow/run, toolchain and UTC build time, plus each artifact's relative path, target, package type, size, digest and explicit signing status.

The validator uses only the Python standard library:

```powershell
python tools/release/validate_inventory.py .\dist
```

Unsigned local preview builds require an explicit override:

```powershell
python tools/release/validate_inventory.py .\dist --allow-unsigned
```

The override is rejected for stable releases and must never appear in a production publishing job. Both `unsigned` and `not-applicable` signing states are rejected for stable artifacts; a Windows launcher installer must have a signed and timestamped publisher identity on every channel. The `not-applicable` status is reserved for package types that genuinely contain no executable installer payload (for example, an unsigned portable archive). A stable inventory is not allowed to encode a signing exemption, and passing `--allow-unsigned` on a stable inventory is rejected even when every artifact is already signed. The validator checks structure, paths, lengths and hashes. It does **not** verify Authenticode signatures, certificate chains, GitHub attestations, SBOMs or updater trust. A `signed` JSON value is an assertion, not cryptographic proof.

Run it in an isolated release workspace that the validator's process exclusively controls. The filesystem checks reject links/reparse points observed during validation; this local QA tool is not a defense against a concurrent process that can mutate the release directory while it is being checked.

## Required release sequence

1. **Controlled build:** use a clean checkout at an immutable commit. Pin the Windows runner image, SDKs, compiler/linker and packaging-tool versions, and dependency lockfiles. Use least-privilege CI permissions; do not expose signing credentials to pull-request builds.
2. **Dependency inventory:** generate an SPDX or CycloneDX SBOM for the actual release output. Inventory direct and transitive dependencies, review licenses, scan known vulnerabilities, and retain the SBOM. Critical/high findings block release unless a named owner records explicit, time-bounded acceptance.
3. **Build and test:** build the selected package deterministically where practical. Run tests, inspect package contents, scan resolved inputs and final output for secrets, and confirm publisher credentials are absent. Do not claim reproducibility until independent clean builds have been compared and differences explained.
4. **Sign before hashing:** sign Windows executables/installers using a publisher-controlled certificate in a managed signing service or hardware-backed key store. Never store private signing keys in source control, project files, launcher packages, plain CI variables or diagnostics. Apply a trusted timestamp. Verify final signatures and publisher identity on the release runner (for example, `signtool verify /pa /all /v <file>` plus an explicit certificate allowlist). Runnable binaries inside an unsigned archive still require signature checks.
5. **Create final inventory:** after signing, compute SHA-256 and exact byte length for the bytes that will be uploaded. Write `publisher-artifacts.v1.json` with immutable source/build metadata and explicit signing status.
6. **Validate and attest:** run the inventory validator, signature checks, SBOM checks and repository provenance/attestation workflow. Retain sanitized evidence. The inventory's signing assertion does not replace cryptographic verification.
7. **Publish immutable assets:** publish under a versioned tag/release. Never overwrite assets in place. Record signer identity and signing status; never publish secrets, key material or raw environment variables.
8. **Verify after upload:** download every published asset in a clean job, compare size and SHA-256, and re-verify signatures and attestations. Stop promotion and quarantine/revoke a release if any check fails.
9. **Promote deliberately:** promote to stable only after clean-machine install/upgrade/uninstall/recovery tests pass on the approved Windows baseline. Promotion must not replace bytes or lower the stable version.

## Signing and key operations

The publisher owns its code-signing identity and key protection. Signing must be auditable and restricted to the release pipeline. Rotate certificates with an overlap period and record the signer used for each release. On suspected compromise, stop releases, revoke the affected certificate where supported, investigate the exposure window, and communicate a recovery release. Windows Authenticode identity is separate from the Phase 5.2 updater-signing trust system.

A code-signing certificate improves publisher identity and Windows trust signals; it does not make code safe and does not replace provenance or updater metadata signatures.

## Clean-machine acceptance checklist

This checklist is executable only after Phase 1 defines the package format and supported Windows baseline. Record OS build, architecture, VM image, privilege level and results.

- [ ] Install a downloaded artifact on a clean supported Windows image with no Studio or developer toolchain installed.
- [ ] Confirm dependencies are bundled or installed through the documented path; no undeclared dependency is assumed.
- [ ] Confirm product/publisher metadata, icon, version, install scope and location.
- [ ] Launch as a standard user without unnecessary elevation.
- [ ] Upgrade from the prior supported release while preserving user/project data and configuration.
- [ ] Interrupt install/upgrade and verify the documented recovery path.
- [ ] Uninstall without deleting user data unless explicitly requested.
- [ ] Reinstall and verify a clean launch.
- [ ] Check bundled dependencies against the SBOM and package inspection report.
- [ ] Verify signatures, publisher identity, timestamps, uploaded hashes and provenance.

Do not mark this checklist passed using only a developer workstation or build-only CI job. At least one clean Windows VM run is required for each supported package/install mode.

## Retained release evidence

Retain immutable source revision, workflow/run ID, pinned toolchain description, build/test logs, inventory, exact published assets, SBOM, signature verification, provenance/attestation, clean-machine report and release notes. Sanitize evidence; never include secrets, access tokens, signing keys, user data or private paths.

## Implementation boundary and handoff

Implemented in this branch: inventory v1 schema; a standard-library validator; and adversarial metadata/path/hash tests.

Still dependent on approved interfaces or Windows infrastructure: actual installer/portable format and toolchain, app identity/install scope, integration with the real build/export pipeline, SBOM/provenance generation, clean Windows install/upgrade/uninstall/recovery tests, and Authenticode signing/verification.

Phase 5.2 signed updater metadata/trust/recovery and Phase 5.3 whole-product security/diagnostics review are not implemented or claimed complete. This prototype is isolated from Runtime and game-update interfaces; architecture-owner approval is required before integration.
