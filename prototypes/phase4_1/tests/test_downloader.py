import errno
import hashlib
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from launchforge_delivery.downloader import BoundedDownloader, DownloadCancelled, DownloadError
from launchforge_delivery.manifest import ManifestFile


class FakeResponse:
    status = 200

    def __init__(self, body, headers=None):
        """Initialize the helper state and its test dependencies."""
        self.body = body
        self.offset = 0
        self.headers = headers or {}
        self.closed = False

    def read(self, amount=-1):
        """Read at most the requested number of bytes from the response."""
        if amount < 0:
            amount = len(self.body) - self.offset
        result = self.body[self.offset:self.offset + amount]
        self.offset += len(result)
        return result

    def getheader(self, name, default=None):
        """Return a response header or the supplied default."""
        return self.headers.get(name, default)

    def close(self):
        """Close the underlying response resource."""
        self.closed = True


class FakeOpener:
    def __init__(self, *responses):
        """Initialize the helper state and its test dependencies."""
        self.responses = list(responses)
        self.calls = 0

    def open(self, request, timeout):
        """Open a deterministic fake HTTPS response for the requested URL."""
        self.calls += 1
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        """Create the temporary fixture and test subject."""
        self.payload = b"authenticated game bytes"
        self.entry = ManifestFile(
            path="bin/game.exe",
            url="https://cdn.example.com/releases/game.exe",
            size=len(self.payload),
            sha256=hashlib.sha256(self.payload).hexdigest(),
        )
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        """Remove the temporary fixture and release test resources."""
        self.temp.cleanup()

    def downloader(self, opener, **kwargs):
        """Implement the downloader behavior for DownloaderTests."""
        return BoundedDownloader({"cdn.example.com"}, opener=opener, retries=0, **kwargs)

    def test_success_streams_and_verifies_before_return(self):
        """Verify that success streams and verifies before return behaves as expected."""
        response = FakeResponse(self.payload, {"Content-Length": str(len(self.payload))})
        progress = []
        downloader = self.downloader(FakeOpener(response), chunk_size=5)
        result = downloader.download(self.entry, self.directory, progress=lambda done, total: progress.append((done, total)))
        self.assertEqual(result.read_bytes(), self.payload)
        self.assertTrue(progress)
        self.assertEqual(progress[-1], (len(self.payload), len(self.payload)))
        self.assertTrue(response.closed)

    def test_hash_mismatch_removes_partial_file(self):
        """Verify that hash mismatch removes partial file behaves as expected."""
        entry = ManifestFile(self.entry.path, self.entry.url, self.entry.size, "0" * 64)
        with self.assertRaisesRegex(DownloadError, "SHA-256"):
            self.downloader(FakeOpener(FakeResponse(self.payload))).download(entry, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_short_response_rejected_and_cleaned(self):
        """Verify that short response rejected and cleaned behaves as expected."""
        with self.assertRaisesRegex(DownloadError, "before signed"):
            self.downloader(FakeOpener(FakeResponse(self.payload[:-1]))).download(self.entry, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_oversized_stream_rejected_and_cleaned(self):
        """Verify that oversized stream rejected and cleaned behaves as expected."""
        body = self.payload + b"x"
        entry = ManifestFile(self.entry.path, self.entry.url, len(self.payload), self.entry.sha256)
        with self.assertRaisesRegex(DownloadError, "exceeded"):
            self.downloader(FakeOpener(FakeResponse(body))).download(entry, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_content_length_mismatch_and_compression_rejected(self):
        """Verify that content length mismatch and compression rejected behaves as expected."""
        response = FakeResponse(self.payload, {"Content-Length": "1"})
        with self.assertRaisesRegex(DownloadError, "Content-Length"):
            self.downloader(FakeOpener(response)).download(self.entry, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

        response = FakeResponse(self.payload, {"Content-Encoding": "gzip"})
        with self.assertRaisesRegex(DownloadError, "encoding"):
            self.downloader(FakeOpener(response)).download(self.entry, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_downloader_byte_limit_and_malformed_digest_rejected(self):
        """Verify that downloader byte limit and malformed digest rejected behaves as expected."""
        downloader = self.downloader(FakeOpener(), max_file_bytes=len(self.payload) - 1)
        with self.assertRaisesRegex(DownloadError, "byte limit"):
            downloader.download(self.entry, self.directory)
        bad_digest = ManifestFile(self.entry.path, self.entry.url, self.entry.size, "Z" * 64)
        with self.assertRaisesRegex(DownloadError, "metadata"):
            self.downloader(FakeOpener()).download(bad_digest, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_local_disk_exhaustion_is_not_retried_and_partial_file_is_removed(self):
        """Verify that local disk exhaustion is not retried and partial file is removed behaves as expected."""
        response = FakeResponse(self.payload)
        opener = FakeOpener(response)
        real_fdopen = __import__("os").fdopen

        class FullDiskWriter:
            def __init__(self, wrapped):
                """Initialize the helper state and its test dependencies."""
                self.wrapped = wrapped

            def __enter__(self):
                """Implement the enter   behavior for FullDiskWriter."""
                return self

            def __exit__(self, *args):
                """Implement the exit   behavior for FullDiskWriter."""
                self.wrapped.close()

            def write(self, data):
                """Implement the write behavior for FullDiskWriter."""
                raise OSError(errno.ENOSPC, "no space left on device")

            def flush(self):
                """Implement the flush behavior for FullDiskWriter."""
                self.wrapped.flush()

            def fileno(self):
                """Implement the fileno behavior for FullDiskWriter."""
                return self.wrapped.fileno()

        def failing_fdopen(fd, *args, **kwargs):
            """Implement the failing fdopen behavior for DownloaderTests."""
            return FullDiskWriter(real_fdopen(fd, *args, **kwargs))

        downloader = BoundedDownloader({"cdn.example.com"}, opener=opener, retries=2, retry_backoff_seconds=0)
        with patch("launchforge_delivery.downloader.os.fdopen", side_effect=failing_fdopen):
            with self.assertRaises(DownloadError):
                downloader.download(self.entry, self.directory)
        self.assertEqual(opener.calls, 1)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_non_allowlisted_host_and_http_rejected(self):
        """Verify that non allowlisted host and http rejected behaves as expected."""
        bad = ManifestFile(self.entry.path, "https://evil.example/file", self.entry.size, self.entry.sha256)
        with self.assertRaisesRegex(DownloadError, "allowlisted"):
            self.downloader(FakeOpener()).download(bad, self.directory)
        bad = ManifestFile(self.entry.path, "http://cdn.example.com/file", self.entry.size, self.entry.sha256)
        with self.assertRaisesRegex(DownloadError, "HTTPS"):
            self.downloader(FakeOpener()).download(bad, self.directory)

    def test_cancelled_download_cleans_partial_file(self):
        """Verify that cancelled download cleans partial file behaves as expected."""
        response = FakeResponse(self.payload)
        counter = iter([False, True])
        with self.assertRaises(DownloadCancelled):
            self.downloader(FakeOpener(response), chunk_size=4).download(
                self.entry, self.directory, cancelled=lambda: next(counter, True)
            )
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_redirect_is_not_followed_and_partial_file_cleaned(self):
        """Verify that redirect is not followed and partial file cleaned behaves as expected."""
        redirect = urllib.error.HTTPError(self.entry.url, 302, "Found", {}, None)
        with self.assertRaises(DownloadError):
            self.downloader(FakeOpener(redirect)).download(self.entry, self.directory)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_bounded_retry_on_transient_transport_error(self):
        """Verify that bounded retry on transient transport error behaves as expected."""
        opener = FakeOpener(urllib.error.URLError("temporary"), FakeResponse(self.payload))
        downloader = BoundedDownloader({"cdn.example.com"}, opener=opener, retries=1, retry_backoff_seconds=0)
        result = downloader.download(self.entry, self.directory)
        self.assertEqual(result.read_bytes(), self.payload)
        self.assertEqual(opener.calls, 2)

    def test_cancel_before_request_does_not_create_file(self):
        """Verify that cancel before request does not create file behaves as expected."""
        with self.assertRaises(DownloadCancelled):
            self.downloader(FakeOpener()).download(self.entry, self.directory, cancelled=lambda: True)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_symlink_temp_directory_rejected(self):
        """Verify that symlink temp directory rejected behaves as expected."""
        link = self.directory / "link"
        target = self.directory / "target"
        target.mkdir()
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable on this host")
        with self.assertRaisesRegex(DownloadError, "non-symlink"):
            self.downloader(FakeOpener()).download(self.entry, link)


if __name__ == "__main__":
    unittest.main()
