from pathlib import Path

from qibao_api.local_sources.discovery import (
    LocalTerminalDiscovery,
    SystemCandidate,
)
from qibao_api.local_sources.models import LocalSourceSettings


def create_tdx(root: Path, *, sh_count: int = 2, sz_count: int = 1) -> Path:
    for exchange, count in (("sh", sh_count), ("sz", sz_count)):
        lday = root / "vipdoc" / exchange / "lday"
        lday.mkdir(parents=True)
        for index in range(count):
            (lday / f"{exchange}{index:06d}.day").write_bytes(b"daily")
    (root / "TdxW.exe").write_bytes(b"exe")
    return root


def test_manual_tdx_path_wins_and_reports_local_file_coverage(tmp_path: Path) -> None:
    manual = create_tdx(tmp_path / "manual")
    detected = create_tdx(tmp_path / "detected", sh_count=1, sz_count=1)
    discovery = LocalTerminalDiscovery(
        system_candidates=lambda: (
            SystemCandidate(vendor="tdx", path=detected, origin="process"),
        )
    )

    result = discovery.inspect(LocalSourceSettings(tdx_install_paths=(manual,)))

    assert result.active_tdx_vipdoc == manual / "vipdoc"
    assert [item.origin for item in result.terminals[:2]] == ["manual", "process"]
    assert result.terminals[0].status == "ready"
    assert result.terminals[0].sh_daily_count == 2
    assert result.terminals[0].sz_daily_count == 1


def test_direct_vipdoc_path_is_normalized_and_duplicates_are_removed(
    tmp_path: Path,
) -> None:
    root = create_tdx(tmp_path / "tdx")
    discovery = LocalTerminalDiscovery(
        system_candidates=lambda: (
            SystemCandidate(vendor="tdx", path=root, origin="process"),
        )
    )

    result = discovery.inspect(LocalSourceSettings(
        tdx_install_paths=(root / "vipdoc", root),
    ))

    assert len([item for item in result.terminals if item.vendor == "tdx"]) == 1
    assert result.terminals[0].install_path == root
    assert result.terminals[0].data_path == root / "vipdoc"


def test_ths_install_is_detected_but_not_claimed_as_a_local_data_source(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ths"
    root.mkdir()
    (root / "hexin.exe").write_bytes(b"exe")
    discovery = LocalTerminalDiscovery(system_candidates=lambda: ())

    result = discovery.inspect(LocalSourceSettings(ths_install_paths=(root,)))

    terminal = result.terminals[0]
    assert terminal.vendor == "ths"
    assert terminal.status == "detected_only"
    assert terminal.data_path is None
    assert result.active_tdx_vipdoc is None


def test_ths_variant_with_nested_launcher_is_detected(tmp_path: Path) -> None:
    root = tmp_path / "ths-variant"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "hexinlauncher.exe").write_bytes(b"exe")

    result = LocalTerminalDiscovery(system_candidates=lambda: ()).inspect(
        LocalSourceSettings(ths_install_paths=(root,))
    )

    assert result.terminals[0].status == "detected_only"
    assert result.terminals[0].install_path == root


def test_invalid_manual_directory_is_reported_without_becoming_active(
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "empty"
    invalid.mkdir()

    result = LocalTerminalDiscovery(system_candidates=lambda: ()).inspect(
        LocalSourceSettings(tdx_install_paths=(invalid,))
    )

    assert result.terminals[0].status == "invalid"
    assert result.active_tdx_vipdoc is None
