# Phase 3.1 handoff — network adapter and typed data model

## Implemented on this branch

- `packages/content-data/src/index.ts`: bounded HTTPS JSON GET adapter and typed data mapping/inspection primitives.
- `packages/content-data/test/content-data.test.mjs`: fixture-only tests for HTTPS/method validation, redirects, cancellation, timeouts, response byte caps, JSON MIME/UTF-8/shape validation, bounded retries (including credential preservation across a retry after a redirect), JSON Pointer mapping, safe transformations, and inspector output.
- `packages/content-data/package.json`, `tsconfig.json`: standalone TypeScript package configuration.
- `.github/workflows/phase3-content-data.yml`: Node 22 CI typecheck and test commands with read-only token permissions, disabled checkout credential persistence, and action dependencies pinned to immutable SHAs.

## Public prototype surface

- `fetchJson(request, fetchImpl?)`: HTTPS GET JSON with injected Fetch, default 10-second timeout, 1 MiB streamed body cap, three same-origin manual redirects, two bounded retries, no cookies/ambient credentials, no-store cache, and caller AbortSignal support.
- `validateHttpsEndpoint(url)`: URL scheme/credential/query-secret validation.
- `mapFields<T>(json, mappings)`: RFC 6901 JSON Pointer mapping, declared types, required/optional/default values, and safe transforms (`trim`, case conversion, `toNumber`, `toBoolean`, `toUrl`).
- `inspectResponse(json)`: bounded JSON path/type inventory suitable for a future field picker.

These are isolated prototype APIs, not approved project-schema or Runtime contracts.

## Exit-gate evidence

Run in this directory with Node.js 22 and TypeScript 5.8+:

```sh
npm install
npm run typecheck
npm test
```

The package's CI workflow runs the same typecheck and fixture suite on PRs. Do not substitute live-network smoke tests for deterministic fixtures. The 3.1 gate is limited to the network/binding contract; it does not claim an integrated launcher preview or exported Runtime.

## Contract dependencies and unresolved integration work

- Phase 0 network/security and Phase 1 Runtime/project contracts are mandatory for production use. Phase 0 candidate security/stack records are still reviewable proposals until accepted by the integration owner.
- The current `main` contains conformance and planning material but no Studio app, launcher Runtime, approved project/connection schema, egress policy implementation, or application data-binding harness.
- HTTPS and same-origin redirects do not provide DNS/IP egress protection. The eventual privileged host must reject loopback, link-local, private, reserved, and otherwise unauthorized destinations after resolution and on connection; the host needs a documented DNS rebinding policy.
- The current adapter deliberately supports only GET JSON. It does not implement POST, arbitrary methods, pagination, WebSockets, arbitrary scripting, or private-database access.
- The prototype strips credential-like request headers after any redirect. A future approved policy may permit explicit redirect hosts, but must define credential forwarding per origin.
- JSON path and safe transform semantics need integration-owner review before serialization into the project schema.
- No application-level Preview/Runtime parity claim is made until both hosts consume this module and the same fixture set.

## Ordered handoff rule

This PR stops at **3.1**. Stage **3.2** (visual Connection Builder, connection workflow and sample/live preview) and **3.3** (UI states, action registry, credentials, redaction, export gate and Preview/Runtime parity) are not part of this handoff. Do not start either stage until the integration owner reviews and accepts the 3.1 exit gate and freezes the dependent Studio/Runtime contracts.
