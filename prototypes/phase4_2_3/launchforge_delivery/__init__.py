"""Isolated Phase 4.2/4.3 game-operations prototype."""
from .transaction import (
    Artifact,
    FileRecord,
    InstallResult,
    IntegrityError,
    RecoveryError,
    RecoveryReport,
    TransactionEngine,
    TransactionError,
    UnsupportedPlatformError,
)
from .lifecycle import GameLifecycleService, GameSnapshot, GameState, LaunchConfig, LauncherAdapter, VerifiedArtifactProvider
from .manifest_adapter import BoundedDownloaderProvider, artifacts_from_verified_manifest

__all__ = [
    "Artifact", "FileRecord", "InstallResult", "IntegrityError", "RecoveryError",
    "RecoveryReport", "TransactionEngine", "TransactionError", "UnsupportedPlatformError",
    "GameLifecycleService", "GameSnapshot", "GameState", "LaunchConfig", "LauncherAdapter", "VerifiedArtifactProvider",
    "artifacts_from_verified_manifest", "BoundedDownloaderProvider",
]
