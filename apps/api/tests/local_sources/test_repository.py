from pathlib import Path

import pytest

from qibao_api.local_sources.models import LocalSourceSettings
from qibao_api.local_sources.repository import LocalSourceSettingsRepository


def test_defaults_disable_optional_realtime_bridge() -> None:
    settings = LocalSourceSettings()

    assert settings.auto_discovery is True
    assert settings.tdx_install_paths == ()
    assert settings.ths_install_paths == ()
    assert settings.tdx_rpc_enabled is False
    assert settings.tdx_rpc_url is None


def test_rejects_network_paths_and_non_loopback_bridge() -> None:
    with pytest.raises(ValueError, match="local absolute path"):
        LocalSourceSettings(tdx_install_paths=(Path("//server/share/tdx"),))
    with pytest.raises(ValueError, match="loopback"):
        LocalSourceSettings(
            tdx_rpc_enabled=True,
            tdx_rpc_url="http://192.168.1.5:17709/",
        )


def test_repository_round_trips_ordered_paths_atomically(tmp_path: Path) -> None:
    repository = LocalSourceSettingsRepository(tmp_path / "data-sources.json")
    first = tmp_path / "tdx-a"
    second = tmp_path / "tdx-b"
    settings = LocalSourceSettings(
        auto_discovery=False,
        tdx_install_paths=(first, second),
        tdx_rpc_enabled=True,
        tdx_rpc_url="http://127.0.0.1:17709/",
    )

    assert repository.load().state == "default"
    repository.save(settings)
    loaded = repository.load()

    assert loaded.state == "ready"
    assert loaded.settings == settings
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_repository_uses_safe_defaults(tmp_path: Path) -> None:
    path = tmp_path / "data-sources.json"
    path.write_text("{broken", encoding="utf-8")

    loaded = LocalSourceSettingsRepository(path).load()

    assert loaded.state == "invalid_local_config"
    assert loaded.settings.tdx_rpc_enabled is False
