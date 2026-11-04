import hashlib
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from launchforge_delivery.manifest import ManifestError, ManifestLimits, parse_and_verify_manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        """Create the temporary fixture and test subject."""
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.keys = {("com.example.publisher", "release-2026"): self.public_key}
        self.document = {
            "schema_version": 1,
            "publisher_id": "com.example.publisher",
            "key_id": "release-2026",
            "game_id": "com.example.game",
            "release_version": "1.2.3",
            "issued_at": "2026-01-01T12:00:00Z",
            "files": [{
                "path": "bin/Game.exe",
                "url": "https://cdn.example.com/game/Game.exe",
                "size": 3,
                "sha256": hashlib.sha256(b"abc").hexdigest(),
            }],
        }

    def signed(self, document=None, raw_override=None):
        """Create a canonical signed manifest fixture for the test."""
        obj = self.document if document is None else document
        raw = raw_override or json.dumps(obj, ensure_ascii=False).encode("utf-8")
        canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return raw, self.private_key.sign(canonical)

    def verify(self, document=None, raw_override=None, **kwargs):
        """Verify the signed manifest fixture using its trusted public key."""
        raw, signature = self.signed(document, raw_override)
        return parse_and_verify_manifest(
            raw,
            signature,
            kwargs.get("trusted_keys", self.keys),
            kwargs.get("allowed_hosts", {"cdn.example.com"}),
            kwargs.get("limits", ManifestLimits()),
        )

    def test_valid_signature_and_canonicalization(self):
        """Verify that valid signature and canonicalization behaves as expected."""
        manifest = self.verify()
        self.assertEqual(manifest.game_id, "com.example.game")
        self.assertEqual(manifest.files[0].path, "bin/Game.exe")
        # Original input whitespace/key order is not the signed representation.
        self.assertIn(b'"schema_version":1', manifest.canonical_bytes)

    def test_bad_signature_rejected(self):
        """Verify that bad signature rejected behaves as expected."""
        raw, signature = self.signed()
        bad = bytes([signature[0] ^ 1]) + signature[1:]
        with self.assertRaisesRegex(ManifestError, "signature"):
            parse_and_verify_manifest(raw, bad, self.keys, {"cdn.example.com"})

    def test_untrusted_publisher_key_rejected(self):
        """Verify that untrusted publisher key rejected behaves as expected."""
        with self.assertRaisesRegex(ManifestError, "not trusted"):
            self.verify(trusted_keys={})

    def test_duplicate_json_keys_rejected_before_signature_check(self):
        """Verify that duplicate json keys rejected before signature check behaves as expected."""
        raw = b'{"schema_version":1,"schema_version":1}'
        with self.assertRaisesRegex(ManifestError, "duplicate JSON key"):
            parse_and_verify_manifest(raw, b"x" * 64, self.keys, {"cdn.example.com"})

    def test_unknown_field_and_unsupported_version_rejected(self):
        """Verify that unknown field and unsupported version rejected behaves as expected."""
        changed = dict(self.document, extra="not allowed")
        with self.assertRaisesRegex(ManifestError, "fields mismatch"):
            self.verify(changed)
        changed = dict(self.document, schema_version=2)
        with self.assertRaisesRegex(ManifestError, "schema_version"):
            self.verify(changed)

    def test_signature_type_and_surrogate_strings_rejected(self):
        """Verify that signature type and surrogate strings rejected behaves as expected."""
        with self.assertRaisesRegex(ManifestError, "64 bytes"):
            parse_and_verify_manifest(b"{}", "x" * 64, self.keys, {"cdn.example.com"})
        changed = json.loads(json.dumps(self.document))
        changed["publisher_id"] = "\ud800"
        raw = json.dumps(changed, ensure_ascii=True).encode("utf-8")
        with self.assertRaisesRegex(ManifestError, "surrogate"):
            parse_and_verify_manifest(raw, b"x" * 64, self.keys, {"cdn.example.com"})

    def test_bom_float_and_invalid_utf8_rejected(self):
        """Verify that bom float and invalid utf8 rejected behaves as expected."""
        with self.assertRaisesRegex(ManifestError, "BOM"):
            parse_and_verify_manifest(b"\xef\xbb\xbf{}", b"x" * 64, self.keys, {"cdn.example.com"})
        raw = b'{"schema_version":1.0}'
        with self.assertRaisesRegex(ManifestError, "floating-point"):
            parse_and_verify_manifest(raw, b"x" * 64, self.keys, {"cdn.example.com"})
        with self.assertRaisesRegex(ManifestError, "UTF-8"):
            parse_and_verify_manifest(b"\xff", b"x" * 64, self.keys, {"cdn.example.com"})

    def test_path_traversal_and_windows_unsafe_names_rejected(self):
        """Verify that path traversal and windows unsafe names rejected behaves as expected."""
        bad_paths = [
            "../evil.dll", "bin/../../evil.dll", "/absolute.exe", "C:/Windows/a.exe",
            "bin\\evil.exe", "bin/file:stream", "bin/CON.txt", "bin/LPT1.log",
            "bin/trailing.", "bin/trailing ", "bin/question?.exe", "bin//empty.exe",
        ]
        for path in bad_paths:
            with self.subTest(path=path):
                changed = json.loads(json.dumps(self.document))
                changed["files"][0]["path"] = path
                with self.assertRaises(ManifestError):
                    self.verify(changed)

    def test_file_directory_prefix_conflicts_rejected(self):
        """Verify that file directory prefix conflicts rejected behaves as expected."""
        changed = json.loads(json.dumps(self.document))
        changed["files"][0]["path"] = "bin"
        changed["files"].append(dict(changed["files"][0], path="bin/game.exe"))
        with self.assertRaisesRegex(ManifestError, "nested under"):
            self.verify(changed)

        changed = json.loads(json.dumps(self.document))
        changed["files"][0]["path"] = "bin/game.exe"
        changed["files"].append(dict(changed["files"][0], path="bin"))
        with self.assertRaisesRegex(ManifestError, "conflicts"):
            self.verify(changed)

    def test_unicode_normalization_and_case_collisions_rejected(self):
        """Verify that unicode normalization and case collisions rejected behaves as expected."""
        changed = json.loads(json.dumps(self.document))
        changed["files"][0]["path"] = "bin/e\u0301.exe"
        with self.assertRaisesRegex(ManifestError, "NFC"):
            self.verify(changed)

        changed = json.loads(json.dumps(self.document))
        second = dict(changed["files"][0], path="BIN/game.EXE")
        changed["files"].append(second)
        with self.assertRaisesRegex(ManifestError, "collide"):
            self.verify(changed)

    def test_url_policy_rejects_non_https_credentials_port_and_unapproved_host(self):
        """Verify that url policy rejects non https credentials port and unapproved host behaves as expected."""
        urls = [
            "http://cdn.example.com/file", "https://user@cdn.example.com/file",
            "https://cdn.example.com:444/file", "https://evil.example/file",
            "https://cdn.example.com/file#fragment",
        ]
        for url in urls:
            with self.subTest(url=url):
                changed = json.loads(json.dumps(self.document))
                changed["files"][0]["url"] = url
                with self.assertRaises(ManifestError):
                    self.verify(changed)

    def test_file_and_aggregate_size_caps(self):
        """Verify that file and aggregate size caps behaves as expected."""
        changed = json.loads(json.dumps(self.document))
        changed["files"][0]["size"] = 10
        limits = ManifestLimits(max_file_bytes=9, max_total_bytes=100)
        with self.assertRaisesRegex(ManifestError, "per-file"):
            self.verify(changed, limits=limits)

        changed["files"][0]["size"] = 6
        changed["files"].append(dict(changed["files"][0], path="bin/other.exe"))
        limits = ManifestLimits(max_file_bytes=10, max_total_bytes=10)
        with self.assertRaisesRegex(ManifestError, "aggregate"):
            self.verify(changed, limits=limits)

    def test_manifest_size_limit(self):
        """Verify that manifest size limit behaves as expected."""
        raw, signature = self.signed()
        limits = ManifestLimits(max_manifest_bytes=10)
        with self.assertRaisesRegex(ManifestError, "byte limit"):
            parse_and_verify_manifest(raw, signature, self.keys, {"cdn.example.com"}, limits)

    def test_bool_is_not_accepted_as_integer_size(self):
        """Verify that bool is not accepted as integer size behaves as expected."""
        changed = json.loads(json.dumps(self.document))
        changed["files"][0]["size"] = True
        with self.assertRaisesRegex(ManifestError, "size"):
            self.verify(changed)


if __name__ == "__main__":
    unittest.main()
