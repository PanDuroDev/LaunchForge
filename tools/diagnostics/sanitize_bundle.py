#!/usr/bin/env python3
"""Create a minimal support bundle from allow-listed structured diagnostics.

Free-form log messages, stack traces, URLs, paths, user identifiers and unknown
fields are never copied to the exported bundle. This is a reference exporter,
not a replacement for an approved Runtime logging implementation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_LINE_BYTES = 64 * 1024
MAX_RECORDS = 10_000
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

_REQUIRED_FIELDS = {
    "schema_version", "timestamp_utc", "severity", "component", "event_code", "outcome",
}
_OPTIONAL_FIELDS = {
    "error_code", "operation_stage", "duration_ms", "app_version", "runtime_version",
    "platform", "metadata_role", "correlation_id", "attempt",
}
_ALLOWED_FIELDS = _REQUIRED_FIELDS | _OPTIONAL_FIELDS

_SEVERITIES = {"debug", "info", "warning", "error", "critical"}
_COMPONENTS = {"studio", "runtime", "launcher_updater", "game_delivery", "packager", "bootstrapper"}
_OUTCOMES = {"started", "completed", "failed", "cancelled", "recovered", "recovery_failed"}
_EVENT_CODES = {
    "LF_APP_START_FAILED",
    "LF_BOOTSTRAP_FAILED",
    "LF_CONNECTION_FAILED",
    "LF_EXPORT_FAILED",
    "LF_GAME_INSTALL_FAILED",
    "LF_GAME_LAUNCH_FAILED",
    "LF_GAME_REPAIR_FAILED",
    "LF_GAME_UPDATE_FAILED",
    "LF_GAME_VERIFY_FAILED",
    "LF_PROJECT_LOAD_FAILED",
    "LF_PROJECT_SAVE_FAILED",
    "LF_RECOVERY_REQUIRED",
    "LF_RECOVERY_SUCCEEDED",
    "LF_UPDATE_CHECK_FAILED",
    "LF_UPDATE_FAILED",
    "LF_UPDATE_ROLLBACK",
    "LF_UPDATE_SUCCEEDED",
}
_ERROR_CODES = {
    "LF_IO_DENIED", "LF_NETWORK_TIMEOUT", "LF_NETWORK_TLS", "LF_METADATA_EXPIRED",
    "LF_METADATA_SIGNATURE", "LF_METADATA_ROLLBACK", "LF_TARGET_HASH",
    "LF_DISK_SPACE", "LF_PATH_REJECTED", "LF_STAGE_FAILED", "LF_HEALTH_CHECK",
    "LF_ROLLBACK", "LF_RECOVERY_REQUIRED", "LF_RUNTIME_INCOMPATIBLE", "LF_UNKNOWN",
}
_OPERATION_STAGES = {
    "startup", "project_load", "project_save", "connection", "export", "install",
    "upgrade", "uninstall", "metadata_fetch", "metadata_verify", "target_download",
    "target_verify", "stage", "commit", "health_check", "rollback", "recovery",
    "game_install", "game_update", "game_verify", "game_repair", "game_launch",
}
_METADATA_ROLES = {"root", "targets", "snapshot", "timestamp"}
_PLATFORMS = {"windows-x64", "windows-arm64"}
_VERSION_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:alpha|beta|preview|rc)(?:\.(?:0|[1-9][0-9]*))?)?$"
)
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_CORRELATION_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class BundleError(ValueError):
    """The input diagnostic bundle cannot be safely processed."""


@dataclass(frozen=True)
class SanitizeStats:
    """Counts for a sanitized export; contains no source paths or user data."""

    input_records: int
    exported_records: int
    dropped_records: int


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous JSON objects instead of choosing one duplicate value."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BundleError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    """Reject NaN and Infinity tokens that are outside strict JSON."""
    raise BundleError("non-standard JSON constant")


def _reject_float(_: str) -> None:
    """Reject floating-point values; diagnostic schema fields are exact integers."""
    raise BundleError("floating-point value is not allowed")


def _valid_timestamp(value: Any) -> bool:
    """Accept a bounded RFC 3339 UTC timestamp with an explicit Z suffix."""
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _valid_version(value: Any) -> bool:
    """Accept core SemVer with only approved prerelease labels and no build metadata."""
    return isinstance(value, str) and len(value) <= 128 and bool(_VERSION_RE.fullmatch(value))


def _allowed_string(value: Any, allowed: set[str]) -> bool:
    """Return True only when a value is a string in the supplied fixed registry."""
    return isinstance(value, str) and value in allowed


def sanitize_record(record: Any) -> dict[str, Any] | None:
    """Return only a fully valid allow-listed record; drop unknown or unsafe fields."""
    if not isinstance(record, dict):
        return None
    keys = set(record)
    if not _REQUIRED_FIELDS.issubset(keys) or not keys.issubset(_ALLOWED_FIELDS):
        return None

    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        return None
    if not _valid_timestamp(record["timestamp_utc"]):
        return None
    if not _allowed_string(record["severity"], _SEVERITIES):
        return None
    if not _allowed_string(record["component"], _COMPONENTS):
        return None
    if not _allowed_string(record["event_code"], _EVENT_CODES):
        return None
    if not _allowed_string(record["outcome"], _OUTCOMES):
        return None

    safe = {
        "schema_version": 1,
        "timestamp_utc": record["timestamp_utc"],
        "severity": record["severity"],
        "component": record["component"],
        "event_code": record["event_code"],
        "outcome": record["outcome"],
    }
    if "error_code" in record:
        if not _allowed_string(record["error_code"], _ERROR_CODES):
            return None
        safe["error_code"] = record["error_code"]
    if "operation_stage" in record:
        if not _allowed_string(record["operation_stage"], _OPERATION_STAGES):
            return None
        safe["operation_stage"] = record["operation_stage"]
    if "metadata_role" in record:
        if not _allowed_string(record["metadata_role"], _METADATA_ROLES):
            return None
        safe["metadata_role"] = record["metadata_role"]
    if "platform" in record:
        if not _allowed_string(record["platform"], _PLATFORMS):
            return None
        safe["platform"] = record["platform"]
    for version_field in ("app_version", "runtime_version"):
        if version_field in record:
            if not _valid_version(record[version_field]):
                return None
            safe[version_field] = record[version_field]
    if "duration_ms" in record:
        value = record["duration_ms"]
        if type(value) is not int or not 0 <= value <= 86_400_000:
            return None
        safe["duration_ms"] = value
    if "attempt" in record:
        value = record["attempt"]
        if type(value) is not int or not 0 <= value <= 100:
            return None
        safe["attempt"] = value
    if "correlation_id" in record:
        value = record["correlation_id"]
        if not isinstance(value, str) or not _CORRELATION_RE.fullmatch(value):
            return None
        safe["correlation_id"] = value
    return safe


def sanitize_jsonl(raw: bytes) -> tuple[bytes, SanitizeStats]:
    """Sanitize bounded JSONL bytes, dropping malformed records without echoing them."""
    if not isinstance(raw, bytes):
        raise BundleError("input must be bytes")
    if len(raw) > MAX_INPUT_BYTES:
        raise BundleError("input exceeds the 10 MiB limit")
    lines = raw.splitlines()
    if len(lines) > MAX_RECORDS:
        raise BundleError("input exceeds the record-count limit")

    output: list[str] = []
    input_records = 0
    dropped_records = 0
    for line in lines:
        if not line.strip():
            continue
        input_records += 1
        if len(line) > MAX_LINE_BYTES:
            dropped_records += 1
            continue
        try:
            decoded = line.decode("utf-8", errors="strict")
            record = json.loads(
                decoded,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_constant,
                parse_float=_reject_float,
            )
            safe = sanitize_record(record)
        except (UnicodeDecodeError, json.JSONDecodeError, BundleError, RecursionError, ValueError):
            safe = None
        if safe is None:
            dropped_records += 1
            continue
        output.append(json.dumps(safe, sort_keys=True, separators=(",", ":"), ensure_ascii=True))

    encoded = ("\n".join(output) + ("\n" if output else "")).encode("utf-8")
    return encoded, SanitizeStats(input_records, len(output), dropped_records)


def _reject_link_or_reparse(path: Path, context: str) -> os.stat_result:
    """Require a regular non-link file before reading or creating a bundle."""
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & _REPARSE_POINT:
        raise BundleError(f"{context} must not be a symbolic link or reparse point")
    return metadata


def sanitize_file(source: Path, destination: Path) -> SanitizeStats:
    """Write a sanitized bundle to a new file, never overwriting an existing path."""
    source_metadata = _reject_link_or_reparse(source, "source")
    if not stat.S_ISREG(source_metadata.st_mode):
        raise BundleError("source must be a regular file")
    if source_metadata.st_size > MAX_INPUT_BYTES:
        raise BundleError("input exceeds the 10 MiB limit")
    raw = source.read_bytes()
    sanitized, stats = sanitize_jsonl(raw)

    if destination.parent.exists() and not destination.parent.is_dir():
        raise BundleError("destination parent must be a directory")
    descriptor = os.open(
        destination,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(sanitized)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return stats


def main(argv: list[str] | None = None) -> int:
    """Sanitize one JSONL diagnostics file and emit counts without source details."""
    parser = argparse.ArgumentParser(
        description="Export allow-listed LaunchForge diagnostics without free-form data."
    )
    parser.add_argument("source", type=Path, help="input structured diagnostics JSONL")
    parser.add_argument("destination", type=Path, help="new output JSONL path; must not exist")
    args = parser.parse_args(argv)
    try:
        stats = sanitize_file(args.source, args.destination)
    except (BundleError, OSError, ValueError, TypeError):
        print("Diagnostic export refused or could not be completed safely.", file=sys.stderr)
        return 1
    print(
        "Sanitized diagnostic export created: "
        f"{stats.exported_records} retained, {stats.dropped_records} omitted."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
