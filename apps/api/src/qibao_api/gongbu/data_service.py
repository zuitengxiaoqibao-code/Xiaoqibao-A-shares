from datetime import datetime
from typing import Protocol

from qibao_api.contracts.bars import DailyBar, DataSourceState, SyncAttempt, SyncReport
from qibao_api.gongbu.tdx_history import DataSourceUnavailable


SOURCE_NAMES = {
    "eltdx": "通达信（eltdx）",
    "mootdx": "通达信",
    "baidu": "百度股市通",
}


class HistorySource(Protocol):
    def fetch_daily(self, symbol: str, limit: int) -> list[DailyBar]: ...


class BarStore(Protocol):
    def upsert(self, bars: list[DailyBar]) -> None: ...
    def export_parquet(self, symbol: str): ...


class FallbackHistorySource:
    def __init__(self, sources: list[HistorySource]) -> None:
        self.sources = sources
        self.last_attempts: tuple[SyncAttempt, ...] = ()

    def fetch_daily(self, symbol: str, limit: int = 250) -> list[DailyBar]:
        errors: list[str] = []
        attempts: list[SyncAttempt] = []
        for source in self.sources:
            source_name = _source_label(source)
            try:
                bars = source.fetch_daily(symbol, limit)
                if bars:
                    attempts.append(SyncAttempt(
                        source=bars[0].source,
                        status="ready",
                        message=f"返回 {len(bars)} 条日线",
                    ))
                    self.last_attempts = tuple(attempts)
                    return bars
                attempts.append(SyncAttempt(
                    source=source_name,
                    status="empty",
                    message="未返回日线",
                ))
            except Exception as error:
                message = str(error) or type(error).__name__
                attempts.append(SyncAttempt(
                    source=source_name,
                    status="error",
                    message=message,
                ))
                errors.append(f"{SOURCE_NAMES.get(source_name, source_name)}: {message}")
        self.last_attempts = tuple(attempts)
        raise DataSourceUnavailable("; ".join(errors) or "no history sources configured")


class MarketDataService:
    def __init__(self, source: HistorySource, repository: BarStore) -> None:
        self.source = source
        self.repository = repository

    def sync_symbol(self, symbol: str, limit: int = 250) -> SyncReport:
        started_at = datetime.now()
        attempts: tuple[SyncAttempt, ...] = ()
        try:
            bars = self.source.fetch_daily(symbol, limit)
            attempts = tuple(getattr(self.source, "last_attempts", ()))
            if not attempts:
                attempts = (SyncAttempt(
                    source=bars[0].source,
                    status="ready",
                    message=f"返回 {len(bars)} 条日线",
                ),)
            self.repository.upsert(bars)
            parquet_path = self.repository.export_parquet(symbol)
            return SyncReport(
                symbol=symbol,
                state=DataSourceState.READY,
                written_rows=len(bars),
                source=bars[0].source,
                parquet_path=str(parquet_path),
                started_at=started_at,
                finished_at=datetime.now(),
                message=(
                    f"已使用 {SOURCE_NAMES.get(bars[0].source, bars[0].source)}，备用链路完成"
                    if len(attempts) > 1 else "同步完成"
                ),
                attempts=attempts,
            )
        except Exception as error:
            attempts = tuple(getattr(self.source, "last_attempts", ()))
            if not attempts:
                attempts = (SyncAttempt(
                    source=_source_label(self.source),
                    status="error",
                    message=str(error) or type(error).__name__,
                ),)
            return SyncReport(
                symbol=symbol,
                state=DataSourceState.ERROR,
                written_rows=0,
                source="history-fallback",
                started_at=started_at,
                finished_at=datetime.now(),
                message=str(error),
                attempts=attempts,
            )


def _source_label(source: object) -> str:
    configured = getattr(source, "source_name", None)
    if configured:
        return str(configured)
    wrapped = getattr(source, "_source", None)
    if wrapped is not None:
        return _source_label(wrapped)
    return source.__class__.__name__
