from datetime import date, datetime, timezone

import pytest

from qibao_api.a_shares.postclose_report import PostCloseReportBuilder, PostCloseReportRepository, PostCloseReportService


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


def test_repository_is_immutable_and_delivery_state_is_separate(tmp_path):
    builder = PostCloseReportBuilder()
    report = builder.freeze(date(2026, 8, 21), datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc), {"涨停": 10})
    repository = PostCloseReportRepository(tmp_path)
    repository.append(report)
    repository.record_delivery(report.report_id, "feishu", "failed", "网络连接失败")
    assert repository.latest(date(2026, 8, 21)) == report
    assert repository.delivery(report.report_id)["feishu"]["status"] == "failed"
    with pytest.raises(ValueError, match="不可覆盖"):
        repository.append(report)


def test_service_retry_reuses_frozen_facts(tmp_path):
    calls = 0
    def source(_date):
        nonlocal calls
        calls += 1
        return {"涨停": 10}
    service = PostCloseReportService(PostCloseReportRepository(tmp_path), source)
    now = datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)
    first = service.run(date(2026, 8, 21), now)
    second = service.run(date(2026, 8, 21), now)
    assert first == second
    assert calls == 1


def test_service_records_explicit_unconfigured_delivery_status(tmp_path):
    repository = PostCloseReportRepository(tmp_path)
    service = PostCloseReportService(
        repository,
        lambda _date: {"涨停": 10},
        delivery=lambda _report: "未配置",
    )

    report = service.run(
        date(2026, 8, 21), datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)
    )

    delivery = repository.delivery(report.report_id)
    assert delivery["feishu"]["status"] == "未配置"
    assert delivery["feishu"]["reason"] is None


def test_service_records_delivery_result_status_without_recollecting_facts(tmp_path):
    repository = PostCloseReportRepository(tmp_path)
    calls = 0

    def source(_date):
        nonlocal calls
        calls += 1
        return {"涨停": 10}

    service = PostCloseReportService(
        repository,
        source,
        delivery=lambda _report: type("Result", (), {"status": "sent"})(),
    )
    first = service.run(
        date(2026, 8, 21), datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)
    )
    second = service.run(
        date(2026, 8, 21), datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)
    )

    assert repository.delivery(first.report_id)["feishu"]["status"] == "sent"
    assert second == first
    assert calls == 1


def test_service_retries_delivery_without_recollecting_facts(tmp_path):
    repository = PostCloseReportRepository(tmp_path)
    calls = 0

    def source(_date):
        nonlocal calls
        calls += 1
        return {"涨停": 10}

    service = PostCloseReportService(
        repository,
        source,
        delivery=lambda _report: type("Result", (), {"status": "sent"})(),
    )
    report = service.run(
        date(2026, 8, 21), datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)
    )
    repository.record_delivery(report.report_id, "feishu", "failed", "首次失败")
    service.delivery = lambda _report: type("Result", (), {"status": "sent"})()

    result = service.retry_delivery(report.report_id)

    assert result == "sent"
    assert repository.delivery(report.report_id)["feishu"]["status"] == "sent"
    assert calls == 1
