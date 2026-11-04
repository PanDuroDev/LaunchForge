#!/usr/bin/env python3
"""Validate a publisher artifact inventory and the files it describes.

This is a publisher-side release QA tool. Its inventory is NOT a client update
manifest and does not authenticate a release or authorize an update.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    """Raised when an inventory or its artifacts violate the release contract."""


_PRODUCT_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_HEX_256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_THUMBPRINT_RE = re.compile(r"^(?:[0-9A-Fa-f]{40}|[0-9A-Fa-f]{64})$")
_PLATFORM_RE = re.compile(r"^windows-[a-z0-9][a-z0-9_-]{0,31}$")
_RUN_ID_RE = re.compile(r"^[0-9]{1,32}$")
_WINDOWS_DEVICE_NAMES = {"con", "prn", "aux", "nul"}
_MAX_ARTIFACTS = 100
_MAX_MANIFEST_BYTES = 1024 * 1024
_MAX_ARTIFACT_BYTES = (1 << 63) - 1
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

_TOP_LEVEL_KEYS = {
    "schema_version", "product_id", "version", "channel",
    "source_revision", "build", "artifacts",
}
_BUILD_KEYS = {"workflow", "run_id", "toolchain", "built_at_utc"}
_ARTIFACT_KEYS = {
    "name", "path", "platform", "package_type", "size_bytes", "sha256", "signing",
}
_SIGNING_KEYS = {
    "status", "subject", "certificate_thumbprint", "timestamped", "reason",
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> None:
    raise ValidationError(f"non-standard JSON numeric constant: {value}")


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{context} must be a JSON object")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    actual = set(value)
    missing, unknown = sorted(expected - actual), sorted(actual - expected)
    if missing:
        raise ValidationError(f"{context} is missing required field(s): {', '.join(missing)}")
    if unknown:
        raise ValidationError(f"{context} contains unsupported field(s): {', '.join(unknown)}")


def _require_string(value: Any, context: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{context} must be a non-empty string")
    if len(value) > maximum or value != value.strip() or "\x00" in value:
        raise ValidationError(f"{context} has invalid whitespace, length, or characters")
    return value


def _validate_version(value: Any, channel: str) -> None:
    version = _require_string(value, "version", maximum=128)
    match = _SEMVER_RE.fullmatch(version)
    if not match:
        raise ValidationError("version must be a valid semantic version")
    prerelease = match.group(4)
    if prerelease is not None:
        identifiers = prerelease.split(".")
        if any(part.isdigit() and len(part) > 1 and part.startswith("0") for part in identifiers):
            raise ValidationError("numeric semantic-version prerelease identifiers must not contain leading zeroes")
    if channel == "stable" and prerelease is not None:
        raise ValidationError("stable channel versions must not contain a prerelease suffix")
    if channel in {"beta", "preview"} and prerelease is None:
        raise ValidationError(f"{channel} channel versions must contain a prerelease suffix")


def _validate_utc_timestamp(value: Any) -> None:
    timestamp = _require_string(value, "build.built_at_utc", maximum=32)
    if not timestamp.endswith("Z"):
        raise ValidationError("build.built_at_utc must use an explicit UTC 'Z' suffix")
    try:
        parsed = datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ValidationError("build.built_at_utc must be a valid RFC 3339 UTC timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise ValidationError("build.built_at_utc must be UTC")


def _safe_relative_path(value: Any, context: str) -> tuple[str, ...]:
    raw = _require_string(value, context, maximum=500)
    if "\\" in raw or raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise ValidationError(f"{context} must be a relative POSIX path")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValidationError(f"{context} contains an empty, current, or parent path segment")
    if any(part.endswith((".", " ")) for part in parts):
        raise ValidationError(f"{context} contains a Windows-ambiguous path segment")
    if any(any(char in part for char in '<>"|?*') for part in parts):
        raise ValidationError(f"{context} contains a character forbidden in Windows paths")
    for part in parts:
        device_stem = part.split(".", 1)[0].casefold()
        if device_stem in _WINDOWS_DEVICE_NAMES or re.fullmatch(r"(?:com|lpt)[1-9]", device_stem):
            raise ValidationError(f"{context} contains a reserved Windows device name")
    if any(":" in part for part in parts):
        raise ValidationError(f"{context} contains a Windows drive or alternate-stream delimiter")
    return tuple(parts)


def _is_reparse_point(path_stat: os.stat_result) -> bool:
    return bool(getattr(path_stat, "st_file_attributes", 0) & _REPARSE_POINT)


def _check_no_links(root: Path, parts: tuple[str, ...], context: str) -> Path:
    current = root
    for index, part in enumerate(parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError as exc:
            raise ValidationError(f"{context} does not exist: {'/'.join(parts)}") from exc
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse_point(metadata):
            raise ValidationError(f"{context} traverses a symbolic link or reparse point")
        if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise ValidationError(f"{context} parent component is not a directory")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValidationError(f"{context} is not a regular file")
    return current


def _hash_file(path: Path, context: str) -> tuple[int, str]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValidationError(f"cannot safely open {context}") from exc
    digest, total = hashlib.sha256(), 0
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValidationError(f"{context} is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                total += len(block)
                digest.update(block)
    finally:
        os.close(descriptor)
    return total, digest.hexdigest()


def _validate_signing(
    value: Any, context: str, *, allow_unsigned: bool, channel: str, package_type: str,
) -> None:
    if channel == "stable" and allow_unsigned:
        raise ValidationError("--allow-unsigned must not be used for stable releases")
    signing = _require_object(value, context)
    _require_exact_keys(signing, _SIGNING_KEYS, context)
    status = signing["status"]
    if not isinstance(status, str) or status not in {"signed", "unsigned", "not-applicable"}:
        raise ValidationError(f"{context}.status must be signed, unsigned, or not-applicable")
    timestamped = signing["timestamped"]
    if type(timestamped) is not bool:
        raise ValidationError(f"{context}.timestamped must be a boolean")
    subject, thumbprint, reason = (
        signing["subject"], signing["certificate_thumbprint"], signing["reason"]
    )
    if status == "signed":
        _require_string(subject, f"{context}.subject", maximum=512)
        if not isinstance(thumbprint, str) or not _THUMBPRINT_RE.fullmatch(thumbprint):
            raise ValidationError(
                f"{context}.certificate_thumbprint must be a 40- or 64-character hex thumbprint"
            )
        if timestamped is not True:
            raise ValidationError(f"{context} signed artifacts must declare a trusted timestamp")
        if reason is not None:
            raise ValidationError(f"{context}.reason must be null for signed artifacts")
    else:
        if subject is not None or thumbprint is not None or timestamped is not False:
            raise ValidationError(
                f"{context} non-signed artifacts must not claim signer identity or timestamping"
            )
        _require_string(reason, f"{context}.reason", maximum=512)
        if channel == "stable":
            raise ValidationError("stable releases must contain only signed artifacts")
        if package_type == "installer" and status == "not-applicable":
            raise ValidationError("installer artifacts must not use the not-applicable signing status")
        if status == "unsigned" and not allow_unsigned:
            raise ValidationError(
                f"{context} is unsigned; pass --allow-unsigned only for a non-production preview build"
            )


def validate_inventory(
    release_dir: Path | str,
    manifest_name: str = "publisher-artifacts.v1.json",
    *,
    allow_unsigned: bool = False,
) -> dict[str, Any]:
    """Validate a publisher inventory and all files it references."""
    root = Path(release_dir)
    try:
        root_metadata = root.lstat()
    except FileNotFoundError as exc:
        raise ValidationError("release directory does not exist") from exc
    if stat.S_ISLNK(root_metadata.st_mode) or _is_reparse_point(root_metadata):
        raise ValidationError("release directory must not be a symbolic link or reparse point")
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise ValidationError("release directory must be a directory")
    root = root.resolve(strict=True)

    manifest_parts = _safe_relative_path(manifest_name, "manifest path")
    manifest_path = _check_no_links(root, manifest_parts, "manifest")
    if manifest_path.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ValidationError("manifest exceeds the 1 MiB size limit")
    try:
        with manifest_path.open("r", encoding="utf-8") as stream:
            inventory = json.load(
                stream,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonstandard_constant,
            )
    except ValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        # ValueError also covers Python's integer-string conversion limit for
        # hostile numeric tokens. Never leak parser internals to CLI diagnostics.
        raise ValidationError("manifest contains invalid or excessively complex JSON") from exc

    inventory = _require_object(inventory, "manifest")
    _require_exact_keys(inventory, _TOP_LEVEL_KEYS, "manifest")
    if type(inventory["schema_version"]) is not int or inventory["schema_version"] != 1:
        raise ValidationError("schema_version must be the integer 1")

    product_id = _require_string(inventory["product_id"], "product_id", maximum=128)
    if not _PRODUCT_ID_RE.fullmatch(product_id):
        raise ValidationError("product_id must use lowercase reverse-DNS-like segments")
    channel = inventory["channel"]
    if not isinstance(channel, str) or channel not in {"stable", "beta", "preview"}:
        raise ValidationError("channel must be stable, beta, or preview")
    _validate_version(inventory["version"], channel)

    revision = inventory["source_revision"]
    if not isinstance(revision, str) or not _REVISION_RE.fullmatch(revision):
        raise ValidationError("source_revision must be a lowercase 40- or 64-character Git revision")

    build = _require_object(inventory["build"], "build")
    _require_exact_keys(build, _BUILD_KEYS, "build")
    _require_string(build["workflow"], "build.workflow", maximum=200)
    run_id = _require_string(build["run_id"], "build.run_id", maximum=32)
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValidationError("build.run_id must contain decimal digits only")
    _require_string(build["toolchain"], "build.toolchain", maximum=512)
    _validate_utc_timestamp(build["built_at_utc"])

    artifacts = inventory["artifacts"]
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= _MAX_ARTIFACTS:
        raise ValidationError(f"artifacts must be an array containing 1 to {_MAX_ARTIFACTS} entries")

    seen_names: set[str] = set()
    seen_paths: set[str] = set()
    for index, raw_artifact in enumerate(artifacts):
        context = f"artifacts[{index}]"
        artifact = _require_object(raw_artifact, context)
        _require_exact_keys(artifact, _ARTIFACT_KEYS, context)
        name = _require_string(artifact["name"], f"{context}.name", maximum=255)
        if "/" in name or "\\" in name or name in {".", ".."}:
            raise ValidationError(f"{context}.name must be a filename, not a path")
        if name.casefold() in seen_names:
            raise ValidationError(f"duplicate artifact name (case-insensitive): {name}")
        seen_names.add(name.casefold())

        parts = _safe_relative_path(artifact["path"], f"{context}.path")
        relative_path = "/".join(parts)
        if relative_path.casefold() in seen_paths:
            raise ValidationError(f"duplicate artifact path (case-insensitive): {relative_path}")
        seen_paths.add(relative_path.casefold())
        if relative_path.casefold() == manifest_name.casefold():
            raise ValidationError(f"{context}.path must not refer to the inventory itself")

        platform = artifact["platform"]
        if not isinstance(platform, str) or not _PLATFORM_RE.fullmatch(platform):
            raise ValidationError(f"{context}.platform must identify a Windows target")
        package_type = artifact["package_type"]
        if not isinstance(package_type, str) or package_type not in {"installer", "portable"}:
            raise ValidationError(f"{context}.package_type must be installer or portable")

        size = artifact["size_bytes"]
        if type(size) is not int or not 0 < size <= _MAX_ARTIFACT_BYTES:
            raise ValidationError(f"{context}.size_bytes must be a positive 64-bit integer")
        expected_hash = artifact["sha256"]
        if not isinstance(expected_hash, str) or not _HEX_256_RE.fullmatch(expected_hash):
            raise ValidationError(f"{context}.sha256 must be a lowercase SHA-256 hex digest")

        _validate_signing(
            artifact["signing"], f"{context}.signing",
            allow_unsigned=allow_unsigned, channel=channel, package_type=package_type,
        )
        artifact_path = _check_no_links(root, parts, f"artifact {relative_path}")
        actual_size, actual_hash = _hash_file(artifact_path, f"artifact {relative_path}")
        if actual_size != size:
            raise ValidationError(
                f"artifact {relative_path} size mismatch (metadata {size}, actual {actual_size})"
            )
        if actual_hash != expected_hash:
            raise ValidationError(f"artifact {relative_path} SHA-256 mismatch")

    return inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a publisher artifact inventory and the local files it describes."
    )
    parser.add_argument("release_dir", type=Path, help="directory containing inventory and release files")
    parser.add_argument(
        "--manifest", default="publisher-artifacts.v1.json",
        help="inventory path relative to release_dir",
    )
    parser.add_argument(
        "--allow-unsigned", action="store_true",
        help="allow unsigned metadata only for beta/preview; never permits unsigned stable artifacts",
    )
    args = parser.parse_args(argv)
    try:
        inventory = validate_inventory(
            args.release_dir, args.manifest, allow_unsigned=args.allow_unsigned
        )
    except (ValidationError, OSError) as exc:
        print(f"Release inventory validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Publisher artifact inventory valid: "
        f"{inventory['product_id']} {inventory['version']} ({inventory['channel']}), "
        f"{len(inventory['artifacts'])} artifact(s)"
    )
    print(
        "Note: hashes prove byte equality only; this tool does not verify Authenticode, "
        "attestations, or update trust."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
