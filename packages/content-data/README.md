# @launchforge/content-data — Stage 3.1

A renderer-neutral prototype for the ordered Phase 3.1 handoff: bounded HTTPS JSON transport and typed data/binding semantics against fixtures.

## Included

- HTTPS-only JSON GET transport with manual same-origin redirects, caller cancellation, per-request timeout, bounded streamed response bytes, UTF-8/JSON content-type parsing, structural limits, and bounded retries.
- JSON Pointer (RFC 6901) field mapping with declared output types, optional/default values, and a small explicit transformation allowlist.
- Bounded response-field inspection intended to supply field choices to a later Connection Builder.
- Injected Fetch implementation for deterministic fixture tests.

## Development

Requires Node.js 22+ and TypeScript 5.8+.

```sh
npm install
npm run typecheck
npm test
```

Run commands from this directory. Tests use Node's built-in runner and injected Fetch implementations; no live publisher endpoint is needed.

## Security and stage boundary

Only GET is supported. The adapter requires HTTPS, rejects embedded credentials and common secret query parameters, omits cookies/ambient credentials, disables caching and automatic redirects, rejects cross-origin redirects, strips credential-like request headers after redirects, and bounds response resources. Retries are restricted to transient failures and are capped.

HTTPS validation and same-origin redirect handling do not prevent DNS rebinding or private-address access. A future host adapter must enforce approved DNS/IP egress policy before shipping. Do not use private database credentials from a distributed launcher.

This package is only the 3.1 network/binding prototype. It does not claim the visual Connection Builder, live preview surface, Runtime integration, UI states/actions, secure credential storage, export scanning, or preview/Runtime parity. Those are later stage gates and depend on reviewed Studio/Runtime contracts.
