# Phase 0 threat model and security baseline

- **Status:** Baseline proposal for integration-owner approval.
- **Assets protected:** User files, launcher project and assets, local game installation, publisher reputation, user credentials, and integrity of exported packages.
- **Trust assumption:** Imported projects, project assets, remote data, and publisher-provided metadata are untrusted input. The exported launcher is a client running on a machine not controlled by LaunchForge.

## Trust boundaries

1. **Studio UI / WebView -> privileged host:** treat every command argument and message as attacker-controlled. The UI is not an authorization boundary.
2. **Project importer -> project validator:** JSON and assets may be malformed, oversized, path-traversing, or crafted to exploit parser/rendering behavior.
3. **Renderer -> Runtime host:** components may request only allowlisted typed actions. Rendering content must never execute user code.
4. **Build process -> exported package:** every resolved input is scanned and validated; client packages are inspectable by their recipients.
5. **Launcher -> local filesystem/processes:** every file path and game launch target is constrained to a pre-authorized root/configuration.
6. **Launcher -> network:** remote JSON and files are not trusted. Networking is outside the Phase 1 MVP and must use bounded HTTPS policy when introduced.

## Threats and controls

| Threat | Example | Required controls |
|---|---|---|
| Secret disclosure | Publisher API key or signing key is serialized into project or package | Classify credentials; keep publisher/server secrets off client; OS secure storage for Studio-only and user credentials; scan build inputs and final package; fail closed without printing the secret |
| Frontend-to-host escalation | XSS or compromised component calls filesystem/process API | No arbitrary scripts/custom components in MVP; Tauri capabilities restricted to local app window; purpose-built Rust commands; validate sender, arguments, IDs, and authorization in host; no generic command bridge |
| Project/asset path traversal | `../../startup` or `C:\...` in an asset path | Strict relative path grammar; reject absolute/UNC/device/drive/ADS/traversal paths; canonicalize immediately before access; verify containment; test symlinks/junctions/reparse points |
| Malicious asset content | SVG contains script or external references | Treat images as data; allowlist raster formats initially or sanitize SVG in a dedicated, tested pipeline; no active content, script, remote image, or HTML embedding by default |
| Renderer injection | Project text becomes executable markup or attribute | Escape text and attributes; avoid untrusted `innerHTML`; use restrictive CSP; never evaluate project text as code or CSS; component/property allowlists |
| Process abuse | Visual action launches arbitrary shell or executable | No shell action; UI may request `launchGame(gameId)` only; host resolves user/publisher-configured executable; validate working directory/arguments; no admin by default; explicit error if target is missing |
| Network abuse (future) | SSRF, cleartext traffic, redirect credential leakage, unbounded response | HTTPS only outside explicitly scoped local development; TLS validation; bounded timeouts, response sizes and retries; cancellation; origin-aware redirects; never forward credentials across origins; no private IP/local-network access by default |
| Update/package tampering (future) | Replaced manifest and artifact share a matching hash | Signed release metadata against a client trust anchor; bind version to artifact; reject invalid signature/downgrade/replay; stage and recover; deferred from MVP |
| Diagnostic leakage | Logs include tokens or user paths | Structured event codes; redact secrets and sensitive paths by default; no raw request headers or arbitrary payload logging |
| Supply-chain compromise | Dependency or build tool changes output | Pin reviewed dependency versions and lockfiles; minimize dependencies; reproducible build metadata; audit dependency changes; secure CI permissions; review release artifacts |

## Credential classes

- **Studio-only:** used to configure/publish; OS secure storage; never included in project JSON or export.
- **Runtime user credentials:** only introduced for a specific supported sign-in flow; scoped, expiring, stored in OS secure storage where persistence is needed.
- **Public project configuration:** public URLs and documented public identifiers may be serialized.
- **Publisher/server secrets:** private API keys, database passwords, signing keys, and service credentials remain on publisher-controlled servers or secure build infrastructure. They must never ship to the launcher.

## MVP network policy

No remote network or private database access is required by the MVP. The Phase 1 Runtime should not expose a generic HTTP command. When Phase 3 introduces data connections, it must require HTTPS in production, validate TLS, set connect/read timeouts, cancellation, content-type/schema limits, response-size limits, redirect rules, and bounded retries. Redirects must not carry credentials to a different origin.

## Filesystem and process policy

- Asset references are stable IDs resolved through a project-owned asset table.
- Project-relative paths use a restricted grammar and are checked again after canonicalization.
- Reject traversal, UNC, drive-qualified, device namespace, alternate data stream, and reserved device names.
- Define symlink/junction/reparse-point handling in the Rust host and test escape attempts on Windows.
- Avoid administrator privileges for per-user workflows.
- The renderer never receives a generic filesystem handle or raw process launcher.
- A game launch action passes a game ID only. The host resolves the preconfigured executable and fixed/validated arguments. Shell parsing is not used.

## Diagnostics policy

Every event uses a stable code and severity. Redact tokens, passwords, authorization headers, private keys, and sensitive path segments. Do not put secret values in exception text. Diagnostic export must be opt-in and preview its sanitized contents before sharing.

## Required adversarial tests before release

1. Invalid JSON, oversized JSON, deep nesting, duplicate IDs, unknown schema/component/action, and malformed Unicode.
2. Asset path traversal, absolute/UNC/device/ADS paths, reserved device names, symlink/junction escape, and time-of-check/time-of-use changes.
3. HTML/script/attribute injection through all text, labels, titles, descriptions, and asset metadata.
4. Unknown host command, wrong argument type, unauthorized window, forged game ID, and invalid launch target.
5. Missing asset/game target, locked files, access denied, and interrupted export.
6. Canary secrets in project, environment, diagnostics, and package; export must fail and logs must not reveal the value.
7. When networking is added: HTTP downgrade, invalid TLS, redirects across origins, oversized/malformed content, timeout, cancellation, and retry exhaustion.

## Out of scope / residual risks

The baseline does not protect a machine already controlled by a local administrator, a compromised Windows kernel, a WebView2 zero-day, a malicious publisher intentionally distributing a harmful launcher, or a compromised developer/build workstation. It reduces accidental privilege exposure; it is not a sandbox certification. Tauri's capability model cannot make unsafe Rust code or overly broad commands safe.
