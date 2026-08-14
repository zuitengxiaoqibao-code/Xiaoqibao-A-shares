from datetime import date

from qibao_api.a_shares.quant_factor_cache import QuantFactorCache


def test_factor_cache_reuses_matching_history_and_invalidates_changes() -> None:
    cache = QuantFactorCache()
    calls = 0

    def compute():
        nonlocal calls
        calls += 1
        return {"call": calls}

    first = cache.get_or_compute(
        trading_date=date(2026, 8, 11),
        symbol="600001",
        factor_version="a-share-factors-v1",
        history_fingerprint="history-a",
        loader=compute,
    )
    reused = cache.get_or_compute(
        trading_date=date(2026, 8, 11),
        symbol="600001",
        factor_version="a-share-factors-v1",
        history_fingerprint="history-a",
        loader=compute,
    )
    changed = cache.get_or_compute(
        trading_date=date(2026, 8, 11),
        symbol="600001",
        factor_version="a-share-factors-v1",
        history_fingerprint="history-b",
        loader=compute,
    )

    assert first == reused == {"call": 1}
    assert changed == {"call": 2}
    assert calls == 2
