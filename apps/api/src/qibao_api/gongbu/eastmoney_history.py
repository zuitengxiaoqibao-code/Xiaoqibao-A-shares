"""Unadjusted daily OHLC, volume (shares) and actual traded amount."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.gongbu.tdx_history import DataSourceUnavailable


class EastmoneyHistorySource:
    source_name = "eastmoney"

    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def listing_date(self, symbol: str) -> date:
        response = self.client.get("https://push2.eastmoney.com/api/qt/stock/get",
            params={"secid": f"{1 if symbol.startswith('6') else 0}.{symbol}", "fields": "f57,f189"},
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
            timeout=httpx.Timeout(8, connect=3))
        response.raise_for_status()
        data = response.json().get("data")
        if not isinstance(data, dict) or data.get("f57") != symbol:
            raise DataSourceUnavailable("上市日期证券校验失败")
        return datetime.strptime(str(data.get("f189")), "%Y%m%d").date()

    def fetch_daily(self, symbol: str, limit: int = 300) -> list[DailyBar]:
        validate_a_share_code(symbol)
        today = datetime.now(timezone.utc).date()
        # Request a bounded date window; the endpoint can ignore lmt with beg=0.
        response = self.client.get(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            params={"secid": f"{1 if symbol.startswith('6') else 0}.{symbol}",
                    "klt": "101", "fqt": "0", "lmt": str(limit),
                    "beg": (today - timedelta(days=max(900, limit * 3))).strftime("%Y%m%d"),
                    "end": today.strftime("%Y%m%d"),
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57"},
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"},
            timeout=httpx.Timeout(8, connect=3),
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if payload.get("rc") != 0 or not isinstance(data, dict) or data.get("code") != symbol:
            raise DataSourceUnavailable("东方财富未返回匹配证券的日线")
        rows = data.get("klines")
        if not isinstance(rows, list) or not rows:
            raise DataSourceUnavailable("东方财富未返回日线")
        bars = []
        seen = set()
        for row in rows:
            values = row.split(",")
            if len(values) < 7 or values[0] in seen:
                raise DataSourceUnavailable("东方财富日线字段或日期重复校验失败")
            seen.add(values[0])
            volume = Decimal(values[5]) * 100
            if volume != volume.to_integral_value():
                raise DataSourceUnavailable("东方财富成交量单位校验失败")
            bars.append(DailyBar(symbol=symbol, trade_date=values[0],
                                 open=Decimal(values[1]), close=Decimal(values[2]),
                                 high=Decimal(values[3]), low=Decimal(values[4]),
                                 volume=int(volume), amount=Decimal(values[6]), source=self.source_name))
        return sorted(bars, key=lambda bar: bar.trade_date)[-limit:]
