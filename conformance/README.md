# Phase 6 conformance catalog

The machine-readable inventory is `phase6-catalog.json`. It contains 40 planned conformance cases grouped under project-format, migration, capability, parity, security, packaging, performance, and operations.

## Validate the catalog

From the repository root, using only the Python standard library:

```sh
python tools/validate_conformance_catalog.py
python -m unittest discover -s tests -p "test_phase6_catalog.py" -v
```

The validator checks catalog structure, stable ID syntax and uniqueness, category/prefix consistency, product-surface values, dependency/evidence presence, exact field sets, dependency-label grammar, and references against the canonical `dependency_registry`. Keep each prerequisite area under one registry ID; case entries must reference registered IDs only.

**Important:** These commands validate the test catalog only. They do not execute LaunchForge behavior, migration, renderer, Runtime, packaging, or security conformance. All entries currently have `lifecycle: planned`. Do not change a case to `implemented` until its executable adapter and passing evidence exist.

## Contract dependencies

Each `contract_dependencies` value is a planning label for a prerequisite area (for example `phase1:renderer-contract`). It is not an approved schema identifier, public API name, or claim that the contract exists. Replace or map these labels only after the relevant Phase 0–5 contracts are reviewed and accepted.

The catalog is intentionally renderer/runtime neutral and must not be used to infer support for an OS, Studio, or exported Launcher target.

## Continuous validation

The `.github/workflows/phase6-catalog.yml` workflow runs the same validator, unit test suite, and compile check on relevant pull requests and pushes. A successful run confirms catalog/harness metadata only; it does not mark any of the 40 product conformance cases as executed.

## Newly tracked contract-consistency edges

The catalog includes planned cases for UUID policy agreement between schema and semantic validation (`LF-COMPAT-007`) and application-icon reference/ICO payload validation through export (`LF-COMPAT-008`). They intentionally do not choose an uppercase/lowercase UUID rule or redefine the application-icon contract; those decisions remain owned by Phase 0/1. Both cases remain `planned` until the upstream contract is approved and executable fixtures are integrated.

## Phase 3.1 data and network cases

The inventory includes planned typed-mapping conformance (`LF-CAP-006`) for JSON Pointer parsing, declared field types, optional/default handling and safe transformations. It also includes `LF-SEC-006` for host-enforced DNS/IP egress controls; HTTPS and same-origin redirects alone are not a private-address or DNS-rebinding defense. Both remain planned until Phase 0/1/3 owners approve the respective contracts and integrate them with Studio and exported Runtime.

## Portable Windows package verification

The inventory includes `LF-PKG-006`, a planned preflight requirement for a portable Windows ZIP verifier. The candidate verifier in [PR #23](https://github.com/PanDuroDev/LaunchForge/pull/23) passed five Windows hosted fixture cases in [run #41924660818](https://github.com/PanDuroDev/LaunchForge/actions/runs/41924660818), covering a valid package and hostile/malformed archives. This is CI fixture evidence, not a fresh-user clean-VM acceptance result. The catalog case remains `planned` until the verifier and package contract are accepted and the manual clean-machine gate passes.
