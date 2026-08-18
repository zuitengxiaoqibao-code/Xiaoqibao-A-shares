from __future__ import annotations


class RefreshPolicy:
    _LEVELS = {
        "index_minutes": 0,
        "current_stock": 0,
        "late_session_candidates": 1,
        "market_anomalies": 1,
        "news_events": 1,
        "market_cross_section": 2,
        "sector_strength": 2,
        "fund_flow": 2,
        "company_research": 3,
        "financials": 3,
        "backtest": 3,
    }
    _INTRADAY_VISIBLE = {0: 1_000, 1: 1_000, 2: 10_000, 3: None}
    _INTRADAY_HIDDEN = {0: 5_000, 1: 10_000, 2: 15_000, 3: None}
    _POST_CLOSE = {0: 60_000, 1: 60_000, 2: 300_000, 3: None}
    _OFF_SESSION = {0: 5_000, 1: 15_000, 2: 60_000, 3: None}

    def interval_ms(self, topic: str, *, phase: str, visible: bool) -> int | None:
        level = self._LEVELS.get(topic, 2)
        if phase == "intraday":
            return (self._INTRADAY_VISIBLE if visible else self._INTRADAY_HIDDEN)[level]
        if phase == "post_close":
            return self._POST_CLOSE[level]
        return self._OFF_SESSION[level]

