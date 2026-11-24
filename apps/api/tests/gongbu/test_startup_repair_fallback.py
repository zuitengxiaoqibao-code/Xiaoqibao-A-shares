from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

from qibao_api.gongbu.tdx_official_package import OfficialTdxPackageService


def coverage(*, complete=True, universe_count=5200):
    return SimpleNamespace(
        universe_count=universe_count, target_date=date(2026, 11, 18),
        dominant_trade_date=date(2026, 11, 18), dominant_date_coverage_percent=99.5,
        coverage_percent=99.5 if complete else 50, missing_history_count=0 if complete else 2400,
        quality="ready" if complete else "partial", blockers=() if complete else ("history_coverage_below_98_percent",),
    )


class OnlineHistory:
    def __init__(self, *, fail=False, complete=True):
        self.calls = []
        self.fail = fail
        self.complete = complete

    def default_target_date(self):
        return date(2026, 11, 18)

    def create_target_repair(self, target):
        self.calls.append(target)
        return SimpleNamespace(job_id="online", total_count=2, pending_count=2)

    def run(self, job_id, progress=None):
        if self.fail:
            raise httpx.ConnectError("offline")
        result = SimpleNamespace(total_count=2, ready_count=2, failed_count=0,
                                 skipped_count=0, pending_count=0, tdx_ready_count=0,
                                 baidu_ready_count=2)
        if progress:
            progress(result)
        return result

    def coverage(self, target):
        return coverage(complete=self.complete)


@pytest.mark.parametrize("failure_stage", ["metadata", "download"])
@pytest.mark.parametrize("complete", [True, False])
def test_official_failure_automatically_switches_to_online_and_verifies_result(tmp_path, failure_stage, complete):
    def handler(request):
        if request.url.path.endswith("_hsjdayinfo.js") and failure_stage == "download":
            return httpx.Response(200, text='window.HSJDAY_SOFT_SIZE="500MB";window.HSJDAY_SOFT_TIME="2026-11-18 16:00:00";')
        raise httpx.ReadTimeout("upstream timeout", request=request)

    history = OnlineHistory(complete=complete)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(cache_dir=tmp_path / "cache", state_path=tmp_path / "state.json",
                                            tdx_import_service=object(), history_service=history, client=client,
                                            clock=lambda: datetime(2026, 11, 19, tzinfo=timezone.utc))
        result = service.run(service.create_job().job_id)

    assert result.state == ("completed" if complete else "partial")
    assert result.percent == 100
    assert history.calls == [date(2026, 11, 18)]
    assert result.online_ready == 2
    attempts = {attempt.source: attempt for attempt in result.source_attempts}
    assert attempts["tdx_official"].state == "failed"
    assert "超时" in attempts["tdx_official"].detail
    assert attempts["baidu"].state == "completed"
    assert result.remaining_gap_count == (0 if complete else 2400)
    assert service.current_job() == result


def test_all_sources_unavailable_exposes_reasons_and_does_not_loop(tmp_path):
    history = OnlineHistory(fail=True)
    def handler(request):
        raise httpx.ConnectError("offline", request=request)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OfficialTdxPackageService(cache_dir=tmp_path / "cache", state_path=tmp_path / "state.json",
                                            tdx_import_service=object(), history_service=history, client=client)
        result = service.run(service.create_job().job_id)
    assert result.state == "failed"
    assert result.error_stage == "online_repair"
    assert "在线及后备" in result.error_detail
    assert len(history.calls) == 1
    assert all(attempt.state != "running" for attempt in result.source_attempts)


def test_universe_refresh_failure_is_retained_while_other_sources_are_tried(tmp_path):
    def unavailable():
        raise ValueError("证券目录来源不可用")
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as client:
        service = OfficialTdxPackageService(cache_dir=tmp_path / "cache", state_path=tmp_path / "state.json",
                                            tdx_import_service=object(), history_service=OnlineHistory(),
                                            prepare_universe=unavailable, client=client)
        result = service.run(service.create_job().job_id)
    attempt = next(item for item in result.source_attempts if item.source == "a_share_universe")
    assert attempt.state == "failed"
    assert "证券目录来源不可用" in attempt.detail
    assert result.online_ready == 2


def test_tiny_universe_cannot_pass_final_full_market_verification(tmp_path):
    history = OnlineHistory()
    history.coverage = lambda target: coverage(universe_count=1)
    service = OfficialTdxPackageService(cache_dir=tmp_path / "cache", state_path=tmp_path / "state.json",
                                        tdx_import_service=object(), history_service=history)
    try:
        result = service._final_review(service.create_job(), date(2026, 11, 18), latest_trade_date=None)
    finally:
        service.close()
    assert result.state == "partial"
    assert "证券目录数量不足" in result.result_detail


def test_concurrent_repair_clicks_create_only_one_job(tmp_path):
    service = OfficialTdxPackageService(cache_dir=tmp_path / "cache", state_path=tmp_path / "state.json", tdx_import_service=object())
    try:
        def create():
            try:
                return service.create_job()
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: create(), range(2)))
        assert sum(result is not None for result in results) == 1
    finally:
        service.close()
