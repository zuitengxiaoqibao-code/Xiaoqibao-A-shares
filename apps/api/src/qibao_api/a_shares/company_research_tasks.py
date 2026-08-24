from __future__ import annotations

import asyncio
from datetime import date

from qibao_api.contracts.company_research import CompanyResearchResponse
from qibao_api.contracts.company_research_task import CompanyResearchTaskSnapshot
from qibao_api.tasks.progress import TaskProgressRegistry


class CompanyResearchTaskService:
    def __init__(
        self,
        research_service: object,
        registry: TaskProgressRegistry,
        *,
        task_timeout_seconds: float = 180.0,
    ) -> None:
        if task_timeout_seconds <= 0:
            raise ValueError("task_timeout_seconds must be positive")
        self.research_service = research_service
        self.registry = registry
        self.task_timeout_seconds = task_timeout_seconds
        self._results: dict[str, CompanyResearchResponse] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._task_keys: dict[tuple[str, date | None], str] = {}
        self._keys_by_task: dict[str, tuple[str, date | None]] = {}

    def start(self, symbol: str, as_of: date | None) -> CompanyResearchTaskSnapshot:
        key = (symbol, as_of)
        existing_id = self._task_keys.get(key)
        if existing_id is not None:
            existing = self.snapshot(existing_id)
            if existing is not None and existing.progress.status in {"queued", "running", "succeeded"}:
                return existing
            self._task_keys.pop(key, None)
            self._keys_by_task.pop(existing_id, None)
        progress = self.registry.create(
            "company-research",
            stage="queued",
            detail=f"等待研究 {symbol}",
            total=6,
        )
        task = asyncio.create_task(self._run(progress.task_id, symbol, as_of))
        self._tasks[progress.task_id] = task
        self._task_keys[key] = progress.task_id
        self._keys_by_task[progress.task_id] = key
        return CompanyResearchTaskSnapshot(progress=progress)

    def snapshot(self, task_id: str) -> CompanyResearchTaskSnapshot | None:
        progress = self.registry.get(task_id)
        if progress is None:
            return None
        return CompanyResearchTaskSnapshot(progress=progress, result=self._results.get(task_id))

    async def _run(self, task_id: str, symbol: str, as_of: date | None) -> None:
        processed = 0
        current_stage = "identity"
        current_detail = f"等待研究 {symbol}"

        def report(stage: str, detail: str) -> None:
            nonlocal processed, current_stage, current_detail
            current_stage = stage
            current_detail = detail
            processed += 1
            self.registry.update(
                task_id,
                status="running",
                stage=stage,
                processed=processed,
                detail=detail,
            )

        try:
            result = await asyncio.wait_for(
                self.research_service.get(symbol, as_of, progress_callback=report),
                timeout=self.task_timeout_seconds,
            )
            self._results[task_id] = result
            self.registry.update(
                task_id,
                status="succeeded",
                stage="complete",
                processed=6,
                detail="六个研究区块已完成",
            )
        except asyncio.TimeoutError:
            timeout_detail = {
                "identity": "研究任务超时：股票标的识别长时间无响应",
                "diagnosis": "研究任务超时：行情与风险诊断长时间无响应",
                "financials": "研究任务超时：财务数据来源长时间无响应",
                "profile": "研究任务超时：通达信 F10 来源长时间无响应",
                "events": "研究任务超时：事件与研报数据长时间无响应",
                "analysis": "研究任务超时：研究分析长时间无响应",
            }.get(current_stage, f"研究任务超时：{current_detail}")
            self.registry.update(
                task_id,
                status="failed",
                stage=current_stage,
                detail=timeout_detail,
                error="TimeoutError",
            )
        except asyncio.CancelledError:
            self.registry.update(task_id, status="cancelled", stage="cancelled", detail="任务已取消")
            raise
        except Exception as error:
            self.registry.update(
                task_id,
                status="failed",
                stage="failed",
                detail="公司研究任务失败",
                error=type(error).__name__,
            )
        finally:
            self._tasks.pop(task_id, None)
            progress = self.registry.get(task_id)
            if progress is not None and progress.status in {"failed", "cancelled"}:
                key = self._keys_by_task.pop(task_id, None)
                if key is not None and self._task_keys.get(key) == task_id:
                    self._task_keys.pop(key, None)

    def close(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        self._task_keys.clear()
        self._keys_by_task.clear()
