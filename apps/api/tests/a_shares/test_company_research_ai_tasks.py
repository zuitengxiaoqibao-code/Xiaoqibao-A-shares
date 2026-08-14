import asyncio
import sqlite3
import threading
from datetime import datetime, timezone

import pytest

from qibao_api.a_shares.company_research_ai_tasks import CompanyResearchAITaskService
from qibao_api.a_shares.company_research_ai_cache import (
    CompanyResearchAIResultRepository,
    CompanyResearchAIResultStoreError,
)
from qibao_api.contracts.company_research import CompanyResearchAIAnalysis, CompanyResearchAIResult, CompanyResearchSection, CompanyResearchVersion
from qibao_api.tasks.progress import TaskProgressRegistry
from tests.routes.test_company_research import sample_response


NOW = datetime(2026, 8, 12, 15, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_company_research_ai_task_reuses_same_frozen_version_and_does_not_block_research() -> None:
    calls = 0
    release = threading.Event()
    value = sample_response().model_copy(update={
        "research_sections": tuple(CompanyResearchSection(
            key=key, label=label, status="ready", summary=f"{label}冻结结论",
            evidence_ids=(f"evidence-{index}",),
        ) for index, (key, label) in enumerate((
            ("business_model", "商业模式"), ("industry_space", "行业空间"),
            ("financial_trend", "财务趋势"), ("profit_quality", "利润质量"),
            ("competitive_position", "竞争地位"), ("valuation_percentile", "估值分位"),
            ("future_catalysts", "未来催化"), ("contrary_risks", "反方风险"),
            ("invalidation_conditions", "失效条件"), ("verification_checklist", "核验清单"),
        ))),
        "research_version": CompanyResearchVersion(
            snapshot_id="research-v1", version_number=1, content_hash="a" * 64,
            generated_at=NOW,
        ),
    })

    class Versions:
        def get(self, snapshot_id):
            assert snapshot_id == "research-v1"
            return value

    class AI:
        def configuration_identity(self):
            return ("configured", "model", "company-research-ai-v1")

        def analyze(self, request):
            nonlocal calls
            calls += 1
            assert request.snapshot_id == "research-v1"
            assert request.evidence
            release.wait(timeout=1)
            return CompanyResearchAIResult(
                status="ready", snapshot_id=request.snapshot_id,
                analysis=CompanyResearchAIAnalysis(
                    executive_summary="只基于冻结证据总结。",
                    contrary_risks=(), verification_questions=("继续核验现金流",),
                ),
                provider="test", model="model", generated_at=NOW,
            )

    service = CompanyResearchAITaskService(Versions(), AI(), TaskProgressRegistry())
    first = service.start("research-v1")
    duplicate = service.start("research-v1")
    assert duplicate.progress.task_id == first.progress.task_id
    assert first.result is None

    release.set()
    for _ in range(100):
        snapshot = service.snapshot(first.progress.task_id)
        if snapshot and snapshot.progress.status == "succeeded":
            break
        await asyncio.sleep(0.01)
    snapshot = service.snapshot(first.progress.task_id)
    assert snapshot is not None and snapshot.result is not None
    assert snapshot.result.status == "ready"
    assert calls == 1
    service.close()


@pytest.mark.asyncio
async def test_company_research_ai_task_reuses_persisted_result_after_restart(tmp_path) -> None:
    calls = 0
    value = sample_response().model_copy(update={
        "research_sections": tuple(CompanyResearchSection(
            key=key, label=label, status="ready", summary=f"{label}冻结结论",
            evidence_ids=(f"evidence-{index}",),
        ) for index, (key, label) in enumerate((
            ("business_model", "商业模式"), ("industry_space", "行业空间"),
            ("financial_trend", "财务趋势"), ("profit_quality", "利润质量"),
            ("competitive_position", "竞争地位"), ("valuation_percentile", "估值分位"),
            ("future_catalysts", "未来催化"), ("contrary_risks", "反方风险"),
            ("invalidation_conditions", "失效条件"), ("verification_checklist", "核验清单"),
        ))),
        "research_version": CompanyResearchVersion(
            snapshot_id="research-v1", version_number=1, content_hash="a" * 64,
            generated_at=NOW,
        ),
    })

    class Versions:
        def get(self, snapshot_id):
            assert snapshot_id == "research-v1"
            return value

    class AI:
        def configuration_identity(self):
            return ("configured", "https://ai.example/v1", "model", "company-research-ai-v1", "revision-1")

        def analyze(self, request):
            nonlocal calls
            calls += 1
            return CompanyResearchAIResult(
                status="ready", snapshot_id=request.snapshot_id,
                analysis=CompanyResearchAIAnalysis(
                    executive_summary="只基于冻结证据总结。",
                    contrary_risks=(), verification_questions=("继续核验现金流",),
                ),
                provider="test", model="model", generated_at=NOW,
            )

    database = tmp_path / "company-research-ai.sqlite3"
    first_repository = CompanyResearchAIResultRepository(database)
    first_service = CompanyResearchAITaskService(
        Versions(), AI(), TaskProgressRegistry(), result_repository=first_repository,
    )
    first = first_service.start("research-v1")
    for _ in range(100):
        completed = first_service.snapshot(first.progress.task_id)
        if completed and completed.progress.status == "succeeded":
            break
        await asyncio.sleep(0.01)
    assert calls == 1
    first_service.close()
    first_repository.close()

    second_repository = CompanyResearchAIResultRepository(database)
    second_service = CompanyResearchAITaskService(
        Versions(), AI(), TaskProgressRegistry(), result_repository=second_repository,
    )
    restored = second_service.start("research-v1")

    assert restored.progress.status == "succeeded"
    assert restored.progress.detail == "已复用冻结研究版本的 AI 证据总结"
    assert restored.result is not None
    assert restored.result.analysis is not None
    assert restored.result.analysis.executive_summary == "只基于冻结证据总结。"
    assert calls == 1
    second_service.close()
    second_repository.close()

    with pytest.raises(CompanyResearchAIResultStoreError, match="read failed") as caught:
        second_repository.get(
            "research-v1",
            ("configured", "https://ai.example/v1", "model", "company-research-ai-v1", "revision-1"),
        )
    assert isinstance(caught.value.__cause__, sqlite3.ProgrammingError)
