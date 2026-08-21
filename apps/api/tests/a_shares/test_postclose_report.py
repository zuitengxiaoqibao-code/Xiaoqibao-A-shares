from datetime import date, datetime, timezone

import pytest

from qibao_api.a_shares.postclose_report import PostCloseReportBuilder


def test_freeze_rejects_before_market_close_and_preserves_partial_facts():
    builder = PostCloseReportBuilder()
    with pytest.raises(ValueError, match="收盘前不能冻结"):
        builder.freeze(date(2026, 8, 21), datetime(2026, 8, 21, 6, 0, tzinfo=timezone.utc), {"涨停": 10})
    report = builder.freeze(date(2026, 8, 21), datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc), {"涨停": 10}, coverage=80)
    assert report.quality == "partial"
    assert report.facts["涨停"] == 10
    explained = builder.explain(report, ai_explanation=None)
    assert explained.ai_status == "unavailable"
    assert explained.facts == report.facts
