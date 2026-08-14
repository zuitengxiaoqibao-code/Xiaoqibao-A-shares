from datetime import datetime, timezone
from pathlib import Path

from qibao_api.a_shares.instrument_directory import AShareInstrument, AShareInstrumentDirectory


NOW = datetime(2026, 8, 13, 1, 30, tzinfo=timezone.utc)


def item(symbol: str, name: str, **kwargs) -> AShareInstrument:
    return AShareInstrument(
        symbol=symbol,
        name=name,
        exchange="sh" if symbol.startswith("6") else "sz",
        observed_at=NOW,
        quote_quality="ready",
        **kwargs,
    )


def test_directory_search_uses_code_name_prefix_and_recorded_aliases(tmp_path: Path) -> None:
    directory = AShareInstrumentDirectory(tmp_path / "instruments.sqlite3")
    directory.observe_many([
        item("600519", "贵州茅台", short_name="茅台", search_aliases=("gzmt", "maotai")),
        item("000001", "平安银行", search_aliases=("payh",)),
    ])

    assert [row.symbol for row in directory.search("6005")] == ["600519"]
    assert [row.symbol for row in directory.search("贵州")] == ["600519"]
    assert [row.symbol for row in directory.search("gzmt")] == ["600519"]
    assert [row.symbol for row in directory.search("茅台")] == ["600519"]


def test_directory_snapshot_preserves_status_and_metadata(tmp_path: Path) -> None:
    directory = AShareInstrumentDirectory(tmp_path / "instruments.sqlite3")
    directory.observe_many([
        item(
            "600519", "贵州茅台", short_name="茅台", historical_names=("贵州茅台酒",),
            industry="白酒", sectors=("消费", "沪深300"), trading_status="active",
        ),
    ])

    snapshot = directory.snapshot()

    assert len(snapshot) == 1
    assert snapshot[0].industry == "白酒"
    assert snapshot[0].sectors == ("消费", "沪深300")
    assert snapshot[0].trading_status == "active"
