import hashlib
from types import SimpleNamespace
import tempfile
import unittest
from pathlib import Path

from launchforge_delivery import (
    Artifact,
    FileRecord,
    GameLifecycleService,
    GameState,
    BoundedDownloaderProvider,
    TransactionEngine,
    TransactionError,
)


class FakeRuntime:
    def __init__(self):
        """Initialize the fake adapter and record subsequent calls."""
        self.calls = []

    def launch_game(self, game_id):
        """Record the configured game ID and return a deterministic fake process handle."""
        self.calls.append((game_id,))
        return {"pid": 1234}


class FakeDownloader:
    def __init__(self, payload):
        """Initialize the fake adapter and record subsequent calls."""
        self.payload = payload

    def download(self, entry, temporary_directory, *, cancelled=None, progress=None):
        """Return one deterministic temp artifact while forwarding progress and cancellation."""
        if cancelled and cancelled():
            raise TransactionError("cancelled")
        path = Path(temporary_directory) / ("launchforge-download-test-" + entry.path.replace("/", "_"))
        path.write_bytes(self.payload)
        if progress:
            progress(len(self.payload), len(self.payload))
        return path


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        """Create the temporary install root, source artifacts, and transaction engine for the test."""
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.install_dir = self.base / "Game"
        self.source = self.base / "Game.exe"
        self.source.write_bytes(b"verified executable bytes")
        payload = self.source.read_bytes()
        self.record = FileRecord("bin/Game.exe", len(payload), hashlib.sha256(payload).hexdigest())
        self.artifacts = [Artifact(self.record, self.source)]
        self.events = []
        self.engine = TransactionEngine(self.install_dir, min_free_bytes=1, chunk_size=5)
        self.service = GameLifecycleService(self.engine, on_change=self.events.append)

    def tearDown(self):
        """Remove the temporary filesystem fixture after the test."""
        self.temp.cleanup()

    def test_install_reports_staging_commit_verification_and_installed_states(self):
        """Verify that install reports staging commit verification and installed states behaves as expected."""
        result = self.service.install("sample.game", "1.0.0", self.artifacts)
        self.assertEqual(result.version, "1.0.0")
        states = [event.state for event in self.events]
        self.assertIn(GameState.STAGING, states)
        self.assertIn(GameState.COMMITTING, states)
        self.assertIn(GameState.VERIFYING, states)
        self.assertEqual(states[-1], GameState.INSTALLED)
        self.assertEqual(self.service.snapshot.completed_bytes, self.record.size)
        self.assertEqual(self.service.snapshot.total_bytes, self.record.size)

    def test_verify_transitions_to_ready_or_error(self):
        """Verify that verify transitions to ready or error behaves as expected."""
        self.service.install("sample.game", "1", self.artifacts)
        self.assertTrue(self.service.verify("sample.game", "1", [self.record]))
        self.assertEqual(self.service.snapshot.state, GameState.READY)
        (self.install_dir / "bin/Game.exe").write_bytes(b"tampered")
        self.assertFalse(self.service.verify("sample.game", "1", [self.record]))
        self.assertEqual(self.service.snapshot.state, GameState.ERROR)

    def test_launch_only_calls_runtime_for_verified_declared_executable(self):
        """Verify that launch only calls runtime for verified declared executable behaves as expected."""
        self.service.install("sample.game", "1", self.artifacts)
        runtime = FakeRuntime()
        handle = self.service.launch("sample.game", "1", [self.record], runtime)
        self.assertEqual(handle, {"pid": 1234})
        self.assertEqual(self.service.snapshot.state, GameState.RUNNING)
        self.assertEqual(runtime.calls, [("sample.game",)])
        self.service.process_exited(0)
        self.assertEqual(self.service.snapshot.state, GameState.READY)

    def test_launch_bridge_accepts_only_configured_game_id(self):
        """Verify that launch bridge accepts only configured game id behaves as expected."""
        self.service.install("sample.game", "1", self.artifacts)
        runtime = FakeRuntime()
        self.service.launch("sample.game", "1", [self.record], runtime)
        self.assertEqual(runtime.calls, [("sample.game",)])

    def test_launch_rejects_runtime_adapter_without_process_handle(self):
        """Verify that launch rejects runtime adapter without process handle behaves as expected."""
        self.service.install("sample.game", "1", self.artifacts)
        class NoHandleRuntime:
            def launch_game(self, game_id):
                """Record the configured game ID and return a deterministic fake process handle."""
                return None
        with self.assertRaisesRegex(TransactionError, "process handle"):
            self.service.launch("sample.game", "1", [self.record], NoHandleRuntime())
        self.assertEqual(self.service.snapshot.state, GameState.ERROR)

    def test_launch_blocked_if_installed_game_is_corrupt(self):
        """Verify that launch blocked if installed game is corrupt behaves as expected."""
        self.service.install("sample.game", "1", self.artifacts)
        (self.install_dir / "bin/Game.exe").write_bytes(b"tampered")
        runtime = FakeRuntime()
        with self.assertRaisesRegex(TransactionError, "integrity"):
            self.service.launch("sample.game", "1", [self.record], runtime)
        self.assertEqual(runtime.calls, [])

    def test_cancellation_during_staging_does_not_replace_install(self):
        """Verify that cancellation during staging does not replace install behaves as expected."""
        self.service.install("sample.game", "1", self.artifacts)
        old = (self.install_dir / "bin/Game.exe").read_bytes()
        new_source = self.base / "Game-v2.exe"
        new_source.write_bytes(b"version two is significantly longer")
        new_record = FileRecord("bin/Game.exe", new_source.stat().st_size, hashlib.sha256(new_source.read_bytes()).hexdigest())
        new_artifact = Artifact(new_record, new_source)
        original = self.service._set
        def cancel_after_progress(state, **kwargs):
            """Request cancellation after the first positive staging progress event."""
            original(state, **kwargs)
            if state == GameState.STAGING and kwargs.get("completed_bytes", 0) > 0:
                self.service.cancel()
        self.service._set = cancel_after_progress
        with self.assertRaises(TransactionError):
            self.service.update("sample.game", "2", [new_artifact])
        self.assertEqual((self.install_dir / "bin/Game.exe").read_bytes(), old)
        self.assertEqual(self.service.snapshot.state, GameState.CANCELLED)

    def test_manifest_provider_flows_download_progress_into_transaction_and_cleans_temp_files(self):
        """Verify that manifest provider flows download progress into transaction and cleans temp files behaves as expected."""
        temp_downloads = self.base / "downloads"
        temp_downloads.mkdir(mode=0o700)
        manifest = SimpleNamespace(
            game_id="sample.game",
            release_version="1.0.0",
            files=(SimpleNamespace(path="bin/Game.exe", size=self.record.size, sha256=self.record.sha256),),
        )
        provider = BoundedDownloaderProvider(FakeDownloader(self.source.read_bytes()), temp_downloads)
        result = self.service.apply_verified_manifest("install", manifest, provider)
        self.assertEqual(result.action, "install")
        states = [event.state for event in self.events]
        self.assertIn(GameState.DOWNLOADING, states)
        self.assertIn(GameState.STAGING, states)
        self.assertEqual(states[-1], GameState.INSTALLED)
        self.assertEqual(list(temp_downloads.iterdir()), [])

    def test_invalid_provider_progress_is_rejected(self):
        """Verify that invalid provider progress is rejected behaves as expected."""
        class BadProgressProvider:
            def acquire(self, manifest, progress, cancelled):
                """Emit invalid aggregate progress to exercise provider boundary validation."""
                progress(1, 999)
                return {}
            def cleanup(self, downloads):
                """Accept provider cleanup without retaining temporary resources."""
                return None
        manifest = SimpleNamespace(
            game_id="sample.game",
            release_version="1.0.0",
            files=(SimpleNamespace(path="bin/Game.exe", size=self.record.size, sha256=self.record.sha256),),
        )
        with self.assertRaisesRegex(TransactionError, "invalid aggregate progress"):
            self.service.apply_verified_manifest("install", manifest, BadProgressProvider())
        self.assertEqual(self.service.snapshot.state, GameState.ERROR)

    def test_cancel_during_download_is_reported_and_provider_temp_files_are_cleaned(self):
        """Verify that cancel during download is reported and provider temp files are cleaned behaves as expected."""
        temp_downloads = self.base / "downloads"
        temp_downloads.mkdir(mode=0o700)
        manifest = SimpleNamespace(
            game_id="sample.game",
            release_version="1.0.0",
            files=(SimpleNamespace(path="bin/Game.exe", size=self.record.size, sha256=self.record.sha256),),
        )
        service = GameLifecycleService(self.engine, on_change=lambda event: self.service.cancel() if event.state == GameState.DOWNLOADING and event.completed_bytes > 0 else None)
        self.service = service
        provider = BoundedDownloaderProvider(FakeDownloader(self.source.read_bytes()), temp_downloads)
        with self.assertRaises(TransactionError):
            service.apply_verified_manifest("install", manifest, provider)
        self.assertEqual(service.snapshot.state, GameState.CANCELLED)
        self.assertEqual(list(temp_downloads.iterdir()), [])

    def test_rejects_concurrent_lifecycle_operations(self):
        """Verify that rejects concurrent lifecycle operations behaves as expected."""
        self.service._begin("game", "1", 0, GameState.STAGING)
        with self.assertRaises(TransactionError):
            self.service.verify("game", "1", [self.record])
        self.service._busy = False


if __name__ == "__main__":
    unittest.main()
