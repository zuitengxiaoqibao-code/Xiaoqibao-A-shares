from datetime import date
from decimal import Decimal

import pandas as pd

from qibao_api.contracts.bars import DailyBar
from qibao_api.gongbu.tdx_client import SourceAttemptObserver


class DataSourceUnavailable(RuntimeError):
    pass


class TdxHistorySource:
    source_name = "mootdx"

    def __init__(
        self,
        client=None,
        *,
        client_factory=None,
        observer: SourceAttemptObserver | None = None,
    ) -> None:
        if (client is None) == (client_factory is None):
            raise ValueError("provide exactly one mootdx client or client factory")
        self.client = client
        self.client_factory = client_factory
        self.observer = observer

    def fetch_daily(self, symbol: str, limit: int = 250) -> list[DailyBar]:
        client = self.client_factory() if self.client_factory is not None else self.client
        if self.observer is not None and hasattr(client, "observer"):
            client.observer = self.observer
        try:
            frame = client.bars(
                symbol=symbol, frequency=9, start=0, offset=limit
            )
            if frame is None or frame.empty:
                raise DataSourceUnavailable("mootdx returned no daily bars")

            bars = [self._convert_row(symbol, row) for _, row in frame.iterrows()]
            return sorted(bars, key=lambda item: item.trade_date)
        finally:
            if self.client_factory is not None:
                close = getattr(client, "close", None)
                if callable(close):
                    close()

    @staticmethod
    def _convert_row(symbol: str, row: pd.Series) -> DailyBar:
        trade_date: date = pd.to_datetime(row["datetime"]).date()
        return DailyBar(
            symbol=symbol,
            trade_date=trade_date,
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
            volume=int(row["vol"]),
            amount=Decimal(str(row["amount"])),
            source="mootdx",
        )
