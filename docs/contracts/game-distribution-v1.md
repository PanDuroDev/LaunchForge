# Game distribution manifest v1 (Phase 4.1 prototype)

> **Status: PROPOSED / PROTOTYPE ONLY.** This contract is not approved for Runtime integration. It deliberately does not define an install root, extraction rules, lifecycle API, or persistent rollback state. Those depend on the Phase 0 filesystem/security decisions and Phase 1 Runtime/build contracts.

## Security model

The manifest and every downloaded byte are untrusted until verification succeeds. The signature authenticates the manifest; the signed SHA-256 and byte count bind each artifact to that manifest. HTTPS is transport protection, not publisher authentication.

The application must provision the publisher trust store out-of-band. A manifest cannot introduce, replace, or rotate its own trusted key. The trust-store lookup key is `(publisher_id, key_id)`. A key rotation/revocation policy and durable anti-rollback state are integration-owner decisions and are not silently specified here.

The v1 prototype uses Ed25519 signatures over the canonical JSON representation described below. The signature is detached from the manifest and delivered as a separate 64-byte value (or strict Base64 encoding at an API boundary). The trusted public key is exactly 32 raw bytes.

## JSON shape

All objects reject unknown fields. Duplicate JSON object keys are invalid. JSON must be UTF-8, with no BOM, floating-point numbers, NaN, or Infinity.

```json
{
  "schema_version": 1,
  "publisher_id": "com.example.publisher",
  "key_id": "release-2026",
  "game_id": "com.example.game",
  "release_version": "1.2.3",
  "issued_at": "2026-01-01T12:00:00Z",
  "files": [
    {
      "path": "bin/Game.exe",
      "url": "https://cdn.example.com/game/1.2.3/bin/Game.exe",
      "size": 123456,
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    }
  ]
}
```

| Field | Rule |
|---|---|
| `schema_version` | Integer exactly `1` (booleans are not integers here). |
| `publisher_id`, `key_id`, `game_id`, `release_version` | Non-empty bounded strings; exact matching is case-sensitive. |
| `issued_at` | UTC RFC 3339 timestamp ending in `Z`; freshness/rollback policy is enforced by a future persistent trust service. |
| `files` | Non-empty array bounded by the consumer's configured file-count limit. |
| `path` | Relative slash-separated destination identity. Must be safe on Windows and POSIX; must be unique under Unicode NFC plus case-folding. This prototype validates names only; it does not write to destination paths. |
| `url` | HTTPS, no user-info or fragment, default port only, and hostname present in the publisher's out-of-band host allowlist. Redirects are rejected. |
| `size` | Exact non-negative integer, bounded per file and in aggregate before any download. |
| `sha256` | Exactly 64 lowercase hexadecimal characters. |

## Canonical signature input

1. Parse strict UTF-8 JSON while rejecting duplicate keys and non-finite values.
2. Validate the complete schema and all limits.
3. Serialize the parsed object as UTF-8 JSON with lexicographically sorted object keys, no insignificant whitespace (`separators=(',', ':')`), `ensure_ascii=False`, and no NaN/Infinity.
4. Verify the detached Ed25519 signature over those canonical bytes using the already-trusted `(publisher_id, key_id)` public key.

Producers must use this exact canonicalization. Consumers must not verify one representation and then consume a different parsed representation.

## Download behavior

- The downloader streams in fixed-size chunks to an exclusively created random temporary file under a caller-provided private temporary directory.
- It enforces declared size, configured per-file/aggregate limits, optional Content-Length consistency, identity content encoding, per-operation network timeout, total operation deadline, cancellation, and SHA-256 before returning a file path.
- The final path is not derived from manifest input. The file is removed on cancellation, error, timeout, or integrity failure.
- Redirects are not followed. A redirect is a failure even when its target appears to be on an allowed host.
- Retries are bounded and limited to transient transport errors and selected retryable HTTP statuses. Integrity, schema, policy, and cancellation errors are not retried.
- Resume/range requests are intentionally omitted from v1 to avoid mixing partial bytes from different representations.

## Limits and non-goals

The implementation has conservative defaults for manifest bytes, file count, per-file size, aggregate release size, and path length. Callers may lower these limits; production increases require a threat-model review.

This contract does **not** authorize extraction, install-root writes, process launch, administrator privileges, DRM, anti-cheat, delta patching, or launcher self-updates. ZIP/TAR archives are not supported by this prototype. Each manifest entry is a single opaque file artifact.

## Required integration decisions (blocked)

Before this contract can be approved for Runtime use, the integration owner must decide: (1) Phase 0 secure path and filesystem semantics, including Windows reparse-point handling; (2) Phase 1 Runtime language/API and cancellation/progress conventions; (3) publisher trust bootstrap, key rotation/revocation, and downgrade policy; (4) per-user storage quota and concurrent download accounting; (5) trusted temporary-directory ownership/permissions; and (6) compatibility policy for future manifest versions.
