import hashlib
import json
import struct
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from qibao_api.contracts.market_sentiment import (
    MarketBreadthObservation,
    MarketFactorObservation,
)
from qibao_api.a_shares.market_sentiment import MarketSentimentFactorBuilder
from qibao_api.gongbu.tencent_market_sentiment import (
    MarketSentimentFetchResult,
    MarketSentimentSourceUnavailable,
    RawSentimentBatch,
)


TDX_DAY_RECORD = struct.Struct("<IIIIIfII")
BENCHMARK_FILES = {
    "sh000852.day": "000852",
    "sh000300.day": "000300",
    "sh511010.day": "511010",
}


@dataclass(frozen=True, slots=True)
class TdxLocalDailyBar:
    symbol: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal
    source: str = "tdx-local-day"


def discover_tdx_vipdoc(explicit_home: Path | None = None) -> Path | None:
    if explicit_home is None:
        return None
    candidates = (explicit_home / "vipdoc", explicit_home)
    return next(
        (
            candidate
            for candidate in candidates
            if (candidate / "sh" / "lday").is_dir()
            and (candidate / "sz" / "lday").is_dir()
        ),
        None,
    )


def read_tdx_day_bars(
    path: Path,
    *,
    symbol: str,
    as_of: date,
    limit: int | None = 252,
    start_date: date | None = None,
) -> tuple[TdxLocalDailyBar, ...]:
    try:
        size = path.stat().st_size
        record_count = size // TDX_DAY_RECORD.size
        first_record = 0 if start_date is not None else max(0, record_count - max(limit * 2, limit or 0))
        with path.open("rb") as handle:
            handle.seek(first_record * TDX_DAY_RECORD.size)
            content = handle.read()
    except OSError:
        return ()
    rows = []
    for offset in range(0, len(content) - TDX_DAY_RECORD.size + 1, TDX_DAY_RECORD.size):
        raw_date, opening, high, low, close, amount, volume, _reserved = (
            TDX_DAY_RECORD.unpack_from(content, offset)
        )
        try:
            trade_date = date(raw_date // 10000, raw_date // 100 % 100, raw_date % 100)
            if trade_date > as_of or (start_date is not None and trade_date < start_date) or min(opening, high, low, close) <= 0:
                continue
            rows.append(TdxLocalDailyBar(
                symbol=symbol,
                trade_date=trade_date,
                open=Decimal(opening) / Decimal("100"),
                high=Decimal(high) / Decimal("100"),
                low=Decimal(low) / Decimal("100"),
                close=Decimal(close) / Decimal("100"),
                volume=volume,
                amount=Decimal(str(amount)),
            ))
        except (ValueError, OverflowError):
            continue
    return tuple(rows[-limit:]) if limit is not None else tuple(rows)


def _a_share_symbol(path: Path) -> str | None:
    name = path.name.lower()
    if name in BENCHMARK_FILES:
        return BENCHMARK_FILES[name]
    if len(name) != 12 or not name[2:8].isdigit() or not name.endswith(".day"):
        return None
    symbol = name[2:8]
    if name.startswith("sh") and symbol.startswith(("600", "601", "603", "605", "688", "689")):
        return symbol
    if name.startswith("sz") and symbol.startswith(("000", "001", "002", "003", "300", "301")):
        return symbol
    return None


def load_tdx_daily_histories(
    vipdoc_root: Path,
    *,
    as_of: date,
    limit: int | None = 252,
    start_date: date | None = None,
    max_workers: int = 12,
    stop_requested: Callable[[], bool] | None = None,
) -> dict[str, tuple[TdxLocalDailyBar, ...]]:
    should_stop = stop_requested or (lambda: False)
    paths = tuple(
        path
        for exchange in ("sh", "sz")
        for path in (vipdoc_root / exchange / "lday").glob("*.day")
        if _a_share_symbol(path) is not None
    )

    def read(path: Path) -> tuple[str, tuple[TdxLocalDailyBar, ...]] | None:
        if should_stop():
            return None
        symbol = _a_share_symbol(path)
        if symbol is None:
            return None
        bars = read_tdx_day_bars(
            path,
            symbol=symbol,
            as_of=as_of,
            limit=limit,
            start_date=start_date,
        )
        return (symbol, bars) if bars else None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        rows = tuple(item for item in executor.map(read, paths) if item is not None)
    histories = {symbol: bars for symbol, bars in rows}
    for filename, symbol in BENCHMARK_FILES.items():
        if should_stop():
            break
        path = vipdoc_root / "sh" / "lday" / filename
        if path.exists():
            bars = read_tdx_day_bars(
                path,
                symbol=symbol,
                as_of=as_of,
                limit=limit,
                start_date=start_date,
            )
            if bars:
                histories[symbol] = bars
    return histories


class LocalTdxDailyFactorBuilder:
    def __init__(
        self,
        *,
        vipdoc_root: Path,
        overview_source,
        cache_path: Path | None = None,
    ) -> None:
        self.vipdoc_root = vipdoc_root
        self.overview_source = overview_source
        self.cache_path = cache_path
        self._cached_date: date | None = None
        self._cached_factors: MarketFactorObservation | None = None
        self._cached_baseline_wan: Decimal | None = None

    def build(self, *, as_of: date, cutoff: datetime | None = None):
        factors, baseline_wan = self._base_factors(as_of)
        snapshot = self.overview_source.current()
        relative_amount = self._relative_amount(baseline_wan, snapshot, cutoff)
        evidence = tuple(dict.fromkeys((*factors.evidence_ids, "tdx-local-day")))
        return factors.model_copy(update={
            "relative_amount": relative_amount,
            "evidence_ids": evidence,
        })

    def _base_factors(
        self,
        as_of: date,
    ) -> tuple[MarketFactorObservation, Decimal | None]:
        if self._cached_date == as_of and self._cached_factors is not None:
            return self._cached_factors, self._cached_baseline_wan
        cached = self._load_cache(as_of)
        if cached is not None:
            factors, baseline_wan = cached
        else:
            histories = load_tdx_daily_histories(self.vipdoc_root, as_of=as_of)
            factors = MarketSentimentFactorBuilder.from_histories(histories)
            baseline_wan = self._baseline_amount_wan(histories, as_of)
            self._save_cache(as_of, factors, baseline_wan)
        self._cached_date = as_of
        self._cached_factors = factors
        self._cached_baseline_wan = baseline_wan
        return factors, baseline_wan

    @staticmethod
    def _baseline_amount_wan(histories, as_of: date) -> Decimal | None:
        daily_totals: dict[date, Decimal] = {}
        for symbol, bars in histories.items():
            if symbol in MarketSentimentFactorBuilder.BENCHMARK_SYMBOLS:
                continue
            for bar in bars[-21:]:
                if bar.trade_date >= as_of:
                    continue
                daily_totals[bar.trade_date] = daily_totals.get(
                    bar.trade_date, Decimal()
                ) + bar.amount
        values = [amount for _day, amount in sorted(daily_totals.items())][-20:]
        if not values:
            return None
        return sum(values, Decimal()) / Decimal(len(values)) / Decimal("10000")

    @staticmethod
    def _relative_amount(
        baseline_wan: Decimal | None,
        snapshot,
        cutoff: datetime | None,
    ) -> Decimal | None:
        if (
            snapshot is None
            or snapshot.liquidity.total_amount_yi is None
            or cutoff is None
            or baseline_wan is None
        ):
            return None
        progress = LocalTdxDailyFactorBuilder._session_progress(cutoff)
        if baseline_wan <= 0 or progress <= 0:
            return None
        expected_wan = baseline_wan * progress
        current_wan = snapshot.liquidity.total_amount_yi * Decimal("10000")
        return (current_wan / expected_wan).quantize(Decimal("0.0001"))

    def _load_cache(
        self,
        as_of: date,
    ) -> tuple[MarketFactorObservation, Decimal | None] | None:
        if self.cache_path is None or not self.cache_path.exists():
            return None
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if payload.get("as_of") != as_of.isoformat():
                return None
            factors = MarketFactorObservation.model_validate(payload["factors"])
            baseline = payload.get("baseline_amount_wan")
            return factors, Decimal(baseline) if baseline is not None else None
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _save_cache(
        self,
        as_of: date,
        factors: MarketFactorObservation,
        baseline_wan: Decimal | None,
    ) -> None:
        if self.cache_path is None:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        payload = {
            "as_of": as_of.isoformat(),
            "baseline_amount_wan": str(baseline_wan) if baseline_wan is not None else None,
            "factors": factors.model_dump(mode="json"),
        }
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            temporary.replace(self.cache_path)
        except OSError:
            return

    @staticmethod
    def _session_progress(cutoff: datetime) -> Decimal:
        local = cutoff.astimezone()
        minutes = local.hour * 60 + local.minute
        if minutes < 570:
            return Decimal()
        if minutes <= 690:
            elapsed = minutes - 570
        elif minutes < 780:
            elapsed = 120
        elif minutes <= 900:
            elapsed = 120 + minutes - 780
        else:
            elapsed = 240
        return Decimal(max(1, elapsed)) / Decimal("240")


class LocalTdxMarketSentimentSource:
    def __init__(self, *, overview_source) -> None:
        self.overview_source = overview_source

    def fetch(self, *, cutoff: datetime) -> MarketSentimentFetchResult:
        snapshot = self.overview_source.current()
        if snapshot is None or snapshot.quote_count == 0:
            raise MarketSentimentSourceUnavailable(
                "local TDX realtime overview is still warming up"
            )
        observed_at = min(snapshot.observed_at, cutoff)
        content = json.dumps({
            "observed_at": observed_at.isoformat(),
            "quote_count": snapshot.quote_count,
            "universe_count": snapshot.universe_count,
            "breadth": snapshot.breadth.model_dump(mode="json"),
            "limit_ecology": snapshot.limit_ecology.model_dump(mode="json"),
            "total_amount_yi": str(snapshot.liquidity.total_amount_yi),
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        snapshot_id = f"tdx-local-market-{digest[:24]}"
        observation = MarketBreadthObservation(
            requested_count=snapshot.universe_count,
            valid_count=snapshot.quote_count,
            rising_count=snapshot.breadth.rising_count,
            falling_count=snapshot.breadth.falling_count,
            flat_count=snapshot.breadth.flat_count,
            median_change_percent=snapshot.median_change_percent,
            total_amount_wan=(
                snapshot.liquidity.total_amount_yi * Decimal("10000")
                if snapshot.liquidity.total_amount_yi is not None else None
            ),
            limit_up_count=snapshot.limit_ecology.limit_up_count,
            limit_down_count=snapshot.limit_ecology.limit_down_count,
            broken_limit_up_count=snapshot.limit_ecology.broken_limit_up_count,
            max_limit_streak=None,
            observed_at=observed_at,
            fetched_at=cutoff,
            source_snapshot_ids=(snapshot_id,),
        )
        return MarketSentimentFetchResult(
            observation=observation,
            raw_batches=(RawSentimentBatch(
                snapshot_id=snapshot_id,
                requested_symbols=(),
                valid_count=snapshot.quote_count,
                fetched_at=cutoff,
                content_sha256=digest,
                content=content,
            ),),
        )
