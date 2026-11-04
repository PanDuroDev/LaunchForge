import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from launchforge_delivery import (
    Artifact,
    FileRecord,
    IntegrityError,
    RecoveryError,
    TransactionEngine,
    TransactionError,
    UnsupportedPlatformError,
)


def artifact(source: Path, relative: str | None = None) -> Artifact:
    """Build an artifact with an integrity record matching the source file."""
    payload = source.read_bytes()
    return Artifact(
        FileRecord(relative or source.name, len(payload), hashlib.sha256(payload).hexdigest()),
        source,
    )


class TransactionTests(unittest.TestCase):
    def setUp(self):
        """Create the temporary install root, source artifacts, and transaction engine for the test."""
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.install = self.base / "InstalledGame"
        self.sources = self.base / "sources"
        self.sources.mkdir()
        self.source_a = self.sources / "game.exe"
        self.source_a.write_bytes(b"first signed game version")
        self.source_b = self.sources / "data.pak"
        self.source_b.write_bytes(b"asset-data-123")
        self.engine = TransactionEngine(self.install, min_free_bytes=1, chunk_size=4)

    def tearDown(self):
        """Remove the temporary filesystem fixture after the test."""
        self.temp.cleanup()

    def release(self, executable_source=None, asset_source=None):
        """Build the complete immutable release fixture from its source files."""
        executable_source = executable_source or self.source_a
        asset_source = asset_source or self.source_b
        return [artifact(executable_source, "bin/game.exe"), artifact(asset_source, "data/assets.pak")]

    def test_backend_fails_closed_when_platform_lacks_posix_safe_primitives(self):
        """Verify that backend fails closed when platform lacks posix safe primitives behaves as expected."""
        with patch("launchforge_delivery.transaction.os.name", "nt"):
            with self.assertRaises(UnsupportedPlatformError):
                TransactionEngine(self.install, min_free_bytes=1)

    def test_install_verify_and_manifest_bound_paths(self):
        """Verify that install verify and manifest bound paths behaves as expected."""
        result = self.engine.install("sample.game", "1.0.0", self.release())
        self.assertEqual(result.action, "install")
        self.assertEqual(result.file_count, 2)
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), self.source_a.read_bytes())
        records = [a.record for a in self.release()]
        self.assertTrue(self.engine.verify(records))
        self.assertFalse(self.engine.verify([FileRecord("bin/game.exe", 1, "0" * 64)]))

    def test_update_swaps_entire_directory_and_removes_old_extras(self):
        """Verify that update swaps entire directory and removes old extras behaves as expected."""
        self.engine.install("sample.game", "1.0.0", self.release())
        (self.install / "old-extra.txt").write_text("old")
        updated = self.base / "sources" / "game-v2.exe"
        updated.write_bytes(b"second release with changes")
        result = self.engine.update("sample.game", "2.0.0", self.release(executable_source=updated))
        self.assertEqual(result.action, "update")
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), updated.read_bytes())
        self.assertFalse((self.install / "old-extra.txt").exists())
        self.assertTrue(self.engine.verify([a.record for a in self.release(executable_source=updated)]))

    def test_repair_replaces_corrupt_file(self):
        """Verify that repair replaces corrupt file behaves as expected."""
        self.engine.install("sample.game", "1.0.0", self.release())
        (self.install / "bin/game.exe").write_bytes(b"tampered")
        self.assertFalse(self.engine.verify([a.record for a in self.release()]))
        self.engine.repair("sample.game", "1.0.0", self.release())
        self.assertTrue(self.engine.verify([a.record for a in self.release()]))

    def test_hash_failure_during_staging_preserves_old_install(self):
        """Verify that hash failure during staging preserves old install behaves as expected."""
        self.engine.install("sample.game", "1.0.0", self.release())
        old = (self.install / "bin/game.exe").read_bytes()
        corrupt = self.base / "sources" / "corrupt.exe"
        corrupt.write_bytes(b"not the signed bytes")
        bad = [Artifact(self.release()[0].record, corrupt), self.release()[1]]
        with self.assertRaises(IntegrityError):
            self.engine.update("sample.game", "2.0.0", bad)
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), old)
        self.assertTrue(self.engine.verify([a.record for a in self.release()]))

    def test_staging_disk_write_error_preserves_old_install(self):
        """Verify that staging disk write error preserves old install behaves as expected."""
        self.engine.install("sample.game", "1.0.0", self.release())
        old = (self.install / "bin/game.exe").read_bytes()
        new_source = self.base / "sources" / "v2.exe"
        new_source.write_bytes(b"next release bytes")
        engine = TransactionEngine(self.install, min_free_bytes=1, fault_hook=lambda point: None)
        with patch.object(engine, "_stage_artifact", side_effect=OSError("simulated ENOSPC")):
            with self.assertRaises(OSError):
                engine.update("sample.game", "2.0.0", self.release(executable_source=new_source))
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), old)
        self.assertEqual(list(self.base.glob(self.engine.stage_prefix + "*")), [])

    def test_traversal_and_windows_path_attacks_rejected(self):
        """Verify that traversal and windows path attacks rejected behaves as expected."""
        for name in ("../escape.exe", "a/../../escape", "/rooted", "C:/escape", "a\\b", "a/file:ads", "a/CON.txt", "a/NUL", "a/trailing.", "a/trailing ", "a/question?.exe"):
            with self.subTest(name=name):
                bad_record = FileRecord(name, 0, hashlib.sha256(b"").hexdigest())
                with self.assertRaises(TransactionError):
                    self.engine.install("game", "1", [Artifact(bad_record, self.source_a)])
        self.assertFalse(self.install.exists())

    def test_casefold_and_file_directory_collisions_rejected(self):
        """Verify that casefold and file directory collisions rejected behaves as expected."""
        first = Artifact(FileRecord("BIN/game.exe", 1, hashlib.sha256(b"x").hexdigest()), self.source_a)
        second = Artifact(FileRecord("bin/GAME.EXE", 1, hashlib.sha256(b"x").hexdigest()), self.source_a)
        with self.assertRaisesRegex(TransactionError, "collisions"):
            self.engine.install("game", "1", [first, second])
        parent = Artifact(FileRecord("bundle", 1, hashlib.sha256(b"x").hexdigest()), self.source_a)
        child = Artifact(FileRecord("bundle/game.exe", 1, hashlib.sha256(b"x").hexdigest()), self.source_a)
        with self.assertRaisesRegex(TransactionError, "nested|conflicts"):
            self.engine.install("game", "1", [parent, child])

    def test_symlink_artifact_source_rejected(self):
        """Verify that symlink artifact source rejected behaves as expected."""
        link = self.sources / "linked.exe"
        try:
            link.symlink_to(self.source_a)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(TransactionError):
            self.engine.install("game", "1", [artifact(link, "game.exe")])
        self.assertFalse(self.install.exists())

    def test_symlink_install_target_rejected(self):
        """Verify that symlink install target rejected behaves as expected."""
        outside = self.base / "outside"
        outside.mkdir()
        link = self.base / "InstalledGame"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(TransactionError):
            self.engine.install("game", "1", self.release())
        self.assertTrue(outside.is_dir())
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_in_parent_chain_rejected(self):
        """Verify that symlink in parent chain rejected behaves as expected."""
        real_parent = self.base / "real-parent"
        real_parent.mkdir()
        link_parent = self.base / "link-parent"
        try:
            link_parent.symlink_to(real_parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        engine = TransactionEngine(link_parent / "Game", min_free_bytes=1)
        with self.assertRaises((OSError, TransactionError)):
            engine.install("game", "1", self.release())
        self.assertFalse((real_parent / "Game").exists())

    def test_old_install_cleanup_does_not_follow_nested_symlinks(self):
        """Verify that old install cleanup does not follow nested symlinks behaves as expected."""
        self.engine.install("game", "1", self.release())
        outside = self.base / "outside-secret.txt"
        outside.write_text("must survive")
        try:
            (self.install / "malicious-link").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        updated = self.base / "sources" / "v2.exe"
        updated.write_bytes(b"v2 bytes")
        self.engine.update("game", "2", self.release(executable_source=updated))
        self.assertEqual(outside.read_text(), "must survive")
        self.assertFalse((self.install / "malicious-link").exists())

    def test_recover_after_old_directory_rename_restores_previous_install(self):
        """Verify that recover after old directory rename restores previous install behaves as expected."""
        self.engine.install("game", "1", self.release())
        old = (self.install / "bin/game.exe").read_bytes()
        new = self.base / "sources" / "new.exe"
        new.write_bytes(b"new version")
        crashing = TransactionEngine(self.install, min_free_bytes=1, fault_hook=lambda p: (_ for _ in ()).throw(KeyboardInterrupt()) if p == "after_old_moved" else None)
        with self.assertRaises(KeyboardInterrupt):
            crashing.update("game", "2", self.release(executable_source=new))
        self.assertFalse(self.install.exists())
        report = self.engine.recover()
        self.assertGreaterEqual(report.transactions_recovered, 1)
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), old)
        self.assertTrue(self.engine.verify([a.record for a in self.release()]))

    def test_recover_after_new_directory_rename_finishes_verified_commit(self):
        """Verify that recover after new directory rename finishes verified commit behaves as expected."""
        self.engine.install("game", "1", self.release())
        new = self.base / "sources" / "new.exe"
        new.write_bytes(b"new release")
        crashing = TransactionEngine(self.install, min_free_bytes=1, fault_hook=lambda p: (_ for _ in ()).throw(KeyboardInterrupt()) if p == "after_new_moved" else None)
        with self.assertRaises(KeyboardInterrupt):
            crashing.update("game", "2", self.release(executable_source=new))
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), new.read_bytes())
        self.engine.recover()
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), new.read_bytes())
        self.assertTrue(self.engine.verify([a.record for a in self.release(executable_source=new)]))

    def test_recover_first_install_before_commit_discards_stage(self):
        """Verify that recover first install before commit discards stage behaves as expected."""
        crashing = TransactionEngine(self.install, min_free_bytes=1, fault_hook=lambda p: (_ for _ in ()).throw(KeyboardInterrupt()) if p == "after_new_moved" else None)
        # First install's hook after_new_moved simulates a crash after the directory is installed.
        with self.assertRaises(KeyboardInterrupt):
            crashing.install("game", "1", self.release())
        self.engine.recover()
        self.assertTrue(self.engine.verify([a.record for a in self.release()]))

    def test_free_space_reserve_and_total_quota_enforced(self):
        """Verify that free space reserve and total quota enforced behaves as expected."""
        limited = TransactionEngine(self.install, max_total_bytes=2, min_free_bytes=1)
        with self.assertRaisesRegex(TransactionError, "aggregate"):
            limited.install("game", "1", self.release())
        huge_reserve = TransactionEngine(self.install, min_free_bytes=10**18)
        with self.assertRaisesRegex(TransactionError, "free space"):
            huge_reserve.install("game", "1", self.release())
        self.assertFalse(self.install.exists())

    def test_update_requires_existing_install_and_install_rejects_overwrite(self):
        """Verify that update requires existing install and install rejects overwrite behaves as expected."""
        with self.assertRaises(TransactionError):
            self.engine.update("game", "2", self.release())
        self.engine.install("game", "1", self.release())
        with self.assertRaises(TransactionError):
            self.engine.install("game", "2", self.release())

    def test_recovery_refuses_symlink_substitution_without_following_it(self):
        """Verify that recovery refuses symlink substitution without following it behaves as expected."""
        self.engine.install("game", "1", self.release())
        old = (self.install / "bin/game.exe").read_bytes()
        new = self.base / "sources" / "next.exe"
        new.write_bytes(b"next version")
        crashing = TransactionEngine(self.install, min_free_bytes=1, fault_hook=lambda p: (_ for _ in ()).throw(KeyboardInterrupt()) if p == "after_old_moved" else None)
        with self.assertRaises(KeyboardInterrupt):
            crashing.update("game", "2", self.release(executable_source=new))
        journal = next(self.base.glob(".InstalledGame.launchforge-journal-*.json"))
        token = journal.name.split("journal-", 1)[1][:-5]
        stage = self.base / (self.engine.stage_prefix + token)
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("safe")
        import shutil
        shutil.rmtree(stage)
        try:
            stage.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(RecoveryError):
            self.engine.recover()
        self.assertEqual((outside / "sentinel").read_text(), "safe")
        stage.unlink()
        self.engine.recover()
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), old)

    def test_interrupted_commit_after_verification_finishes_cleanup(self):
        """Verify that interrupted commit after verification finishes cleanup behaves as expected."""
        self.engine.install("game", "1", self.release())
        new = self.base / "sources" / "next.exe"
        new.write_bytes(b"next version")
        crashing = TransactionEngine(self.install, min_free_bytes=1, fault_hook=lambda p: (_ for _ in ()).throw(KeyboardInterrupt()) if p == "after_commit_verified" else None)
        with self.assertRaises(KeyboardInterrupt):
            crashing.update("game", "2", self.release(executable_source=new))
        self.engine.recover()
        self.assertTrue(self.engine.verify([a.record for a in self.release(executable_source=new)]))
        self.assertEqual(list(self.base.glob(".InstalledGame.launchforge-backup-*")), [])

    def test_verify_rejects_hardlinked_install_file(self):
        """Verify that verify rejects hardlinked install file behaves as expected."""
        self.engine.install("game", "1", self.release())
        target = self.install / "bin/game.exe"
        outside = self.base / "outside-hardlink.exe"
        target.unlink()
        os.link(self.source_a, outside)
        os.link(outside, target)
        self.assertFalse(self.engine.verify([a.record for a in self.release()]))
        self.assertEqual(outside.read_bytes(), self.source_a.read_bytes())

    def test_verify_rejects_unmanifested_files_symlinks_and_special_objects(self):
        """Verify that verify rejects unmanifested files symlinks and special objects behaves as expected."""
        self.engine.install("game", "1", self.release())
        records = [a.record for a in self.release()]
        extra = self.install / "bin/evil.dll"
        extra.write_bytes(b"unmanifested")
        self.assertFalse(self.engine.verify(records))
        extra.unlink()
        outside = self.base / "outside.dll"
        outside.write_bytes(b"outside")
        try:
            (self.install / "bin/linked.dll").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        self.assertFalse(self.engine.verify(records))
        (self.install / "bin/linked.dll").unlink()
        self.assertTrue(self.engine.verify(records))

    def test_recovery_refuses_symlink_backup_without_following_it(self):
        """Verify that recovery refuses symlink backup without following it behaves as expected."""
        self.engine.install("game", "1", self.release())
        old = (self.install / "bin/game.exe").read_bytes()
        next_release = self.base / "sources" / "next-release.exe"
        next_release.write_bytes(b"newer data")
        crashing = TransactionEngine(self.install, min_free_bytes=1, fault_hook=lambda p: (_ for _ in ()).throw(KeyboardInterrupt()) if p == "after_old_moved" else None)
        with self.assertRaises(KeyboardInterrupt):
            crashing.update("game", "2", self.release(executable_source=next_release))
        journal = next(self.base.glob(".InstalledGame.launchforge-journal-*.json"))
        token = journal.name.split("journal-", 1)[1][:-5]
        backup = self.base / (self.engine.backup_prefix + token)
        outside = self.base / "outside-dir"
        outside.mkdir()
        (outside / "sentinel").write_text("preserve")
        import shutil
        shutil.rmtree(backup)
        try:
            backup.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(RecoveryError):
            self.engine.recover()
        self.assertEqual((outside / "sentinel").read_text(), "preserve")
        self.assertFalse(self.install.exists())
        self.assertTrue(backup.is_symlink())
        self.assertEqual(old, self.source_a.read_bytes())

    def test_first_install_interruption_before_swap_discards_candidate(self):
        """Verify that first install interruption before swap discards candidate behaves as expected."""
        crashing = TransactionEngine(self.install, min_free_bytes=1, fault_hook=lambda p: (_ for _ in ()).throw(KeyboardInterrupt()) if p == "before_swap" else None)
        with self.assertRaises(KeyboardInterrupt):
            crashing.install("game", "1", self.release())
        self.assertFalse(self.install.exists())
        report = self.engine.recover()
        self.assertGreaterEqual(report.transactions_recovered, 1)
        self.assertFalse(self.install.exists())
        self.assertEqual(list(self.base.glob(".InstalledGame.launchforge-stage-*")), [])

    def test_post_swap_integrity_failure_rolls_back_previous_install(self):
        """Verify that post swap integrity failure rolls back previous install behaves as expected."""
        self.engine.install("game", "1", self.release())
        old = (self.install / "bin/game.exe").read_bytes()
        next_release = self.base / "sources" / "next.exe"
        next_release.write_bytes(b"new version bytes")
        def corrupt_candidate(stage):
            """Perform the corrupt candidate behavior for TransactionTests."""
            if stage == "after_new_moved":
                (self.install / "bin/game.exe").write_bytes(b"tampered during swap")
        crashing = TransactionEngine(self.install, min_free_bytes=1, fault_hook=corrupt_candidate)
        with self.assertRaisesRegex(IntegrityError, "post-swap"):
            crashing.update("game", "2", self.release(executable_source=next_release))
        self.assertEqual((self.install / "bin/game.exe").read_bytes(), old)
        self.assertTrue(self.engine.verify([a.record for a in self.release()]))
        self.assertEqual(list(self.base.glob(".InstalledGame.launchforge-backup-*")), [])

    def test_transaction_directory_without_journal_is_cleaned(self):
        """Verify that transaction directory without journal is cleaned behaves as expected."""
        name = self.engine.stage_prefix + "a" * 32
        os.mkdir(self.base / name, 0o700)
        (self.base / name / "junk").write_text("partial stage")
        report = self.engine.recover()
        self.assertEqual(report.transactions_recovered, 0)
        self.assertFalse((self.base / name).exists())

    def test_orphan_backup_without_journal_is_never_deleted_automatically(self):
        """Verify that orphan backup without journal is never deleted automatically behaves as expected."""
        name = self.engine.backup_prefix + "b" * 32
        os.mkdir(self.base / name, 0o700)
        (self.base / name / "valuable.exe").write_bytes(b"preserve me")
        with self.assertRaisesRegex(RecoveryError, "orphan backup"):
            self.engine.recover()
        self.assertEqual((self.base / name / "valuable.exe").read_bytes(), b"preserve me")


if __name__ == "__main__":
    unittest.main()
