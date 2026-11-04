# LaunchForge Phase 4.1 prototype

**Not production-ready and not integrated with Launcher Runtime.** This isolated Python reference implementation demonstrates the proposed manifest-v1 trust and download boundary. Python is used only because the repository has not selected/approved an implementation stack yet.

## What is included

- Strict JSON parsing (duplicate-key rejection, UTF-8 only, no floats/non-finite values, no unknown fields).
- Ed25519 verification against a caller-supplied out-of-band trust store.
- Cross-platform destination-name validation (traversal, absolute paths, Windows drive/ADS syntax, reserved device names, invalid characters, normalization and case-fold collisions).
- HTTPS host allowlisting, no user-info/fragments/non-default ports, and redirects rejected.
- Streaming downloads to random exclusive temporary files, with byte caps, Content-Length checks, SHA-256 verification, cancellation, operation/network timeouts, progress, bounded retry policy, and cleanup on failure.

## Run tests

From this directory:

```sh
python -m unittest discover -s tests -v
```

Install the package dependency first when needed:

```sh
python -m pip install -e .
```

## API outline

- `parse_and_verify_manifest(...)` parses, validates, bounds, and authenticates the manifest.
- `BoundedDownloader.download(...)` downloads one already-verified `ManifestFile` entry into a private temporary directory and returns its random temporary path only after size/hash verification.

The trust store maps `(publisher_id, key_id)` to a raw 32-byte Ed25519 public key. It must be supplied by trusted application configuration, never from manifest data. The caller must also supply explicit allowed HTTPS hosts and a private temporary directory it owns.

## Explicit limitations

This is a manifest/downloader prototype only. It does not extract archives, write to an installation root, perform transactions, recover interrupted installations, maintain durable version/anti-rollback state, or expose a Runtime lifecycle API. Those are reserved for later reviewed handoffs after Phase 0/1 dependencies and this stage's exit gate are approved. No resume support is provided.
