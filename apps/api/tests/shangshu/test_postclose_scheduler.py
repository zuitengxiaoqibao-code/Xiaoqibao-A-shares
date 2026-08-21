from datetime import date, datetime, timezone

from qibao_api.a_shares.postclose_report import PostCloseReportBuilder


def test_postclose_report_has_stable_identity():
    report = PostCloseReportBuilder().freeze(date(2026, 8, 21), datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc), {"涨停": 10})
    assert report.report_id.startswith("postclose-")
