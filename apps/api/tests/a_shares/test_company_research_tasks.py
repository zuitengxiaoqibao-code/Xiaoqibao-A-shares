import asyncio
from datetime import UTC, date, datetime

import pytest

from qibao_api.a_shares.company_research_tasks import CompanyResearchTaskService
from qibao_api.tasks.progress import TaskProgressRegistry
from tests.routes.test_company_research import sample_response


@pytest.mark.asyncio
async def test_company_research_task_reports_six_real_blocks_and_returns_result() -> None:
    class Research:
        async def get(self, symbol, as_of, progress_callback=None):
            for stage in ("identity", "diagnosis", "financials", "profile", "events", "analysis"):
                progress_callback(stage, stage)
                await asyncio.sleep(0)
            return sample_response()

    registry = TaskProgressRegistry(clock=lambda: datetime(2026, 8, 12, tzinfo=UTC))
    service = CompanyResearchTaskService(Research(), registry)

    started = service.start("600519", date(2026, 8, 3))
    for _ in range(100):
        current = service.snapshot(started.progress.task_id)
        if current is not None and current.progress.status == "succeeded":
            break
        await asyncio.sleep(0.001)
    finished = service.snapshot(started.progress.task_id)

    assert finished is not None
    assert finished.progress.status == "succeeded"
    assert finished.progress.processed == 6
    assert finished.progress.percent == 100
    assert finished.result is not None
    assert finished.result.symbol == "600519"


@pytest.mark.asyncio
async def test_company_research_task_keeps_failure_stage_without_fake_result() -> None:
    class Research:
        async def get(self, symbol, as_of, progress_callback=None):
            progress_callback("identity", "identity")
            raise OSError("source unavailable")

    registry = TaskProgressRegistry()
    service = CompanyResearchTaskService(Research(), registry)
    started = service.start("600519", None)
    for _ in range(100):
        current = service.snapshot(started.progress.task_id)
        if current is not None and current.progress.status == "failed":
            break
        await asyncio.sleep(0.001)
    failed = service.snapshot(started.progress.task_id)

    assert failed is not None
    assert failed.progress.status == "failed"
    assert failed.progress.percent < 100
    assert failed.result is None


@pytest.mark.asyncio
async def test_company_research_reuses_the_same_symbol_and_date_task() -> None:
    release = asyncio.Event()
    calls = 0

    class Research:
        async def get(self, symbol, as_of, progress_callback=None):
            nonlocal calls
            calls += 1
            await release.wait()
            for stage in ("identity", "diagnosis", "financials", "profile", "events", "analysis"):
                progress_callback(stage, stage)
            return sample_response()

    registry = TaskProgressRegistry(clock=lambda: datetime(2026, 8, 12, tzinfo=UTC))
    service = CompanyResearchTaskService(Research(), registry)

    first = service.start("600519", date(2026, 8, 12))
    duplicate = service.start("600519", date(2026, 8, 12))
    different_date = service.start("600519", date(2026, 8, 11))

    assert duplicate.progress.task_id == first.progress.task_id
    assert different_date.progress.task_id != first.progress.task_id
    release.set()
    for _ in range(100):
        if service.snapshot(first.progress.task_id).progress.status == "succeeded" and service.snapshot(different_date.progress.task_id).progress.status == "succeeded":
            break
        await asyncio.sleep(0.001)
    assert calls == 2

    completed_duplicate = service.start("600519", date(2026, 8, 12))
    assert completed_duplicate.progress.task_id == first.progress.task_id
    assert calls == 2


@pytest.mark.asyncio
async def test_company_research_allows_retry_after_a_failed_same_key_task() -> None:
    calls = 0

    class Research:
        async def get(self, symbol, as_of, progress_callback=None):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("source unavailable")
            for stage in ("identity", "diagnosis", "financials", "profile", "events", "analysis"):
                progress_callback(stage, stage)
            return sample_response()

    registry = TaskProgressRegistry()
    service = CompanyResearchTaskService(Research(), registry)
    failed = service.start("600519", date(2026, 8, 12))
    for _ in range(100):
        if service.snapshot(failed.progress.task_id).progress.status == "failed":
            break
        await asyncio.sleep(0.001)

    retried = service.start("600519", date(2026, 8, 12))
    assert retried.progress.task_id != failed.progress.task_id
    for _ in range(100):
        if service.snapshot(retried.progress.task_id).progress.status == "succeeded":
            break
        await asyncio.sleep(0.001)
    assert calls == 2


@pytest.mark.asyncio
async def test_company_research_task_ends_with_chinese_timeout_stage() -> None:
    class Research:
        async def get(self, symbol, as_of, progress_callback=None):
            progress_callback("financials", "正在等待财务来源")
            await asyncio.Event().wait()

    registry = TaskProgressRegistry()
    service = CompanyResearchTaskService(Research(), registry, task_timeout_seconds=0.01)
    started = service.start("600519", date(2026, 8, 12))
    for _ in range(100):
        current = service.snapshot(started.progress.task_id)
        if current is not None and current.progress.status == "failed":
            break
        await asyncio.sleep(0.001)

    failed = service.snapshot(started.progress.task_id)
    assert failed is not None
    assert failed.progress.status == "failed"
    assert failed.progress.stage == "financials"
    assert failed.progress.detail == "研究任务超时：财务数据来源长时间无响应"


@pytest.mark.asyncio
async def test_company_research_task_aclose_waits_for_cancelled_tasks() -> None:
    release = asyncio.Event()

    class Research:
        async def get(self, symbol, as_of, progress_callback=None):
            await release.wait()
            return sample_response()

    service = CompanyResearchTaskService(Research(), TaskProgressRegistry())
    started = service.start("600519", date(2026, 8, 12))
    await asyncio.sleep(0)

    await service.aclose()

    assert service.snapshot(started.progress.task_id).progress.status == "cancelled"
    assert not service._tasks
