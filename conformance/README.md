# Phase 6 conformance catalog

The machine-readable inventory is `phase6-catalog.json`. It contains 36 planned conformance cases grouped under project-format, migration, capability, parity, security, packaging, performance, and operations.

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

The `.github/workflows/phase6-catalog.yml` workflow runs the same validator, unit test suite, and compile check on relevant pull requests and pushes. A successful run confirms catalog/harness metadata only; it does not mark any of the 36 product conformance cases as executed.
