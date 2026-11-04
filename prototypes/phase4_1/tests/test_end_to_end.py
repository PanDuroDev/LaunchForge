import hashlib
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from launchforge_delivery import BoundedDownloader, parse_and_verify_manifest


class FakeHttpsResponse(BytesIO):
    status = 200

    def __init__(self, payload):
        super().__init__(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def getheader(self, name, default=None):
        return self.headers.get(name, default)


class FakeHttpsOpener:
    def __init__(self, payload):
        self.payload = payload

    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        return FakeHttpsResponse(self.payload)


class SignedDeliveryFlowTests(unittest.TestCase):
    def test_trusted_manifest_downloads_only_the_bound_artifact_bytes(self):
        payload = b"sample publisher-signed game artifact"
        key = Ed25519PrivateKey.generate()
        public_key = key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        document = {
            "schema_version": 1,
            "publisher_id": "sample.publisher",
            "key_id": "test-key-1",
            "game_id": "sample.game",
            "release_version": "1.0.0",
            "issued_at": "2026-01-01T00:00:00Z",
            "files": [{
                "path": "Game/Game.exe",
                "url": "https://cdn.example.test/releases/1.0.0/Game.exe",
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }],
        }
        canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        manifest = parse_and_verify_manifest(
            json.dumps(document).encode("utf-8"),
            key.sign(canonical),
            {("sample.publisher", "test-key-1"): public_key},
            {"cdn.example.test"},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = BoundedDownloader(
                {"cdn.example.test"},
                opener=FakeHttpsOpener(payload),
                retries=0,
            )
            downloaded = downloader.download(manifest.files[0], Path(temp_dir))
            self.assertEqual(downloaded.read_bytes(), payload)
            self.assertEqual(len(list(Path(temp_dir).iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
