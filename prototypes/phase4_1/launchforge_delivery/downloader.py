"""Bounded, hash-verifying HTTPS artifact downloader (no extraction/install)."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional, Protocol

from .manifest import ManifestFile


class DownloadError(RuntimeError):
    """Download rejected or failed validation."""


class DownloadCancelled(DownloadError):
    """The caller cancelled an in-progress download."""


class _Response(Protocol):
    status: int

    def read(self, amount: int = -1) -> bytes:
        """Read at most the requested number of bytes from the response."""
        ...
    def read1(self, amount: int = -1) -> bytes:
        """Read at most one underlying chunk from the response."""
        ...
    def getheader(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Return a response header or the supplied default."""
        ...
    def close(self) -> None:
        """Close the underlying response resource."""
        ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Reject redirects so downloads cannot leave the approved origin."""
        return None


class BoundedDownloader:
    """Download one signed manifest entry to a random temporary file.

    temporary_directory must be private, owned by the caller, and not writable
    by an untrusted local principal. Install-root path safety is intentionally
    outside the scope of this Phase 4.1 prototype.
    """

    RETRYABLE_HTTP = {408, 429, 500, 502, 503, 504}

    def __init__(
        self,
        allowed_hosts: set[str] | frozenset[str],
        *,
        max_file_bytes: int = 8 * 1024 * 1024 * 1024,
        timeout_seconds: float = 20.0,
        total_timeout_seconds: float = 300.0,
        retries: int = 1,
        chunk_size: int = 64 * 1024,
        opener=None,
        retry_backoff_seconds: float = 0.1,
    ) -> None:
        """Initialize the helper state and its test dependencies."""
        if max_file_bytes <= 0 or timeout_seconds <= 0 or total_timeout_seconds <= 0:
            raise ValueError("download limits and timeouts must be positive")
        if retries < 0 or retries > 3:
            raise ValueError("retries must be between 0 and 3")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.allowed_hosts = frozenset(allowed_hosts)
        self.max_file_bytes = max_file_bytes
        self.timeout_seconds = timeout_seconds
        self.total_timeout_seconds = total_timeout_seconds
        self.retries = retries
        self.chunk_size = chunk_size
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.opener = opener or urllib.request.build_opener(_NoRedirect())

    def download(
        self,
        entry: ManifestFile,
        temporary_directory: Path,
        *,
        cancelled: Optional[Callable[[], bool]] = None,
        progress: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """Return a verified random temp path; delete partial files on every failure."""
        self._validate_entry(entry)
        if entry.size > self.max_file_bytes:
            raise DownloadError("artifact exceeds configured downloader byte limit")
        directory = Path(temporary_directory)
        if not directory.is_dir() or directory.is_symlink():
            raise DownloadError("temporary directory must be an existing non-symlink directory")

        deadline = time.monotonic() + self.total_timeout_seconds
        last_error: Optional[BaseException] = None
        for attempt in range(self.retries + 1):
            if cancelled and cancelled():
                raise DownloadCancelled("download cancelled before request")
            if time.monotonic() >= deadline:
                raise DownloadError("download exceeded total operation timeout") from last_error
            try:
                return self._download_once(entry, directory, deadline, cancelled, progress)
            except DownloadCancelled:
                raise
            except Exception as exc:
                last_error = exc
                if isinstance(exc, urllib.error.HTTPError):
                    exc.close()
                if not self._is_retryable(exc) or attempt >= self.retries:
                    if isinstance(exc, DownloadError):
                        raise
                    raise DownloadError(f"artifact download failed: {exc}") from exc
                delay = self.retry_backoff_seconds * (2 ** attempt)
                if time.monotonic() + delay >= deadline:
                    raise DownloadError("download exceeded total operation timeout") from exc
                time.sleep(delay)
        raise DownloadError("download failed") from last_error

    def _validate_entry(self, entry: ManifestFile) -> None:
        """Revalidate transport and integrity metadata at the downloader boundary."""
        # ManifestFile is a public dataclass; callers must not bypass manifest verification.
        # Repeat transport-sensitive checks here to keep this boundary defensive.
        from urllib.parse import urlsplit

        try:
            parts = urlsplit(entry.url)
            hostname = parts.hostname
            port = parts.port
        except (AttributeError, ValueError) as exc:
            raise DownloadError("artifact URL is malformed") from exc
        if parts.scheme != "https" or not hostname or parts.username or parts.password or parts.fragment or port not in (None, 443):
            raise DownloadError("artifact URL violates HTTPS transport policy")
        normalized_host = hostname.encode("idna").decode("ascii").lower().rstrip(".")
        normalized_allowlist = {host.encode("idna").decode("ascii").lower().rstrip(".") for host in self.allowed_hosts}
        if normalized_host not in normalized_allowlist:
            raise DownloadError("artifact URL host is not allowlisted")
        if (
            type(entry.size) is not int
            or entry.size < 0
            or not isinstance(entry.sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", entry.sha256) is None
        ):
            raise DownloadError("artifact metadata is invalid")

    def _download_once(self, entry, directory, deadline, cancelled, progress) -> Path:
        """Stream one response into an exclusive temporary file and verify its exact digest."""
        fd, temp_name = tempfile.mkstemp(prefix="launchforge-download-", suffix=".part", dir=directory)
        temp_path = Path(temp_name)
        response = None
        try:
            request = urllib.request.Request(
                entry.url,
                headers={"Accept-Encoding": "identity", "User-Agent": "LaunchForge-Delivery-Prototype/0.1"},
                method="GET",
            )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DownloadError("download exceeded total operation timeout")
            response = self.opener.open(request, timeout=min(self.timeout_seconds, remaining))
            status = getattr(response, "status", 200)
            if status != 200:
                raise DownloadError(f"unexpected HTTP status: {status}")
            encoding = response.getheader("Content-Encoding")
            if encoding and encoding.strip().lower() not in ("", "identity"):
                raise DownloadError("compressed content encoding is not accepted")
            content_length = response.getheader("Content-Length")
            if content_length is not None:
                if not content_length.isascii() or not content_length.isdigit():
                    raise DownloadError("invalid Content-Length header")
                if int(content_length) != entry.size:
                    raise DownloadError("Content-Length does not match signed manifest size")

            digest = hashlib.sha256()
            received = 0
            # HTTPResponse.read(amt) may wait for the entire amount. read1()
            # returns after at most one recv so deadline/cancellation checks
            # run between short reads even when a peer trickles bytes.
            read_chunk = getattr(response, "read1", response.read)
            with os.fdopen(fd, "wb", closefd=True) as output:
                fd = -1
                while True:
                    if cancelled and cancelled():
                        raise DownloadCancelled("download cancelled")
                    remaining_time = deadline - time.monotonic()
                    if remaining_time <= 0:
                        raise DownloadError("download exceeded total operation timeout")
                    chunk = read_chunk(min(self.chunk_size, entry.size - received + 1))
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > entry.size or received > self.max_file_bytes:
                        raise DownloadError("download exceeded signed or configured byte limit")
                    digest.update(chunk)
                    output.write(chunk)
                    if progress:
                        progress(received, entry.size)
                output.flush()
                os.fsync(output.fileno())

            if received != entry.size:
                raise DownloadError("download ended before signed manifest size")
            if digest.hexdigest() != entry.sha256:
                raise DownloadError("download SHA-256 does not match signed manifest")
            return temp_path
        except BaseException:
            if fd >= 0:
                os.close(fd)
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    # A close failure must not invalidate a fully verified file or
                    # hide the original download error.
                    pass

    @classmethod
    def _is_retryable(cls, exc: BaseException) -> bool:
        """Classify transient transport failures without retrying policy or integrity failures."""
        if isinstance(exc, (DownloadCancelled, DownloadError)):
            return False
        if isinstance(exc, urllib.error.HTTPError):
            return exc.code in cls.RETRYABLE_HTTP
        # Do not retry arbitrary OSError: ENOSPC, permission errors and local
        # filesystem failures are not transient network failures.
        return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError))
