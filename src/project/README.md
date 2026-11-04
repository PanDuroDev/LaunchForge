# LaunchForge Project Foundation (Phase 1.1)

This crate implements the P1-A project persistence boundary against the Phase 0 project-v1 candidate.

## Scope

- Create an empty, valid project v1 starter with UUIDv4 identities.
- Parse UTF-8 JSON and enforce the 1 MiB project-document limit.
- Validate JSON Schema Draft 2020-12 using the repository-owned schema file at `poc/contracts/project-v1.schema.json`.
- Enforce semantic invariants that need cross-entity inspection: canonical lowercase UUIDv4 IDs, typed application-icon references, asset/game references, root container, component count/depth, window minimums, portable asset filename rules, and duplicate asset paths.
- Open project files with validation.
- Save validated projects through a same-directory temporary file and an atomic replacement operation.
- Return optional metadata from document accessors so untrusted in-memory mutations cannot turn simple reads into panics.
- Reject a project file that is itself a symbolic link.

## Single source of truth

The crate embeds the existing Phase 0 schema using `include_str!`; it does not copy the schema into Rust source or create a second JSON Schema definition. JSON Schema validation is performed in-process with remote-reference features disabled. Cross-field rules are implemented separately because JSON Schema alone cannot express all v1 project relationships.

The schema and Phase 0 semantic validator remain candidates until PR #16 receives integration-owner approval. Any accepted Phase 0 changes must be consumed here rather than creating a parallel schema.

## Commands

From the repository root:

```powershell
cargo test --manifest-path .\src\project\Cargo.toml
```

Run the focused integration test:

```powershell
cargo test --manifest-path .\src\project\Cargo.toml --test project_store
```

## Boundaries and limitations

- Asset paths are validated lexically only. This crate does not resolve/read assets. The privileged host must canonicalize paths immediately before access and reject symlink, junction, and reparse-point escapes.
- Game executable configuration, first-run trust/approval, and process launch are not implemented here.
- Project schema migration is not implemented. Non-v1 integer versions return an explicit `UNSUPPORTED_SCHEMA_VERSION` diagnostic stating that no automatic migration is available; schema migrations require a separately accepted compatibility contract.
- The crate consumes `window.iconAssetId` and validates that it resolves to a typed `applicationIcon` asset with a lowercase `.ico` filename. It does not inspect ICO binary layers or stage/embed icon bytes; that belongs to the build/export package. The project bootstrap layer must materialize the default `assets/launcher-icon.ico` referenced by `create()`.
- The Windows atomic replacement path uses MoveFileExW with replace-existing and write-through flags; Windows CI execution is still required to validate it.
- The repository's integration owner must wire this crate into the accepted Studio/Runtime workspace and CI after Phase 0 approval.

## Validation status

The current execution environment has no Rust toolchain, so `cargo test` has not been run locally. Do not mark the P1-A gate passed until the crate compiles and its integration tests pass on the Windows CI/toolchain selected by Phase 0.
