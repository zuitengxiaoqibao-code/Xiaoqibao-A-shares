import logging
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from mootdx.quotes import Quotes

from qibao_api.gongbu.tdx_client import TDX_SERVERS
from qibao_api.gongbu.tdx_local_overview import (
    TdxRealtimeQuote,
    build_market_statistics,
)
from qibao_api.gongbu.tencent_quotes import market_prefix


logger = logging.getLogger(__name__)
TENCENT_REALTIME_ENDPOINT = "https://qt.gtimg.cn/q="
MINIMUM_COMPLETE_A_SHARE_COUNT = 4_000
CHINA_TZ = ZoneInfo("Asia/Shanghai")


def _clean_name(value: object) -> str:
    return str(value or "").replace("\x00", "").strip()


def _is_a_share_symbol(symbol: str, market: int) -> bool:
    if len(symbol) != 6 or not symbol.isdigit():
        return False
    if market == 1:
        return symbol.startswith(("600", "601", "603", "605", "688", "689"))
    return symbol.startswith(("000", "001", "002", "003", "300", "301"))


class MootdxAShareCatalogSource:
    """Loads the full A-share symbol catalog in-process from TDX nodes."""

    def __init__(
        self,
        *,
        directory=None,
        servers: tuple[tuple[str, int], ...] = TDX_SERVERS,
        minimum_count: int = MINIMUM_COMPLETE_A_SHARE_COUNT,
        client_factory: Callable[..., Any] | None = None,
        vipdoc_root: Path | None = None,
    ) -> None:
        self.directory = directory
        self.servers = servers
        self.minimum_count = minimum_count
        self.client_factory = client_factory or self._create_client
        self.vipdoc_root = vipdoc_root
        self.last_source = "tdx-catalog"
        self._cached: tuple[tuple[str, str], ...] = ()

    @staticmethod
    def _create_client(server: tuple[str, int]):
        return Quotes.factory(
            market="std",
            server=server,
            timeout=3,
            auto_retry=False,
        )

    def load(self) -> tuple[tuple[str, str], ...]:
        if len(self._cached) >= self.minimum_count:
            return self._cached
        local_catalog = self._from_directory() if self.vipdoc_root is not None else ()
        if len(local_catalog) >= self.minimum_count:
            self.last_source = "local-tdx-vipdoc-catalog"
            self._cached = local_catalog
            return local_catalog
        errors: list[str] = []
        for server in self.servers:
            client = None
            try:
                client = self.client_factory(server=server)
                catalog = self._from_tdx_client(client)
                if len(catalog) >= self.minimum_count:
                    self.last_source = "tdx-catalog"
                    self._cached = catalog
                    return catalog
                errors.append(f"{server[0]}:{server[1]} count={len(catalog)}")
            except Exception as error:
                errors.append(f"{server[0]}:{server[1]} {type(error).__name__}")
            finally:
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass
        catalog = local_catalog or self._from_directory()
        if len(catalog) >= self.minimum_count:
            self.last_source = (
                "local-tdx-vipdoc-catalog"
                if self.vipdoc_root is not None
                else "local-a-share-directory"
            )
            self._cached = catalog
            return catalog
        raise OSError(
            "complete A-share catalog unavailable; "
            + "; ".join(errors)
            + f"; local-directory count={len(catalog)}"
        )

    @staticmethod
    def _from_tdx_client(client) -> tuple[tuple[str, str], ...]:
        catalog: dict[str, str] = {}
        for market in (0, 1):
            frame = client.stocks(market)
            if frame is None or bool(getattr(frame, "empty", True)):
                continue
            for row in frame.to_dict("records"):
                symbol = str(row.get("code") or "").strip()
                name = _clean_name(row.get("name"))
                if _is_a_share_symbol(symbol, market) and name:
                    catalog[symbol] = name
        return tuple(sorted(catalog.items()))

    def _from_directory(self) -> tuple[tuple[str, str], ...]:
        if self.directory is None:
            return ()
        local_symbols = self._vipdoc_symbols()
        result = []
        for symbol in self.directory.active_symbols():
            instrument = self.directory.resolve(symbol)
            if instrument is None:
                continue
            if getattr(instrument, "exchange", None) not in {"sh", "sz"}:
                continue
            if local_symbols is not None and symbol not in local_symbols:
                continue
            name = _clean_name(instrument.name)
            if name and name != symbol:
                result.append((symbol, name))
        return tuple(sorted(dict(result).items()))

    def _vipdoc_symbols(self) -> set[str] | None:
        if self.vipdoc_root is None:
            return None
        symbols = set()
        for exchange, market in (("sh", 1), ("sz", 0)):
            folder = self.vipdoc_root / exchange / "lday"
            for path in folder.glob("*.day"):
                filename = path.name.lower()
                symbol = filename[2:8]
                if (
                    len(filename) == 12
                    and filename.startswith(exchange)
                    and filename.endswith(".day")
                    and _is_a_share_symbol(symbol, market)
                ):
                    symbols.add(symbol)
        return symbols


def parse_tencent_realtime_quotes(
    raw: bytes,
    catalog: dict[str, str],
) -> tuple[TdxRealtimeQuote, ...]:
    try:
        text = raw.decode("gbk", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("Tencent realtime quotes are not valid GBK") from error
    quotes: dict[str, TdxRealtimeQuote] = {}
    for statement in text.split(";"):
        statement = statement.strip()
        if not statement.startswith("v_") or '="' not in statement:
            continue
        _key, payload = statement.split('="', 1)
        if not payload.endswith('"'):
            continue
        fields = payload[:-1].split("~")
        try:
            if len(fields) < 38:
                raise ValueError("incomplete quote")
            symbol = fields[2].strip()
            if symbol not in catalog:
                continue
            price = Decimal(fields[3])
            previous_close = Decimal(fields[4])
            opening = Decimal(fields[5])
            volume = Decimal(fields[6])
            high = Decimal(fields[33])
            low = Decimal(fields[34])
            amount_wan = Decimal(fields[37])
            observed_at = datetime.strptime(fields[30], "%Y%m%d%H%M%S").replace(
                tzinfo=CHINA_TZ
            )
            if min(price, previous_close, high, low) <= 0:
                raise ValueError("non-positive price")
            if volume < 0 or amount_wan < 0:
                raise ValueError("negative turnover")
        except (IndexError, InvalidOperation, ValueError):
            continue
        exchange = "SH" if market_prefix(symbol) == "sh" else "SZ"
        quotes[symbol] = TdxRealtimeQuote(
            symbol=symbol,
            exchange_code=f"{symbol}.{exchange}",
            name=_clean_name(fields[1]) or catalog[symbol],
            previous_close=previous_close,
            price=price,
            high=high,
            low=low,
            open=opening if opening > 0 else previous_close,
            volume=volume,
            amount_wan=amount_wan,
            observed_at=observed_at,
        )
    return tuple(quotes.values())


class SelfContainedOverviewProvider:
    """Builds a truthful full-market snapshot without an external local service."""

    def __init__(
        self,
        *,
        catalog_loader,
        client: httpx.Client,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        batch_size: int = 80,
        max_workers: int = 8,
        minimum_coverage: Decimal = Decimal("0.80"),
    ) -> None:
        if batch_size < 1 or max_workers < 1:
            raise ValueError("batch size and worker count must be positive")
        self.catalog_loader = catalog_loader
        self.client = client
        self.clock = clock
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.minimum_coverage = minimum_coverage

    def fetch(self):
        catalog = tuple(
            self.catalog_loader.load()
            if hasattr(self.catalog_loader, "load")
            else self.catalog_loader()
        )
        if not catalog:
            raise OSError("A-share catalog is empty")
        names = dict(catalog)
        chunks = tuple(self._chunks(tuple(names)))
        quotes: dict[str, TdxRealtimeQuote] = {}
        failures: list[str] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            pending = {
                executor.submit(self._fetch_batch, chunk, names): index
                for index, chunk in enumerate(chunks, start=1)
            }
            for future in as_completed(pending):
                try:
                    quotes.update({item.symbol: item for item in future.result()})
                except (OSError, ValueError, httpx.HTTPError) as error:
                    failures.append(f"batch-{pending[future]}:{type(error).__name__}")
        coverage = Decimal(len(quotes)) / Decimal(len(catalog))
        if coverage < self.minimum_coverage:
            raise OSError(
                f"Tencent full-market coverage too low: {len(quotes)}/{len(catalog)}; "
                + ",".join(failures[:8])
            )
        observed_at = max(
            (item.observed_at for item in quotes.values() if item.observed_at is not None),
            default=self.clock(),
        )
        catalog_source = getattr(self.catalog_loader, "last_source", "tdx-catalog")
        return build_market_statistics(
            quotes.values(),
            observed_at=observed_at,
            universe_count=len(catalog),
            source=f"tencent-realtime+{catalog_source}",
        )

    def _fetch_batch(
        self,
        symbols: tuple[str, ...],
        names: dict[str, str],
    ) -> tuple[TdxRealtimeQuote, ...]:
        instruments = tuple(f"{market_prefix(symbol)}{symbol}" for symbol in symbols)
        response = self.client.get(f"{TENCENT_REALTIME_ENDPOINT}{','.join(instruments)}")
        response.raise_for_status()
        return parse_tencent_realtime_quotes(
            response.content,
            {symbol: names[symbol] for symbol in symbols},
        )

    def _chunks(self, symbols: tuple[str, ...]) -> Iterable[tuple[str, ...]]:
        for start in range(0, len(symbols), self.batch_size):
            yield symbols[start:start + self.batch_size]
