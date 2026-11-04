from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.release.validate_inventory import ValidationError, validate_inventory


class PublisherInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "artifacts").mkdir()
        self.payload = b"fixture launcher package\n"
        (self.root / "artifacts" / "launcher.exe").write_bytes(self.payload)
        self.inventory = self.valid_inventory()
        self.write_inventory()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def valid_inventory(self) -> dict:
        return {
            "schema_version": 1,
            "product_id": "com.example.launcher",
            "version": "1.2.3",
            "channel": "stable",
            "source_revision": "a" * 40,
            "build": {
                "workflow": "publisher-release.yml",
                "run_id": "123456789",
                "toolchain": "Windows SDK pinned by workflow; toolchain details recorded by CI",
                "built_at_utc": "2026-11-04T20:00:00Z",
            },
            "artifacts": [
                {
                    "name": "launcher.exe",
                    "path": "artifacts/launcher.exe",
                    "platform": "windows-x64",
                    "package_type": "installer",
                    "size_bytes": len(self.payload),
                    "sha256": hashlib.sha256(self.payload).hexdigest(),
                    "signing": {
                        "status": "signed",
                        "subject": "CN=Example Publisher",
                        "certificate_thumbprint": "A" * 40,
                        "timestamped": True,
                        "reason": None,
                    },
                }
            ],
        }

    def write_inventory(self) -> None:
        (self.root / "publisher-artifacts.v1.json").write_text(
            json.dumps(self.inventory), encoding="utf-8"
        )

    def assert_invalid(self, message: str | None = None, *, allow_unsigned: bool = False) -> None:
        self.write_inventory()
        with self.assertRaises(ValidationError) as raised:
            validate_inventory(self.root, allow_unsigned=allow_unsigned)
        if message:
            self.assertIn(message, str(raised.exception))

    def test_accepts_matching_signed_inventory(self) -> None:
        result = validate_inventory(self.root)
        self.assertEqual(result["version"], "1.2.3")

    def test_rejects_duplicate_json_keys(self) -> None:
        raw = (self.root / "publisher-artifacts.v1.json").read_text(encoding="utf-8")
        raw = raw.replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,')
        (self.root / "publisher-artifacts.v1.json").write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "duplicate JSON key"):
            validate_inventory(self.root)

    def test_rejects_unhashable_channel_value(self) -> None:
        self.inventory["channel"] = ["stable"]
        self.assert_invalid("channel must be stable")

    def test_rejects_unhashable_signing_status(self) -> None:
        self.inventory["artifacts"][0]["signing"]["status"] = ["signed"]
        self.assert_invalid("status must be signed")

    def test_rejects_unhashable_package_type(self) -> None:
        self.inventory["artifacts"][0]["package_type"] = ["installer"]
        self.assert_invalid("package_type must be installer")

    def test_rejects_boolean_artifact_size(self) -> None:
        self.inventory["artifacts"][0]["size_bytes"] = True
        self.assert_invalid("positive 64-bit integer")

    def test_rejects_nonstandard_json_constant(self) -> None:
        raw = (self.root / "publisher-artifacts.v1.json").read_text(encoding="utf-8")
        raw = raw.replace(f'"size_bytes": {len(self.payload)}', '"size_bytes": NaN')
        (self.root / "publisher-artifacts.v1.json").write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "non-standard JSON"):
            validate_inventory(self.root)

    def test_rejects_oversized_manifest(self) -> None:
        (self.root / "publisher-artifacts.v1.json").write_text(
            " " * (1024 * 1024 + 1), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValidationError, "1 MiB"):
            validate_inventory(self.root)

    def test_rejects_unknown_fields(self) -> None:
        self.inventory["unreviewed_field"] = "must not silently pass"
        self.assert_invalid("unsupported field")

    def test_rejects_bad_semver(self) -> None:
        self.inventory["version"] = "01.2.3"
        self.assert_invalid("semantic version")

    def test_stable_channel_rejects_prerelease(self) -> None:
        self.inventory["version"] = "1.2.3-rc.1"
        self.assert_invalid("stable channel")

    def test_rejects_numeric_prerelease_identifier_with_leading_zero(self) -> None:
        self.inventory["channel"] = "beta"
        self.inventory["version"] = "1.2.3-beta.02"
        self.assert_invalid("must not contain leading zeroes")

    def test_preview_channel_requires_prerelease(self) -> None:
        self.inventory["channel"] = "preview"
        self.assert_invalid("must contain a prerelease")

    def test_rejects_invalid_timestamp(self) -> None:
        self.inventory["build"]["built_at_utc"] = "2026-02-30T20:00:00Z"
        self.assert_invalid("valid RFC 3339")

    def test_rejects_parent_traversal(self) -> None:
        self.inventory["artifacts"][0]["path"] = "../launcher.exe"
        self.assert_invalid("parent path segment")

    def test_rejects_windows_absolute_path(self) -> None:
        self.inventory["artifacts"][0]["path"] = "C:/temp/launcher.exe"
        self.assert_invalid("relative POSIX path")

    def test_rejects_alternate_data_stream_path(self) -> None:
        self.inventory["artifacts"][0]["path"] = "artifacts/launcher.exe:secret"
        self.assert_invalid("alternate-stream")

    def test_rejects_reserved_windows_device_name(self) -> None:
        self.inventory["artifacts"][0]["path"] = "artifacts/CON.exe"
        self.assert_invalid("reserved Windows device name")

    def test_rejects_windows_forbidden_path_character(self) -> None:
        self.inventory["artifacts"][0]["path"] = "artifacts/launcher?.exe"
        self.assert_invalid("character forbidden in Windows paths")

    def test_rejects_case_insensitive_duplicate_paths(self) -> None:
        duplicate = dict(self.inventory["artifacts"][0])
        duplicate["name"] = "another-name.exe"
        duplicate["path"] = "artifacts/LAUNCHER.exe"
        self.inventory["artifacts"].append(duplicate)
        self.assert_invalid("duplicate artifact path (case-insensitive)")

    def test_rejects_hash_mismatch(self) -> None:
        self.inventory["artifacts"][0]["sha256"] = "0" * 64
        self.assert_invalid("SHA-256 mismatch")

    def test_rejects_size_mismatch(self) -> None:
        self.inventory["artifacts"][0]["size_bytes"] += 1
        self.assert_invalid("size mismatch")

    def test_rejects_duplicate_artifact_path(self) -> None:
        duplicate = dict(self.inventory["artifacts"][0])
        duplicate["name"] = "another-name.exe"
        self.inventory["artifacts"].append(duplicate)
        self.assert_invalid("duplicate artifact path")

    def test_rejects_unsigned_stable_even_with_override(self) -> None:
        signing = self.inventory["artifacts"][0]["signing"]
        signing.update(
            status="unsigned", subject=None, certificate_thumbprint=None,
            timestamped=False, reason="local development fixture"
        )
        self.assert_invalid("stable releases")
        self.write_inventory()
        with self.assertRaisesRegex(ValidationError, "stable releases"):
            validate_inventory(self.root, allow_unsigned=True)

    def test_unsigned_preview_requires_explicit_override(self) -> None:
        self.inventory["channel"] = "preview"
        self.inventory["version"] = "1.2.3-preview.1"
        signing = self.inventory["artifacts"][0]["signing"]
        signing.update(
            status="unsigned", subject=None, certificate_thumbprint=None,
            timestamped=False, reason="local preview only"
        )
        self.assert_invalid("pass --allow-unsigned")
        result = validate_inventory(self.root, allow_unsigned=True)
        self.assertEqual(result["channel"], "preview")

    def test_rejects_symlink_artifact(self) -> None:
        link = self.root / "artifacts" / "linked.exe"
        try:
            link.symlink_to(self.root / "artifacts" / "launcher.exe")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is not available")
        self.inventory["artifacts"][0]["path"] = "artifacts/linked.exe"
        self.assert_invalid("symbolic link or reparse point")

    def test_rejects_symlink_parent(self) -> None:
        other = self.root / "outside"
        other.mkdir()
        (other / "launcher.exe").write_bytes(self.payload)
        linked = self.root / "linked-artifacts"
        try:
            linked.symlink_to(other, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is not available")
        self.inventory["artifacts"][0]["path"] = "linked-artifacts/launcher.exe"
        self.assert_invalid("symbolic link or reparse point")

    def test_rejects_symlink_release_root(self) -> None:
        link = self.root.parent / (self.root.name + "-link")
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is not available")
        try:
            with self.assertRaisesRegex(ValidationError, "release directory"):
                validate_inventory(link)
        finally:
            link.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
