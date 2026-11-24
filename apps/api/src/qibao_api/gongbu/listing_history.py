import re
from datetime import date
from decimal import Decimal

import httpx

from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.gongbu.tdx_history import DataSourceUnavailable
from qibao_api.gongbu.tencent_quotes import market_prefix


class SinaListingDateSource:
    source_name = "sina"

    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def listing_date(self, symbol: str) -> date:
        validate_a_share_code(symbol)
        response = self.client.get(
            f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCI_CorpInfo/stockid/{symbol}.phtml",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=httpx.Timeout(8, connect=3),
        )
        response.raise_for_status()
        # The link carries both the security code and the listing month.
        matches = re.findall(r"stockid=" + re.escape(symbol) + r"&(?:amp;)?InMarketDate=(\d{6})[^>]*>(\d{4}-\d{2}-\d{2})</a>",
                             response.content.decode("gb18030", errors="replace"))
        if len(matches) != 1 or matches[0][0] != matches[0][1].replace("-", "")[:6]:
            raise DataSourceUnavailable("上市日期页面缺少匹配证券的有效证据")
        return date.fromisoformat(matches[0][1])

    def verify_history(self, symbol, bars, target_date, listing_date=None) -> bool:
        """Verify dates/OHLC independently; never invent or import turnover."""
        if not bars:
            return False
        response = self.client.get(
            "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData",
            params={"symbol": market_prefix(symbol) + symbol, "scale": "240", "ma": "no", "datalen": "400"},
            headers={"Referer": "https://finance.sina.com.cn/"}, timeout=httpx.Timeout(8, connect=3),
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            return False
        selected = {}
        for row in rows:
            day = date.fromisoformat(row["day"])
            if day > target_date:
                continue
            if day in selected:
                return False
            prices = {key: Decimal(row[key]) for key in ("open", "high", "low", "close")}
            if any(not value.is_finite() or value <= 0 for value in prices.values()):
                return False
            if (prices["high"] < max(prices["open"], prices["close"])
                    or prices["low"] > min(prices["open"], prices["close"])):
                return False
            selected[day] = prices
        if not selected or max(selected) != bars[-1].trade_date:
            return False
        if listing_date is not None and (min(selected) != listing_date or bars[0].trade_date != listing_date):
            return False
        local = {bar.trade_date: bar for bar in bars}
        remote_dates = {day for day in selected if day >= bars[0].trade_date}
        if set(local) != remote_dates:
            return False
        return all(abs(getattr(bar, key) - selected[day][key]) <= Decimal("0.0005")
                   for day, bar in local.items() for key in ("open", "high", "low", "close"))
