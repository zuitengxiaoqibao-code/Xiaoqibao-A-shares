from datetime import date

import pandas as pd
import pytest

from qibao_api.gongbu.tdx_history import DataSourceUnavailable, TdxHistorySource


class FakeClient:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame
        self.closed = False

    def bars(self, **kwargs) -> pd.DataFrame:
        assert kwargs == {"symbol": "600000", "frequency": 9, "start": 0, "offset": 20}
        return self.frame

    def close(self) -> None:
        self.closed = True


def test_history_source_converts_rows_to_sorted_daily_bars() -> None:
    frame = pd.DataFrame(
        [
            {"open": 9.1, "high": 9.8, "low": 9.0, "close": 9.5, "vol": 1000, "amount": 9500, "datetime": "2026-07-13"},
            {"open": 8.8, "high": 9.2, "low": 8.7, "close": 9.0, "vol": 900, "amount": 8100, "datetime": "2026-07-12"},
        ]
    )

    bars = TdxHistorySource(FakeClient(frame)).fetch_daily("600000", 20)

    assert [bar.trade_date for bar in bars] == [date(2026, 7, 12), date(2026, 7, 13)]
    assert bars[0].source == "mootdx"


def test_history_source_rejects_empty_result() -> None:
    with pytest.raises(DataSourceUnavailable, match="no daily bars"):
        TdxHistorySource(FakeClient(pd.DataFrame())).fetch_daily("600000", 20)


def test_history_source_factory_reconnects_and_closes_each_fetch() -> None:
    clients = []
    frame = pd.DataFrame(
        [{
            "open": 9.1, "high": 9.8, "low": 9.0, "close": 9.5,
            "vol": 1000, "amount": 9500, "datetime": "2026-07-13",
        }]
    )

    def factory():
        client = FakeClient(frame)
        clients.append(client)
        return client

    source = TdxHistorySource(client_factory=factory)
    source.fetch_daily("600000", 20)
    source.fetch_daily("600000", 20)

    assert len(clients) == 2
    assert all(client.closed for client in clients)


def test_history_source_factory_closes_client_after_empty_result() -> None:
    client = FakeClient(pd.DataFrame())
    source = TdxHistorySource(client_factory=lambda: client)

    with pytest.raises(DataSourceUnavailable, match="no daily bars"):
        source.fetch_daily("600000", 20)

    assert client.closed is True
