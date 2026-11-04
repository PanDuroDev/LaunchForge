# Diagnostics and crash-reporting policy

**Status:** Phase 5.3 policy and reference exporter. This is not yet wired into Launcher Runtime or Studio because their logging interfaces do not exist in the accepted repository baseline.

## Default collection policy

Diagnostics are local-first. No automatic telemetry, background upload, analytics endpoint, or LaunchForge-hosted reporting service is assumed. Exporting a support bundle requires an explicit user action. The user must be able to inspect the sanitized bundle before sharing it.

Capture only structured, allow-listed events. Prefer stable event codes and static localized error descriptions over arbitrary exception text.

The machine-readable contract is [diagnostic-event-v1.schema.json](../schemas/diagnostic-event-v1.schema.json). The reference exporter accepts only schema version 1 records containing:

| Field | Allowed value |
|---|---|
| \`timestamp_utc\` | Valid RFC 3339 UTC timestamp ending in \`Z\` |
| \`severity\` | debug, info, warning, error, critical |
| \`component\` | studio, runtime, launcher_updater, game_delivery, packager, bootstrapper |
| \`event_code\` | Bounded code matching \`LF_[A-Z0-9_]+\` |
| \`outcome\` | started, completed, failed, cancelled, recovered, recovery_failed |
| \`error_code\` | Fixed LaunchForge error-code registry only |
| \`operation_stage\` | Fixed operation-stage registry only |
| \`duration_ms\`, \`attempt\` | Bounded integers |
| \`app_version\`, \`runtime_version\` | Valid SemVer only |
| \`platform\` | windows-x64 or windows-arm64 |
| \`metadata_role\` | root, targets, snapshot, timestamp |
| \`correlation_id\` | Random UUID, not a user/device identifier |

Unknown fields or invalid values cause the **entire record to be omitted**. The exporter does not attempt to redact arbitrary free-form strings and then keep the rest of that record.

## Never collect or export by default

- Passwords, access tokens, API keys, cookies, authorization headers, private keys, signing credentials, or credential-bearing URLs.
- Request/response bodies, publisher-provided JSON, game manifests, project contents, or arbitrary UI text.
- Usernames, email addresses, account identifiers, machine names, device IDs, IP addresses, hardware serials, or unique hardware fingerprints.
- Absolute paths, home-directory names, install roots, project paths, filenames supplied by untrusted metadata, or full command lines.
- Environment variables, registry exports, process memory, screenshots, crash dumps, or arbitrary attachments.
- Raw exception messages, stack traces, debug dumps, or unbounded network/library error strings.

Do not rely on regex-based secret masking as the primary boundary. Secrets can occur in unfamiliar encodings or new fields. Unknown/unreviewed fields are rejected by default.

## Export procedure

The reference standard-library tool accepts a JSONL input of structured diagnostic records and writes only allow-listed records to a new output file:

\`\`\`powershell
python tools/diagnostics/sanitize_bundle.py .\\diagnostics-raw.jsonl .\\support-diagnostics-safe.jsonl
\`\`\`

The output path must not already exist. The exporter enforces input and line limits, rejects duplicate JSON keys, drops malformed or unknown records, writes a restricted-permission file where the host OS supports POSIX-style mode bits, and reports only retained/omitted counts. It does not print input paths or raw exception details.

Run the reference tests with:

\`\`\`powershell
python -m unittest discover -s tests/diagnostics -v
\`\`\`

The source input must be treated as sensitive and kept in a private local workspace. This utility is a reference implementation, not a secure host logging service; its filesystem protections and race behavior require platform-specific review before being integrated into production.

## Crash reporting and consent

- Crash reporting is disabled by default.
- No crash data is sent automatically or in the background.
- For the initial Windows MVP, do not attach process-memory dumps or minidumps to the standard diagnostic export.
- A future crash-upload feature requires a separate, explicit opt-in at the time of each submission, a preview of the exact payload, a clear explanation of included data and retention, a cancel path, and an operator/publisher-controlled destination.
- A memory dump can contain credentials, private project data and other process memory. It must never be silently bundled with ordinary logs; any future dump collection needs a separate consent control and security review.
- Define retention and deletion rules before operating any reporting endpoint. No endpoint or retention promise is created by this document.

## Runtime integration requirements

When the approved Runtime/Studio logging interfaces exist:

1. Emit typed events through a small logging API; do not accept arbitrary project-controlled field names or values.
2. Map internal exceptions to a stable error code plus a safe static description. Keep raw exception objects in memory only when needed for local debugging, and never export them by default.
3. Keep debug logging opt-in and local-only. Production logs must not include sensitive values.
4. Sanitize at event creation **and** at export; export is a second boundary, not a replacement for safe logging.
5. Test tokens, URLs with user-info, Windows paths, PII, project payloads, malformed JSON, duplicate keys, unknown fields, and oversized records.
6. Review every added diagnostic field for data minimization and a documented support use before adding it to the allowlist.

This policy remains incomplete until the same rules are applied to actual Studio, Runtime, updater, installer and game-delivery logs.
