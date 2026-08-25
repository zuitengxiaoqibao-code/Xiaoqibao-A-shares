from datetime import date, datetime, timezone
from pathlib import Path
import struct

from qibao_api.gongbu.tdx_directory_discovery import (
    TdxDirectoryCandidate,
    discover_tdx_directories,
    rank_tdx_directories,
)


DAY = struct.Struct("<IIIIIfII")


def _valid_day_bytes(trade_date: int) -> bytes:
    return DAY.pack(trade_date, 1000, 1100, 900, 1050, 1234.0, 100, 0)


def _candidate(root: Path, *, latest: str, readable: int, universe: int) -> TdxDirectoryCandidate:
    return TdxDirectoryCandidate(
        root=root,
        vipdoc_path=root / "vipdoc",
        display_name=root.name,
        version_hint=None,
        latest_trade_date=date.fromisoformat(f"{latest[:4]}-{latest[4:6]}-{latest[6:]}"),
        day_file_count=universe,
        readable_day_file_count=readable,
        a_share_coverage_percent=round(readable / universe * 100, 2),
        last_data_update=datetime(2026, 8, 25, tzinfo=timezone.utc),
        score=0,
        state="ready",
        reasons=(),
    )


def test_known_mock_directory_is_scanned_and_ranked_by_real_day_coverage(tmp_path):
    mock_root = tmp_path / "new_tdx_mock"
    vipdoc = mock_root / "vipdoc" / "sh" / "lday"
    vipdoc.mkdir(parents=True)
    (vipdoc / "sh600000.day").write_bytes(_valid_day_bytes(20260825))

    result = discover_tdx_directories(
        known_paths=(mock_root,),
        search_roots=(tmp_path,),
        universe_symbols=("600000",),
    )

    assert result.candidates[0].root == mock_root.resolve()
    assert result.candidates[0].latest_trade_date == date(2026, 8, 25)
    assert result.candidates[0].readable_day_file_count == 1
    assert result.candidates[0].a_share_coverage_percent == 100.0


def test_rank_prefers_newer_complete_directory_over_more_recent_but_incomplete(tmp_path):
    complete = _candidate(tmp_path / "complete", latest="20260824", readable=2, universe=2)
    incomplete = _candidate(tmp_path / "incomplete", latest="20260825", readable=1, universe=2)

    ranked = rank_tdx_directories((incomplete, complete))

    assert ranked[0].root == complete.root
    assert "覆盖率" in ranked[0].reasons[0] or "可读取" in ranked[0].reasons[0]
