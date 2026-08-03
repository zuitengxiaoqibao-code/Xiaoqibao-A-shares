import json
import threading
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import httpx

from qibao_api.contracts.market_review import DragonTigerSeat, DragonTigerStock


HUNDRED_MILLION = Decimal("100000000")
EASTMONEY_DATA_CENTER = "https://datacenter-web.eastmoney.com/api/data/v1/get"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _rows(raw_payload: bytes) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw_payload.decode("utf-8"))
        result = payload.get("result")
        rows = result.get("data") if isinstance(result, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
        raise ValueError("Eastmoney market review response is invalid") from exc
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ValueError("Eastmoney market review response is invalid")
    return [row for row in rows if isinstance(row, dict)]


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal()


def _yi(value: Any) -> Decimal:
    return (_decimal(value) / HUNDRED_MILLION).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _date(value: Any) -> date:
    return date.fromisoformat(str(value or "")[:10])


def parse_dragon_tiger_details(
    raw_payload: bytes,
    *,
    observed_at: datetime,
) -> tuple[DragonTigerStock, ...]:
    del observed_at
    result = []
    for row in _rows(raw_payload):
        symbol = str(row.get("SECURITY_CODE") or "")
        name = str(row.get("SECURITY_NAME_ABBR") or "").strip()
        reason = str(row.get("EXPLANATION") or row.get("EXPLAIN") or "").strip()
        try:
            result.append(DragonTigerStock(
                symbol=symbol,
                name=name,
                trade_date=_date(row.get("TRADE_DATE")),
                reason=reason,
                change_percent=_decimal(row.get("CHANGE_RATE")),
                buy_amount_yi=_yi(row.get("BILLBOARD_BUY_AMT")),
                sell_amount_yi=_yi(row.get("BILLBOARD_SELL_AMT")),
                net_amount_yi=_yi(row.get("BILLBOARD_NET_AMT")),
            ))
        except (ValueError, TypeError):
            continue
    return tuple(result)


def parse_dragon_tiger_seats(
    raw_payload: bytes,
    *,
    observed_at: datetime,
) -> tuple[DragonTigerSeat, ...]:
    del observed_at
    result = []
    for row in _rows(raw_payload):
        buy = _yi(row.get("BUY"))
        sell = _yi(row.get("SELL"))
        net = _yi(row.get("NET"))
        direction = "buy" if net > 0 else "sell" if net < 0 else "mixed"
        try:
            result.append(DragonTigerSeat(
                symbol=str(row.get("SECURITY_CODE") or ""),
                trade_date=_date(row.get("TRADE_DATE")),
                seat_name=str(row.get("OPERATEDEPT_NAME") or "").strip(),
                direction=direction,
                buy_amount_yi=buy,
                sell_amount_yi=sell,
                net_amount_yi=net,
            ))
        except (ValueError, TypeError):
            continue
    return tuple(result)


class EastmoneyDragonTigerSource:
    def __init__(
        self,
        *,
        cache_path: Path,
        client: httpx.Client | None = None,
        max_stocks: int = 30,
    ) -> None:
        self.cache_path = cache_path
        self.client = client or httpx.Client(timeout=6)
        self._owns_client = client is None
        self.max_stocks = max_stocks
        self._request_lock = threading.Lock()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def fetch(self, *, as_of: date, observed_at: datetime) -> tuple[DragonTigerStock, ...]:
        try:
            details = parse_dragon_tiger_details(
                self._request({
                    "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                    "columns": "ALL",
                    "filter": f"(TRADE_DATE<='{as_of.isoformat()}')",
                    "sortColumns": "TRADE_DATE,SECURITY_CODE",
                    "sortTypes": "-1,1",
                    "pageNumber": "1",
                    "pageSize": "200",
                    "source": "WEB",
                    "client": "WEB",
                }),
                observed_at=observed_at,
            )
            if not details:
                raise ValueError("Eastmoney Dragon Tiger list is empty")
            latest = max(item.trade_date for item in details)
            details = tuple(item for item in details if item.trade_date == latest)[:self.max_stocks]
            seats_by_symbol = self._fetch_all_seats(latest, observed_at=observed_at)
            enriched = []
            for item in details:
                enriched.append(item.model_copy(update={
                    "seats": seats_by_symbol.get(item.symbol, ()),
                }))
            result = tuple(enriched)
            self._save_cache(result, observed_at)
            return result
        except (httpx.HTTPError, OSError, ValueError):
            return self._load_cache()

    def _fetch_all_seats(
        self,
        trade_date: date,
        *,
        observed_at: datetime,
    ) -> dict[str, tuple[DragonTigerSeat, ...]]:
        rows = []
        filter_value = f"(TRADE_DATE='{trade_date.isoformat()}')"
        for report in ("RPT_BILLBOARD_DAILYDETAILSBUY", "RPT_BILLBOARD_DAILYDETAILSSELL"):
            try:
                raw = self._request({
                    "reportName": report,
                    "columns": "ALL",
                    "filter": filter_value,
                    "sortColumns": "NET",
                    "sortTypes": "-1",
                    "pageNumber": "1",
                    "pageSize": "500",
                    "source": "WEB",
                    "client": "WEB",
                })
                rows.extend(parse_dragon_tiger_seats(raw, observed_at=observed_at))
            except (httpx.HTTPError, OSError, ValueError):
                continue
        unique = {}
        for row in rows:
            key = (row.seat_name, row.buy_amount_yi, row.sell_amount_yi, row.net_amount_yi)
            unique[key] = row
        grouped: dict[str, list[DragonTigerSeat]] = {}
        for row in unique.values():
            grouped.setdefault(row.symbol, []).append(row)
        return {symbol: tuple(items) for symbol, items in grouped.items()}

    def _request(self, params: dict[str, str]) -> bytes:
        with self._request_lock:
            response = self.client.get(
                EASTMONEY_DATA_CENTER,
                params=params,
                headers={"User-Agent": USER_AGENT, "Referer": "https://data.eastmoney.com/"},
            )
        response.raise_for_status()
        return response.content

    def _save_cache(
        self,
        rows: tuple[DragonTigerStock, ...],
        observed_at: datetime,
    ) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        payload = {
            "observed_at": observed_at.isoformat(),
            "rows": [item.model_dump(mode="json") for item in rows],
        }
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.replace(self.cache_path)

    def _load_cache(self) -> tuple[DragonTigerStock, ...]:
        if not self.cache_path.exists():
            return ()
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return tuple(DragonTigerStock.model_validate(item) for item in payload.get("rows", []))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return ()
