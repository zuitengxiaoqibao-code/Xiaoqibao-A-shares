from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from qibao_api.a_shares.late_session_factor_cache import LateSessionFactorCache


def _bars():
    rows = [
        SimpleNamespace(close=Decimal("11"), volume=Decimal("200")),
        SimpleNamespace(close=Decimal("10"), volume=Decimal("100")),
    ]
    rows.extend(SimpleNamespace(close=Decimal("10"), volume=Decimal("100")) for _ in range(19))
    return rows


def test_factor_cache_reuses_same_universe_within_trading_day() -> None:
    cache = LateSessionFactorCache()
    calls = 0

    def loader(symbols):
        nonlocal calls
        calls += 1
        return {symbol: _bars() for symbol in symbols}

    first = cache.get_or_build(date(2026, 8, 18), ("600000", "000001"), loader)
    second = cache.get_or_build(date(2026, 8, 18), ("000001", "600000"), loader)

    assert calls == 1
    assert first is second
    assert first.factors["600000"].volume_baseline_5d == Decimal("100")
    assert first.factors["600000"].twenty_day_limit_up_count == 1


def test_factor_cache_rebuilds_for_new_trading_day() -> None:
    cache = LateSessionFactorCache()
    calls = 0

    def loader(symbols):
        nonlocal calls
        calls += 1
        return {symbol: _bars() for symbol in symbols}

    cache.get_or_build(date(2026, 8, 18), ("600000",), loader)
    cache.get_or_build(date(2026, 8, 19), ("600000",), loader)

    assert calls == 2
    assert cache.status()["builds"] == 2
    assert cache.status()["hits"] == 0
