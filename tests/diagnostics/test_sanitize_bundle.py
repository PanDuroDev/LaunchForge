from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.diagnostics.sanitize_bundle import (
    BundleError,
    MAX_INPUT_BYTES,
    main,
    sanitize_file,
    sanitize_jsonl,
    sanitize_record,
)


class DiagnosticSanitizerTests(unittest.TestCase):
    def setUp(self) -> None:
        # Test-only registry: production remains fail-closed until Runtime/Studio
        # supplies an approved event-code source of truth.
        registry_patch = patch(
            "tools.diagnostics.sanitize_bundle._EVENT_CODES",
            {"LF_UPDATE_FAILED"},
        )
        registry_patch.start()
        self.addCleanup(registry_patch.stop)
        self.safe = {
            "schema_version": 1,
            "timestamp_utc": "2026-11-04T20:00:00Z",
            "severity": "error",
            "component": "launcher_updater",
            "event_code": "LF_UPDATE_FAILED",
            "outcome": "failed",
            "error_code": "LF_METADATA_SIGNATURE",
            "operation_stage": "metadata_verify",
            "duration_ms": 1234,
            "app_version": "1.2.3",
            "runtime_version": "1.2.0",
            "platform": "windows-x64",
            "metadata_role": "targets",
            "correlation_id": "123e4567-e89b-42d3-a456-426614174000",
            "attempt": 2,
        }

    def test_fails_closed_without_approved_event_registry(self) -> None:
        with patch("tools.diagnostics.sanitize_bundle._EVENT_CODES", set()):
            raw = json.dumps(self.safe).encode("utf-8") + b"\n"
            first, stats = sanitize_jsonl(raw)
            second, _ = sanitize_jsonl(raw)
            self.assertEqual(first, second)
            self.assertEqual(first, b"")
            self.assertEqual(stats.input_records, 1)
            self.assertEqual(stats.exported_records, 0)
            self.assertEqual(stats.dropped_records, 1)
            self.assertIsNone(sanitize_record(self.safe))

    def test_unknown_fields_drop_entire_record_including_secret(self) -> None:
        hostile = dict(self.safe)
        hostile["message"] = "Authorization: Bearer top-secret-token"
        hostile["path"] = r"C:\Users\alice\AppData\private.db"
        hostile["url"] = "https://user:password@example.invalid/private?token=secret"
        hostile["username"] = "alice@example.invalid"
        output, stats = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")
        self.assertEqual(stats.dropped_records, 1)
        for secret in (b"top-secret-token", b"private.db", b"password", b"alice@example.invalid"):
            self.assertNotIn(secret, output)

    def test_malformed_and_unknown_field_records_are_omitted(self) -> None:
        hostile = dict(self.safe, exception="token=secret")
        raw = (
            json.dumps(self.safe).encode("utf-8")
            + b"\n{not json}\n"
            + json.dumps(hostile).encode("utf-8")
            + b"\n"
        )
        output, stats = sanitize_jsonl(raw)
        self.assertEqual(stats.input_records, 3)
        self.assertEqual(stats.exported_records, 1)
        self.assertEqual(stats.dropped_records, 2)
        self.assertEqual(len(output.splitlines()), 1)
        self.assertEqual(json.loads(output), self.safe)

    def test_duplicate_json_keys_are_omitted(self) -> None:
        raw = (
            b'{"schema_version":1,"schema_version":1,'
            b'"timestamp_utc":"2026-11-04T20:00:00Z"}'
        )
        output, stats = sanitize_jsonl(raw)
        self.assertEqual(output, b"")
        self.assertEqual(stats.dropped_records, 1)

    def test_non_utf8_record_is_omitted(self) -> None:
        output, stats = sanitize_jsonl(b"\xff\xfe\xfa")
        self.assertEqual(output, b"")
        self.assertEqual(stats.dropped_records, 1)

    def test_free_form_message_is_never_allow_listed(self) -> None:
        hostile = dict(self.safe, message="failed at C:/Users/alice")
        output, _ = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")

    def test_bool_does_not_pass_integer_fields(self) -> None:
        hostile = dict(self.safe, duration_ms=True)
        output, _ = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")

    def test_rejects_unknown_error_code(self) -> None:
        hostile = dict(self.safe, error_code="Authorization:Bearer-secret")
        output, _ = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")

    def test_unhashable_enum_value_is_dropped(self) -> None:
        hostile = dict(self.safe, severity=["error"])
        output, stats = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")
        self.assertEqual(stats.dropped_records, 1)

    def test_non_string_registry_values_are_returned_as_invalid(self) -> None:
        fields = (
            "severity", "component", "outcome", "error_code",
            "operation_stage", "metadata_role", "platform",
        )
        for field in fields:
            for value in (["error"], {"value": "error"}):
                with self.subTest(field=field, value=value):
                    hostile = dict(self.safe)
                    hostile[field] = value
                    self.assertIsNone(sanitize_record(hostile))
                    output, stats = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
                    self.assertEqual(output, b"")
                    self.assertEqual(stats.dropped_records, 1)

    def test_rejects_uuid_v1_correlation_id(self) -> None:
        hostile = dict(self.safe, correlation_id="123e4567-e89b-12d3-a456-426614174000")
        output, stats = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")
        self.assertEqual(stats.dropped_records, 1)

    def test_rejects_event_code_outside_fixed_registry(self) -> None:
        hostile = dict(self.safe, event_code="LF_API_KEY_ABCDEF0123456789")
        output, stats = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")
        self.assertEqual(stats.dropped_records, 1)

    def test_rejects_unapproved_semver_identifiers_and_build_metadata(self) -> None:
        for field, value in (
            ("app_version", "1.2.3-alice"),
            ("runtime_version", "1.2.3+secret-token"),
            ("app_version", "1.2.3-release-candidate"),
        ):
            with self.subTest(field=field, value=value):
                hostile = dict(self.safe, **{field: value})
                output, stats = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
                self.assertEqual(output, b"")
                self.assertEqual(stats.dropped_records, 1)

    def test_oversized_integer_literal_is_dropped(self) -> None:
        raw = json.dumps(self.safe).replace('"duration_ms": 1234', '"duration_ms": ' + ("9" * 5000))
        output, stats = sanitize_jsonl(raw.encode("utf-8"))
        self.assertEqual(output, b"")
        self.assertEqual(stats.dropped_records, 1)

    def test_rejects_symlink_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual = root / "actual.jsonl"
            link = root / "linked.jsonl"
            actual.write_text(json.dumps(self.safe), encoding="utf-8")
            try:
                link.symlink_to(actual)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is not available")
            with self.assertRaisesRegex(BundleError, "symbolic link"):
                sanitize_file(link, root / "safe.jsonl")

    def test_rejects_unknown_component(self) -> None:
        hostile = dict(self.safe, component="C:/Users/Alice")
        output, _ = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")

    def test_rejects_invalid_version(self) -> None:
        hostile = dict(self.safe, app_version="1.2.3 token-secret")
        output, _ = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
        self.assertEqual(output, b"")

    def test_rejects_non_utc_or_invalid_timestamps(self) -> None:
        for timestamp in ("2026-11-04T20:00:00+02:00", "2026-02-30T20:00:00Z", "token"):
            with self.subTest(timestamp=timestamp):
                hostile = dict(self.safe, timestamp_utc=timestamp)
                output, _ = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
                self.assertEqual(output, b"")

    def test_rejects_path_or_url_fields_by_dropping_record(self) -> None:
        for field, value in (
            ("path", r"C:\Users\alice\game.exe"),
            ("url", "https://private.example.invalid/?key=secret"),
            ("stack_trace", "secret stack"),
            ("machine_name", "DESKTOP-SECRET"),
        ):
            with self.subTest(field=field):
                hostile = dict(self.safe, **{field: value})
                output, _ = sanitize_jsonl(json.dumps(hostile).encode("utf-8"))
                self.assertEqual(output, b"")

    def test_rejects_oversized_input(self) -> None:
        with self.assertRaisesRegex(BundleError, "10 MiB"):
            sanitize_jsonl(b"x" * (MAX_INPUT_BYTES + 1))

    def test_rejects_too_many_records(self) -> None:
        raw = b"\n" * 10_001
        with self.assertRaisesRegex(BundleError, "record-count"):
            sanitize_jsonl(raw)

    def test_oversized_record_is_dropped(self) -> None:
        oversized = b"x" * (64 * 1024 + 1)
        output, stats = sanitize_jsonl(oversized)
        self.assertEqual(output, b"")
        self.assertEqual(stats.dropped_records, 1)

    def test_file_export_does_not_overwrite_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "raw.jsonl"
            destination = root / "safe.jsonl"
            source.write_text(json.dumps(self.safe), encoding="utf-8")
            destination.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                sanitize_file(source, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), "keep")

    def test_file_export_creates_new_sanitized_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "raw.jsonl"
            destination = root / "safe.jsonl"
            source.write_text(json.dumps(self.safe), encoding="utf-8")
            stats = sanitize_file(source, destination)
            self.assertEqual(stats.exported_records, 1)
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), self.safe)
            if os.name != "nt":
                self.assertEqual(destination.stat().st_mode & 0o777, 0o600)

    def test_cli_returns_generic_error_without_leaking_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "nonexistent-private-input.jsonl"
            destination = Path(tmp) / "safe.jsonl"
            import contextlib
            import io
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main([str(source), str(destination)])
            self.assertEqual(code, 1)
            self.assertNotIn(str(source), stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
