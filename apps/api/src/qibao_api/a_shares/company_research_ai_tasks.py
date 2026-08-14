from __future__ import annotations

import asyncio

from qibao_api.contracts.company_research import CompanyResearchAIEvidence, CompanyResearchAIRequest
from qibao_api.contracts.company_research_ai_task import CompanyResearchAITaskSnapshot
from qibao_api.tasks.progress import TaskProgressRegistry


class CompanyResearchAITaskService:
    def __init__(
        self,
        version_repository,
        ai_gateway,
        registry: TaskProgressRegistry,
        *,
        result_repository=None,
    ) -> None:
        self.version_repository = version_repository
        self.ai_gateway = ai_gateway
        self.registry = registry
        self.result_repository = result_repository
        self._tasks: dict[str, asyncio.Task] = {}
        self._results = {}
        self._task_keys: dict[tuple[str, tuple[str, ...]], str] = {}

    def start(self, snapshot_id: str) -> CompanyResearchAITaskSnapshot:
        identity = tuple(self.ai_gateway.configuration_identity())
        key = (snapshot_id, identity)
        existing_id = self._task_keys.get(key)
        if existing_id is not None:
            existing = self.snapshot(existing_id)
            if existing is not None and existing.progress.status in {"queued", "running", "succeeded"}:
                return existing
        cached = (
            self.result_repository.get(snapshot_id, identity)
            if self.result_repository is not None
            else None
        )
        if cached is not None:
            progress = self.registry.create(
                "company-research-ai",
                stage="complete",
                detail="已复用冻结研究版本的 AI 证据总结",
                total=2,
            )
            self.registry.update(
                progress.task_id,
                status="succeeded",
                stage="complete",
                processed=2,
                detail="已复用冻结研究版本的 AI 证据总结",
            )
            self._task_keys[key] = progress.task_id
            self._results[progress.task_id] = cached
            return self.snapshot(progress.task_id)
        progress = self.registry.create(
            "company-research-ai", stage="queued", detail="等待 AI 证据总结", total=2,
        )
        self._task_keys[key] = progress.task_id
        self._tasks[progress.task_id] = asyncio.create_task(
            self._run(progress.task_id, snapshot_id)
        )
        return CompanyResearchAITaskSnapshot(progress=progress)

    def snapshot(self, task_id: str) -> CompanyResearchAITaskSnapshot | None:
        progress = self.registry.get(task_id)
        if progress is None:
            return None
        return CompanyResearchAITaskSnapshot(progress=progress, result=self._results.get(task_id))

    async def _run(self, task_id: str, snapshot_id: str) -> None:
        try:
            self.registry.update(task_id, status="running", stage="evidence", processed=1, detail="正在冻结 AI 证据输入")
            value = await asyncio.to_thread(self.version_repository.get, snapshot_id)
            if value is None or value.research_version is None:
                raise LookupError("company research version not found")
            evidence = []
            conclusions = []
            for section in value.research_sections:
                conclusions.append(f"{section.label}：{section.summary}")
                for evidence_id in section.evidence_ids:
                    evidence.append(CompanyResearchAIEvidence(
                        evidence_id=evidence_id, section=section.label, summary=section.summary,
                    ))
            unique = {item.evidence_id: item for item in evidence}
            if not unique:
                for row in value.decision_ledger:
                    for evidence_id in row.evidence_ids:
                        unique[evidence_id] = CompanyResearchAIEvidence(
                            evidence_id=evidence_id, section=row.label, summary=row.summary,
                        )
            if not unique:
                raise ValueError("frozen research version has no citeable evidence")
            request = CompanyResearchAIRequest(
                snapshot_id=snapshot_id, symbol=value.symbol,
                generated_at=value.generated_at,
                evidence=tuple(unique.values()),
                deterministic_conclusions=tuple(conclusions),
            )
            result = await asyncio.to_thread(self.ai_gateway.analyze, request)
            if result.status == "ready" and self.result_repository is not None:
                result = await asyncio.to_thread(
                    self.result_repository.put,
                    result,
                    tuple(self.ai_gateway.configuration_identity()),
                )
            self._results[task_id] = result
            self.registry.update(task_id, status="succeeded", stage="complete", processed=2, detail="AI 证据总结已完成")
        except asyncio.CancelledError:
            self.registry.update(task_id, status="cancelled", stage="cancelled", detail="任务已取消")
            raise
        except Exception as error:
            self.registry.update(task_id, status="failed", stage="failed", detail="AI 证据总结不可用", error=type(error).__name__)
        finally:
            self._tasks.pop(task_id, None)

    def close(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
