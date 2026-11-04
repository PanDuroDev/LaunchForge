import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from launchforge_delivery import BoundedDownloaderProvider, TransactionError, artifacts_from_verified_manifest


class ManifestAdapterTests(unittest.TestCase):
    def test_maps_verified_manifest_entries_to_transaction_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "game.bin"
            source.write_bytes(b"artifact")
            manifest = SimpleNamespace(files=(SimpleNamespace(path="bin/game.bin", size=8, sha256=hashlib.sha256(b"artifact").hexdigest()),))
            mapped = artifacts_from_verified_manifest(manifest, {"bin/game.bin": source})
            self.assertEqual(mapped[0].record.path, "bin/game.bin")
            self.assertEqual(mapped[0].source, source)

    def test_downloader_provider_requires_private_directory_and_rejects_symlinked_path(self):
        with tempfile.TemporaryDirectory() as folder:
            private = Path(folder) / "private"
            private.mkdir(mode=0o700)
            provider = BoundedDownloaderProvider(object(), private)
            self.assertEqual(provider.temporary_directory, private)

            public = Path(folder) / "public"
            public.mkdir(mode=0o755)
            with self.assertRaisesRegex(TransactionError, "inaccessible"):
                BoundedDownloaderProvider(object(), public)

            link = Path(folder) / "link"
            try:
                link.symlink_to(private, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable")
            with self.assertRaises(TransactionError):
                BoundedDownloaderProvider(object(), link)

    def test_missing_extra_or_unsafe_paths_rejected(self):
        entry = SimpleNamespace(path="bin/game.bin", size=1, sha256="0" * 64)
        manifest = SimpleNamespace(files=(entry,))
        with self.assertRaisesRegex(TransactionError, "missing"):
            artifacts_from_verified_manifest(manifest, {})
        with self.assertRaisesRegex(TransactionError, "unexpected"):
            artifacts_from_verified_manifest(manifest, {"bin/game.bin": Path("/tmp/a"), "extra": Path("/tmp/b")})
        entry.path = "../escape.exe"
        with self.assertRaises(TransactionError):
            artifacts_from_verified_manifest(manifest, {"../escape.exe": Path("/tmp/a")})


if __name__ == "__main__":
    unittest.main()
