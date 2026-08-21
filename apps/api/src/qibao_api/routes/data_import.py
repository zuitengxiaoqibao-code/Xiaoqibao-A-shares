from __future__ import annotations

import tempfile
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from qibao_api.data_sources.file_adapter import FileImportService


router = APIRouter(prefix="/api", tags=["data-import"])


class IngestRequest(BaseModel):
    mapping: dict[str, str] = Field(default_factory=dict)


def _service(request: Request) -> FileImportService:
    root = Path(getattr(request.app.state, "data_dir", Path("data"))) / "imports"
    return FileImportService(root)


async def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "upload.csv").suffix.lower() or ".csv"
    target = Path(tempfile.gettempdir()) / f"qibao-import-{uuid4().hex}{suffix}"
    with target.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            handle.write(chunk)
    return target


@router.post("/data-import/inspect")
async def inspect_data_import(request: Request, file: UploadFile = File(...)) -> dict:
    path = await _save_upload(file)
    try:
        preview = _service(request).inspect(path)
        return {
            "path": preview.path,
            "format": preview.format,
            "columns": preview.columns,
            "row_count": preview.row_count,
            "preview_rows": preview.preview_rows,
            "error": preview.error,
        }
    finally:
        path.unlink(missing_ok=True)


@router.post("/data-import/ingest")
async def ingest_data_import(
    request: Request,
    mapping: str = Form("{}"),
    file: UploadFile = File(...),
) -> dict:
    path = await _save_upload(file)
    try:
        task_id = f"import-{uuid4().hex}"
        try:
            parsed_mapping = IngestRequest.model_validate({"mapping": json.loads(mapping)}).mapping
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise HTTPException(status_code=422, detail="字段映射不是有效 JSON") from error
        result = _service(request).ingest(path, parsed_mapping, task_id=task_id)
        tasks = getattr(request.app.state, "data_import_tasks", {})
        tasks[task_id] = {
            "task_id": task_id,
            "state": "succeeded",
            "stage": "completed",
            "progress": 100,
            "processed": len(result.batch.records) + result.quarantined_rows,
            "total": len(result.batch.records) + result.quarantined_rows,
            "quarantined_rows": result.quarantined_rows,
            "quality_status": result.batch.quality_status,
            "error_message": None,
        }
        request.app.state.data_import_tasks = tasks
        return {**tasks[task_id], "batch": result.batch.model_dump(mode="json"), "quarantine_reasons": result.quarantine_reasons}
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(error) or "数据导入失败") from error
    finally:
        path.unlink(missing_ok=True)


@router.get("/data-import/tasks/{task_id}")
def data_import_task(task_id: str, request: Request) -> dict:
    tasks = getattr(request.app.state, "data_import_tasks", {})
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return task
