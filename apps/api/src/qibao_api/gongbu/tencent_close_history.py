"""Completed-session snapshots; never substitute these for old historical bars."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import time as monotonic_time
from zoneinfo import ZoneInfo

import httpx

from qibao_api.contracts.bars import DailyBar
from qibao_api.gongbu.tencent_quotes import market_prefix


class TencentCloseHistorySource:
    def __init__(self, client: httpx.Client, *, clock=lambda: datetime.now(ZoneInfo("Asia/Shanghai"))):
        self.client = client
        self.clock = clock
        self._bars = {}
        self._unavailable = {}
        self._target_date = None

    def prefetch(self, symbols, target_date: date):
        now = self.clock().astimezone(ZoneInfo("Asia/Shanghai"))
        self._bars = {}
        self._unavailable = {}
        self._target_date = target_date
        if now.date() != target_date or now.time() < time(15, 5):
            return

        def batch(values, attempt=0):
            try:
                response = self.client.get("https://qt.gtimg.cn/q=" + ",".join(market_prefix(symbol) + symbol for symbol in values),
                                           headers={"Referer": "https://gu.qq.com/"}, timeout=httpx.Timeout(8, connect=3))
                response.raise_for_status()
                bars = []
                for line in response.content.decode("gb18030").splitlines():
                    try:
                        fields = line.split('="', 1)[1].rsplit('"', 1)[0].split("~")
                        observed = datetime.strptime(fields[30], "%Y%m%d%H%M%S")
                        if fields[2] not in values or observed.date() != target_date or observed.time() < time(15, 0):
                            continue
                        trade = fields[35].split("/")
                        if len(trade) != 3 or Decimal(trade[0]) != Decimal(fields[3]) or Decimal(trade[1]) != Decimal(fields[6]):
                            continue
                        if (len(fields) > 40 and fields[40] == "S" and Decimal(fields[6]) == 0
                                and all(Decimal(fields[index]) == 0 for index in (5, 33, 34))
                                and Decimal(trade[2]) == 0):
                            self._unavailable[fields[2]] = "目标日收盘快照标记停牌（S），成交量/额及开高低均为零；不伪造当日日线，保留缺口待复核"
                            continue
                        bars.append(DailyBar(symbol=fields[2], trade_date=target_date, open=Decimal(fields[5]),
                            high=Decimal(fields[33]), low=Decimal(fields[34]), close=Decimal(fields[3]),
                            volume=int(Decimal(fields[6]) * 100), amount=Decimal(trade[2]), source="tencent"))
                    except (ValueError, IndexError, InvalidOperation):
                        continue
                return bars
            except (httpx.HTTPError, UnicodeError):
                if attempt == 0:
                    monotonic_time.sleep(0.2)
                    return batch(values, attempt=1)
                return []

        batches = [symbols[offset:offset + 60] for offset in range(0, len(symbols), 60)]
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="close-quotes") as executor:
            for bars in executor.map(batch, batches):
                self._bars.update({bar.symbol: bar for bar in bars})

    def bar(self, symbol, target_date):
        value = self._bars.get(symbol)
        return value if value is not None and value.trade_date == target_date else None

    def bars(self):
        return tuple(self._bars.values())

    def unavailable_reason(self, symbol, target_date):
        return self._unavailable.get(symbol) if self._target_date == target_date else None
