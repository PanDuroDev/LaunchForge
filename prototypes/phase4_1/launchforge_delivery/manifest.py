"""Strict manifest-v1 parsing and publisher signature verification."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class ManifestError(ValueError):
    """The manifest is malformed, untrusted, or exceeds configured limits."""


@dataclass(frozen=True)
class ManifestLimits:
    max_manifest_bytes: int = 1 * 1024 * 1024
    max_files: int = 10_000
    max_file_bytes: int = 8 * 1024 * 1024 * 1024
    max_total_bytes: int = 64 * 1024 * 1024 * 1024
    max_path_chars: int = 240
    max_identifier_chars: int = 128

    def __post_init__(self) -> None:
        """Validate the configured limits after dataclass initialization."""
        for name, value in vars(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class ManifestFile:
    path: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Manifest:
    publisher_id: str
    key_id: str
    game_id: str
    release_version: str
    issued_at: datetime
    files: tuple[ManifestFile, ...]
    canonical_bytes: bytes


def _object_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build a JSON object while rejecting duplicate keys."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    """Reject non-finite JSON constants before canonicalization."""
    raise ManifestError(f"non-finite JSON number is forbidden: {value}")


def _reject_float(value: str) -> None:
    """Reject floating-point JSON values to keep signed data unambiguous."""
    raise ManifestError(f"floating-point JSON number is forbidden: {value}")


def _parse_integer(value: str) -> int:
    """Parse a bounded JSON integer before Python converts untrusted digit strings."""
    if len(value) > 32:
        raise ManifestError("integer literal exceeds the supported digit limit")
    return int(value)


def _require_string(value: object, name: str, max_chars: int) -> str:
    """Validate a bounded, non-empty Unicode string field."""
    if not isinstance(value, str) or not value or len(value) > max_chars:
        raise ManifestError(f"{name} must be a non-empty string of at most {max_chars} characters")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ManifestError(f"{name} contains an invalid Unicode surrogate") from exc
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ManifestError(f"{name} contains control characters")
    return value


def _validate_path(path: str, max_chars: int) -> str:
    """Reject unsafe or ambiguous cross-platform destination paths."""
    if len(path) > max_chars:
        raise ManifestError("file path exceeds configured path length")
    if unicodedata.normalize("NFC", path) != path:
        raise ManifestError("file path must already be Unicode NFC normalized")
    if path.startswith("/") or "\\" in path or "\x00" in path:
        raise ManifestError("file path must be relative and use '/' separators only")
    if any(ch in path for ch in '<>:"|?*'):
        raise ManifestError("file path contains a character forbidden on Windows")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in path):
        raise ManifestError("file path contains control characters")

    components = path.split("/")
    if not components or any(part in ("", ".", "..") for part in components):
        raise ManifestError("file path contains an empty, '.' or '..' component")

    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved.update(f"COM{i}" for i in range(1, 10))
    reserved.update(f"LPT{i}" for i in range(1, 10))
    reserved.update(f"COM{suffix}" for suffix in ("\u00b9", "\u00b2", "\u00b3"))
    reserved.update(f"LPT{suffix}" for suffix in ("\u00b9", "\u00b2", "\u00b3"))
    for component in components:
        if component.endswith((".", " ")):
            raise ManifestError("file path components may not end in a dot or space")
        if len(component.encode("utf-16-le")) // 2 > 255:
            raise ManifestError("file path component exceeds the Windows component limit")
        device_stem = component.split(".", 1)[0].upper()
        if device_stem in reserved:
            raise ManifestError("file path contains a reserved Windows device name")
    return path


def _validate_url(url: str, allowed_hosts: frozenset[str]) -> None:
    """Require HTTPS URLs whose host is explicitly allowlisted."""
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ManifestError("file URL is malformed") from exc
    if parts.scheme.lower() != "https" or not hostname:
        raise ManifestError("file URL must use HTTPS and include a hostname")
    if parts.username is not None or parts.password is not None or parts.fragment:
        raise ManifestError("file URL must not contain user-info or a fragment")
    if port not in (None, 443):
        raise ManifestError("file URL must use the default HTTPS port")
    try:
        normalized_host = hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise ManifestError("file URL hostname is invalid") from exc
    normalized_allowlist = {host.encode("idna").decode("ascii").lower().rstrip(".") for host in allowed_hosts}
    if normalized_host not in normalized_allowlist:
        raise ManifestError("file URL hostname is not publisher-allowlisted")
    if not parts.path.startswith("/"):
        raise ManifestError("file URL path must be absolute")


def parse_and_verify_manifest(
    raw: bytes,
    signature: bytes,
    trusted_keys: dict[tuple[str, str], bytes],
    allowed_hosts: set[str] | frozenset[str],
    limits: ManifestLimits = ManifestLimits(),
) -> Manifest:
    """Validate and authenticate a manifest using an out-of-band Ed25519 trust store.

    Signature input is the deterministic canonical JSON of the validated object,
    not the original whitespace/key ordering. Duplicate keys and ambiguous JSON
    representations are rejected before canonicalization.
    """
    if not isinstance(raw, bytes) or len(raw) > limits.max_manifest_bytes:
        raise ManifestError("manifest exceeds configured byte limit or is not bytes")
    if not isinstance(signature, bytes) or len(signature) != 64:
        raise ManifestError("Ed25519 signature must be exactly 64 bytes")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ManifestError("UTF-8 BOM is forbidden")
    try:
        text = raw.decode("utf-8", errors="strict")
        document = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_float=_reject_float,
            parse_int=_parse_integer,
            parse_constant=_reject_constant,
        )
    except ManifestError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ManifestError("manifest must be valid UTF-8 JSON") from exc

    if not isinstance(document, dict):
        raise ManifestError("manifest root must be an object")
    required = {
        "schema_version", "publisher_id", "key_id", "game_id",
        "release_version", "issued_at", "files",
    }
    if set(document) != required:
        missing = sorted(required - set(document))
        extra = sorted(set(document) - required)
        raise ManifestError(f"manifest fields mismatch (missing={missing}, extra={extra})")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ManifestError("unsupported manifest schema_version")

    publisher_id = _require_string(document["publisher_id"], "publisher_id", limits.max_identifier_chars)
    key_id = _require_string(document["key_id"], "key_id", limits.max_identifier_chars)
    game_id = _require_string(document["game_id"], "game_id", limits.max_identifier_chars)
    release_version = _require_string(document["release_version"], "release_version", limits.max_identifier_chars)
    issued_at_raw = _require_string(document["issued_at"], "issued_at", 32)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", issued_at_raw) is None:
        raise ManifestError("issued_at must be a UTC RFC 3339 timestamp ending in 'Z'")
    try:
        issued_at = datetime.fromisoformat(issued_at_raw[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestError("issued_at is not a valid RFC 3339 UTC timestamp") from exc

    raw_files = document["files"]
    if not isinstance(raw_files, list) or not raw_files or len(raw_files) > limits.max_files:
        raise ManifestError("files must be a non-empty array within the configured file-count limit")

    files: list[ManifestFile] = []
    seen_paths: set[str] = set()
    total_bytes = 0
    for index, item in enumerate(raw_files):
        if not isinstance(item, dict) or set(item) != {"path", "url", "size", "sha256"}:
            raise ManifestError(f"files[{index}] has missing or unknown fields")
        path = _validate_path(_require_string(item["path"], f"files[{index}].path", limits.max_path_chars), limits.max_path_chars)
        collision_key = unicodedata.normalize("NFC", path).casefold()
        if collision_key in seen_paths:
            raise ManifestError("file paths collide under case-insensitive Unicode normalization")
        path_parts = collision_key.split("/")
        if any("/".join(path_parts[:depth]) in seen_paths for depth in range(1, len(path_parts))):
            raise ManifestError("a manifest file path is nested under another file path")
        if any(existing.startswith(collision_key + "/") for existing in seen_paths):
            raise ManifestError("a manifest file path conflicts with an existing file's directory")
        seen_paths.add(collision_key)

        url = _require_string(item["url"], f"files[{index}].url", 4096)
        _validate_url(url, frozenset(allowed_hosts))
        size = item["size"]
        if type(size) is not int or size < 0 or size > limits.max_file_bytes:
            raise ManifestError(f"files[{index}].size is outside the configured per-file limit")
        total_bytes += size
        if total_bytes > limits.max_total_bytes:
            raise ManifestError("manifest exceeds configured aggregate download limit")
        digest = item["sha256"]
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ManifestError(f"files[{index}].sha256 must be 64 lowercase hexadecimal characters")
        files.append(ManifestFile(path=path, url=url, size=size, sha256=digest))

    canonical = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    public_key_bytes = trusted_keys.get((publisher_id, key_id))
    if public_key_bytes is None:
        raise ManifestError("publisher signing key is not trusted")
    if not isinstance(public_key_bytes, bytes) or len(public_key_bytes) != 32:
        raise ManifestError("trusted Ed25519 public key must be exactly 32 raw bytes")
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(signature, canonical)
    except (InvalidSignature, ValueError) as exc:
        raise ManifestError("manifest signature verification failed") from exc

    return Manifest(
        publisher_id=publisher_id,
        key_id=key_id,
        game_id=game_id,
        release_version=release_version,
        issued_at=issued_at,
        files=tuple(files),
        canonical_bytes=canonical,
    )
