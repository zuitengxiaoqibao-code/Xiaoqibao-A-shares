from datetime import datetime, timezone
from pathlib import Path

from qibao_api.local_sources.discovery import (
    LocalTerminalDiscoveryResult,
    LocalTerminalStatus,
)
from qibao_api.local_sources.models import LocalSourceSettings
from qibao_api.local_sources.repository import (
    LocalTerminalDiscoverySnapshotRepository,
)


def _snapshot(root: Path, settings: LocalSourceSettings) -> LocalTerminalDiscoveryResult:
    vipdoc = root / "vipdoc"
    return LocalTerminalDiscoveryResult(
        scanned_at=datetime(2026, 8, 20, 1, 2, tzinfo=timezone.utc),
        terminals=(
            LocalTerminalStatus(
                vendor="tdx",
                install_path=root,
                data_path=vipdoc,
                origin="manual",
                status="ready",
                sh_daily_count=3000,
                sz_daily_count=3000,
            ),
        ),
        active_tdx_vipdoc=vipdoc,
        settings=settings,
    )


def test_discovery_snapshot_round_trips_for_same_settings(tmp_path: Path) -> None:
    settings = LocalSourceSettings(
        auto_discovery=False,
        tdx_install_paths=(tmp_path / "tdx",),
    )
    repository = LocalTerminalDiscoverySnapshotRepository(tmp_path / "discovery.json")
    expected = _snapshot(tmp_path / "tdx", settings)

    repository.save(expected)

    assert repository.load(settings) == expected


def test_discovery_snapshot_rejects_different_settings(tmp_path: Path) -> None:
    saved_settings = LocalSourceSettings(auto_discovery=True)
    repository = LocalTerminalDiscoverySnapshotRepository(tmp_path / "discovery.json")
    repository.save(_snapshot(tmp_path / "tdx", saved_settings))

    assert repository.load(LocalSourceSettings(auto_discovery=False)) is None


def test_discovery_snapshot_treats_invalid_json_as_cache_miss(tmp_path: Path) -> None:
    path = tmp_path / "discovery.json"
    path.write_text("{broken", encoding="utf-8")

    assert LocalTerminalDiscoverySnapshotRepository(path).load(
        LocalSourceSettings()
    ) is None
