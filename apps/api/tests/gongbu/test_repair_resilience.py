from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from threading import Barrier, Lock
from types import SimpleNamespace

import httpx
import pytest

from qibao_api.gongbu.eastmoney_history import EastmoneyHistorySource
from qibao_api.gongbu.listing_history import SinaListingDateSource
from qibao_api.gongbu.tdx_official_package import OfficialTdxPackageService
from tests.gongbu.test_full_market_history import bars, service, Source, TARGET


def test_eastmoney_unadjusted_units_amount_and_identity():
    def handler(request):
        assert request.url.params["fqt"] == "0"
        return httpx.Response(200, json={"rc": 0, "data": {"code": "600000", "klines": [
            "2026-07-24,10,10.2,10.3,9.9,1234,1256789.12"]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = EastmoneyHistorySource(client).fetch_daily("600000")
    assert result[0].volume == 123400
    assert str(result[0].amount) == "1256789.12"
    assert result[0].source == "eastmoney"


@pytest.mark.parametrize("row", ["2026-07-24,10,10,9,8,100,1000", "2026-07-24,10,10,11,9,-1,1000"])
def test_invalid_ohlc_or_volume_is_rejected(row):
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"rc": 0, "data": {"code": "600000", "klines": [row]}}))) as client:
        with pytest.raises(ValueError):
            EastmoneyHistorySource(client).fetch_daily("600000")


def test_listing_date_requires_security_and_consistent_month():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text='<a href="?stockid=001232&InMarketDate=202608">2026-08-04</a>'))) as client:
        source = SinaListingDateSource(client)
        assert source.listing_date("001232") == date(2026, 8, 4)
        with pytest.raises(RuntimeError):
            source.listing_date("600000")


def test_comprehensive_repair_does_not_abandon_symbols_after_first_failures(tmp_path):
    symbols = ("000001", "000002", "600000", "600001")
    value = service(tmp_path, symbols=symbols, coverage={}, tdx=Source({s: OSError("offline") for s in symbols}), baidu=Source({s: OSError("offline") for s in symbols}), threshold=2)
    value.max_workers = 4
    job = value.run(value.create_backfill().job_id, comprehensive=True)
    assert job.state == "completed"
    assert job.failed_count == 4
    assert job.pending_count == 0
    assert all(item.error_detail == "offline" for item in value.jobs.items(job.job_id))


def test_comprehensive_network_work_overlaps_and_every_symbol_runs_once(tmp_path):
    symbols = ("000001", "000002", "600000", "600001")
    barrier = Barrier(4)
    class ConcurrentSource(Source):
        def fetch_daily(self, symbol, limit):
            barrier.wait(timeout=5)
            return super().fetch_daily(symbol, limit)
    source = ConcurrentSource({s: bars(s, 300) for s in symbols})
    value = service(tmp_path, symbols=symbols, coverage={}, tdx=source, baidu=Source({}))
    value.max_workers = 4
    job = value.run(value.create_backfill().job_id, comprehensive=True)
    assert job.ready_count == 4
    assert sorted(s for s, _ in source.calls) == sorted(symbols)
    assert len(value.jobs.repair_audits()) == 1


def test_transient_independent_source_retries_before_original_fallbacks(tmp_path):
    source = Source({"600000": bars("600000", 300, source="eastmoney")})
    original = source.fetch_daily
    calls = []
    def fetch(symbol, limit):
        calls.append(symbol)
        if len(calls) == 1:
            raise httpx.ReadTimeout("temporary")
        return original(symbol, limit)
    source.fetch_daily = fetch
    value = service(tmp_path, symbols=("600000",), coverage={}, tdx=Source({}), baidu=Source({}))
    value.fallback_sources = (("eastmoney", source),)
    result = value.run(value.create_backfill().job_id, comprehensive=True)
    assert result.eastmoney_ready_count == 1
    assert len(calls) == 2
    assert not value.tdx_source.calls


@pytest.mark.parametrize("missing", [False, True])
def test_new_listing_requires_independent_date_and_every_session(tmp_path, missing):
    value = service(tmp_path, symbols=("600000",), coverage={"600000": (3, TARGET)}, tdx=Source({}), baidu=Source({}))
    values = bars("600000", 3)
    value.listing_date_source = SimpleNamespace(listing_date=lambda symbol: values[0].trade_date)
    value.bar_repository.trade_dates = lambda limit: [item.trade_date for item in values]
    verified = value._confirm_new_listing("600000", values[1:] if missing else values, TARGET)
    assert verified is not missing
    coverage = value.coverage(TARGET)
    assert coverage.eligible_count == 0
    assert coverage.new_listing_complete_count == (0 if missing else 1)
    assert coverage.coverage_percent == (0 if missing else 100)


def test_phase_eta_uses_current_stage_counts_and_resets_for_next_stage(tmp_path):
    now = [datetime(2026, 11, 19, tzinfo=timezone.utc)]
    value = OfficialTdxPackageService(cache_dir=tmp_path / "cache", state_path=tmp_path / "state.json", tdx_import_service=object(), clock=lambda: now[0])
    try:
        job = value._update(value.create_job(), state="running", stage="importing", processed_files=0, total_import_files=100)
        now[0] += timedelta(seconds=10)
        job = value._update(job, processed_files=20)
        assert job.phase_percent == 20
        assert job.phase_eta_seconds == 40
        now[0] += timedelta(seconds=1)
        job = value._update(job, stage="online_repair", online_total=10, online_pending=10)
        assert job.phase_percent == 0
        assert job.phase_eta_seconds is None
        assert job.phase_start_count == 0
    finally:
        value.close()


@pytest.mark.asyncio
async def test_current_universe_requires_all_unique_pages_and_retries(tmp_path, monkeypatch):
    from qibao_api.gongbu import a_share_universe as module
    monkeypatch.setattr(module, "MINIMUM_COMPLETE_A_SHARE_UNIVERSE_COUNT", 2)
    attempts = []
    def handler(request):
        if request.url.path.endswith("getHQNodeStockCount"):
            return httpx.Response(200, json="2")
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=[{"symbol": "sz000001", "code": "000001", "name": "平安银行"},
                                         {"symbol": "sh600000", "code": "600000", "name": "浦发银行"}])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        values = await module.SinaAShareUniverseSource(client).fetch()
    assert len(values) == 2
    assert len(attempts) == 2
    assert all(value.trading_status == "active" for value in values)


def test_old_directory_items_do_not_remain_pending_or_failed(tmp_path):
    value = service(tmp_path, symbols=("000001", "600000"), coverage={}, tdx=Source({}), baidu=Source({}))
    job = value.create_backfill()
    value.jobs.complete_item(job.job_id, "000001", state="failed", source=None, written_rows=0, error_code="OSError")
    value.jobs.restrict_to_gaps(job.job_id, ("600000",))
    assert value.jobs.get(job.job_id).failed_count == 0
    assert value.jobs.get(job.job_id).pending_count == 1
    assert value.jobs.get(job.job_id).skipped_count == 1


@pytest.mark.parametrize("observed,target,expected", [("20260724150100", TARGET, 1), ("20260724145959", TARGET, 0), ("20260723150100", TARGET, 0)])
def test_closing_snapshot_requires_closed_matching_day_and_actual_amount(observed, target, expected):
    from zoneinfo import ZoneInfo
    from qibao_api.gongbu.tencent_close_history import TencentCloseHistorySource
    fields = [""] * 50
    for index, value in {2: "600000", 3: "10", 5: "9.8", 6: "123", 30: observed,
                         33: "10.2", 34: "9.7", 35: "10/123/123456.78"}.items():
        fields[index] = value
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=('v_sh600000="' + "~".join(fields) + '";').encode()))) as client:
        source = TencentCloseHistorySource(client, clock=lambda: datetime(2026, 7, 24, 15, 6, tzinfo=ZoneInfo("Asia/Shanghai")))
        source.prefetch(("600000",), target)
    assert len(source.bars()) == expected
    if expected:
        assert source.bar("600000", TARGET).volume == 12300
        assert str(source.bar("600000", TARGET).amount) == "123456.78"
        assert source.bar("600000", TARGET - timedelta(days=1)) is None


def test_bulk_missing_daily_slice_deduplicates_without_superseding_existing(tmp_path):
    from qibao_api.storage.bar_repository import BarRepository
    repo = BarRepository(tmp_path / "bars.duckdb", tmp_path / "parquet")
    first = bars("600000", 1)
    second = bars("000001", 1)
    repo.upsert(first)
    assert repo.append_missing_batch(first + second + second) == 1
    assert repo.append_missing_batch(first + second) == 0
    assert len(repo.latest("600000")) == 1
    assert len(repo.latest("000001")) == 1


def test_old_or_incomplete_primary_response_continues_to_independent_fallback(tmp_path):
    value = service(tmp_path, symbols=("600000",), coverage={},
                    tdx=Source({"600000": bars("600000", 300)}), baidu=Source({}))
    value.fallback_sources = (("eastmoney", Source({"600000": bars("600000", 2)})),)
    result = value.run(value.create_backfill().job_id, comprehensive=True)
    assert result.tdx_ready_count == 1
    assert result.eastmoney_ready_count == 0
    assert len(value.bar_repository.writes) == 300


def test_retry_keeps_committed_rows_and_clears_outdated_failure_detail(tmp_path):
    value = service(tmp_path, symbols=("600000",), coverage={}, tdx=Source({}), baidu=Source({}))
    job = value.create_backfill()
    value.jobs.complete_item(job.job_id, "600000", state="failed", source=None,
                             written_rows=1, error_code="OSError", error_detail="old failure")
    value.jobs.finish(job.job_id)
    value.jobs.retry_failed(job.job_id)
    item = value.jobs.items(job.job_id)[0]
    assert item.written_rows == 1
    assert item.error_detail is None


def test_suspended_snapshot_reports_reason_without_manufacturing_daily_bar():
    from zoneinfo import ZoneInfo
    from qibao_api.gongbu.tencent_close_history import TencentCloseHistorySource
    fields = [""] * 50
    for index, value in {2: "600000", 3: "10", 5: "0", 6: "0", 30: "20260724150100",
                         33: "0", 34: "0", 35: "10/0/0", 40: "S"}.items():
        fields[index] = value
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text='v_sh600000="' + "~".join(fields) + '";'))) as client:
        source = TencentCloseHistorySource(client, clock=lambda: datetime(2026, 7, 24, 15, 6, tzinfo=ZoneInfo("Asia/Shanghai")))
        source.prefetch(("600000",), TARGET)
        assert source.bars() == ()
        assert "停牌" in source.unavailable_reason("600000", TARGET)


def test_automatic_second_pass_only_retries_failures_and_preserves_writes(tmp_path):
    now = datetime(2026, 11, 19, tzinfo=timezone.utc)
    completed = SimpleNamespace(job_id="sync", total_count=2, pending_count=0, ready_count=1,
        failed_count=1, skipped_count=0, tdx_ready_count=1, baidu_ready_count=0, pause_requested=False)
    history = SimpleNamespace(fallback_sources=(("eastmoney", object()),),
        create_target_repair=lambda target: completed)
    calls = []
    def run(job_id, progress, comprehensive):
        calls.append((job_id, comprehensive))
        if len(calls) == 2:
            completed.failed_count = 0
            completed.ready_count = 2
        progress(completed)
        return completed
    history.run = run
    retries = []
    history.retry_failed = lambda job_id: retries.append(job_id)
    value = OfficialTdxPackageService(cache_dir=tmp_path / "cache", state_path=tmp_path / "state.json",
        tdx_import_service=object(), history_service=history, clock=lambda: now)
    try:
        job = value._run_online_repair(value.create_job(), TARGET)
        assert len(calls) == 2
        assert retries == ["sync"]
        assert job.online_failed == 0
        assert job.online_ready == 2
    finally:
        value.close()


@pytest.mark.parametrize("missing,changed,expected", [(False,False,True), (True,False,False), (False,True,False)])
def test_independent_history_verification_requires_all_actual_dates_and_matching_prices(missing, changed, expected):
    values = bars("600000", 4)
    # An exchange session without a security bar can be acknowledged only
    # when an independent full history agrees on every remaining date/price.
    values.pop(1)
    rows = [{"day": bar.trade_date.isoformat(), "open": "10", "high": "10.2", "low": "9.8", "close": "10"} for bar in values]
    if missing:
        rows.pop(1)
    if changed:
        rows[1]["open"] = "10.1"
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200,json=rows))) as client:
        assert SinaListingDateSource(client).verify_history("600000", values, TARGET, values[0].trade_date) is expected


def test_verified_suspension_does_not_create_bars_and_evidence_expires_on_next_target(tmp_path):
    latest = TARGET - timedelta(days=1)
    value = service(tmp_path, symbols=("600000",), coverage={"600000": (300, latest)}, tdx=Source({}), baidu=Source({}))
    history = [bar.model_copy(update={"trade_date": bar.trade_date - timedelta(days=1)}) for bar in bars("600000",300)]
    value.bar_repository.latest_many = lambda symbols, limit, target: {"600000": history}
    value.listing_date_source = SimpleNamespace(verify_history=lambda *args: True)
    value.close_source = SimpleNamespace(unavailable_reason=lambda *args: "目标日停牌")
    job = value.run(value.create_backfill().job_id)
    assert job.skipped_count == 1
    assert value.bar_repository.writes == []
    assert value.coverage(TARGET).confirmed_suspended_count == 1
    assert value.coverage(TARGET).target_date_count == 0
    assert value.repair_center(TARGET).total_gap_count == 0
    assert value.create_target_repair(TARGET) is None
    assert value.repair_center(TARGET + timedelta(days=1)).total_gap_count == 1
    value.bar_repository.values["600000"] = (299, latest)
    assert value.repair_center(TARGET).total_gap_count == 1
