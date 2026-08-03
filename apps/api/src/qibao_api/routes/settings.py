from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from qibao_api.settings_repository import (
    AISettings,
    AISettingsRepository,
    EffectiveAISettingsResolver,
)
from qibao_api.local_sources.discovery import (
    LocalTerminalDiscovery,
    LocalTerminalDiscoveryResult,
    LocalTerminalStatus,
)
from qibao_api.local_sources.models import LocalSourceSettings
from qibao_api.local_sources.repository import (
    LocalSourceSettingsRepository,
    LocalSourceSettingsRecord,
)


# Local-admin trust boundary: the application binds locally and intentionally supports
# localhost/private OpenAI-compatible providers. Deployment authentication is out of scope here.
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class AISettingsView(BaseModel):
    configured: bool
    base_url: str | None
    model: str | None
    api_key_hint: str | None


class LocalSourceSettingsView(BaseModel):
    settings_state: Literal["ready", "default", "invalid_local_config"]
    settings: LocalSourceSettings
    scanned_at: str
    terminals: tuple[LocalTerminalStatus, ...]
    active_tdx_vipdoc: Path | None
    restart_required: bool = False


def get_ai_settings_repository(request: Request) -> AISettingsRepository:
    return request.app.state.ai_settings_repository


def get_effective_ai_settings(request: Request) -> EffectiveAISettingsResolver:
    return request.app.state.effective_ai_settings


def get_local_source_settings_repository(
    request: Request,
) -> LocalSourceSettingsRepository:
    return request.app.state.local_source_settings_repository


def get_local_terminal_discovery(request: Request) -> LocalTerminalDiscovery:
    return request.app.state.local_terminal_discovery


def _local_source_view(
    record: LocalSourceSettingsRecord,
    discovery: LocalTerminalDiscoveryResult,
    *,
    restart_required: bool = False,
) -> LocalSourceSettingsView:
    return LocalSourceSettingsView(
        settings_state=record.state,
        settings=record.settings,
        scanned_at=discovery.scanned_at.isoformat(),
        terminals=discovery.terminals,
        active_tdx_vipdoc=discovery.active_tdx_vipdoc,
        restart_required=restart_required,
    )


def _invalid_manual_paths(discovery: LocalTerminalDiscoveryResult) -> list[Path]:
    return [
        item.install_path
        for item in discovery.terminals
        if item.origin == "manual" and item.status == "invalid"
    ]


def _view(settings: AISettings | object) -> AISettingsView:
    if not isinstance(settings, AISettings):
        return AISettingsView(
            configured=False, base_url=None, model=None, api_key_hint=None
        )
    visible_count = min(4, max(0, len(settings.api_key) - 1))
    suffix = settings.api_key[-visible_count:] if visible_count else ""
    return AISettingsView(
        configured=True,
        base_url=settings.base_url,
        model=settings.model,
        api_key_hint=f"****{suffix}",
    )


@router.get("/ai", response_model=AISettingsView)
def get_ai_settings(
    settings: Annotated[EffectiveAISettingsResolver, Depends(get_effective_ai_settings)],
) -> AISettingsView:
    return _view(settings.resolve())


@router.put("/ai", response_model=AISettingsView)
async def put_ai_settings(
    request: Request,
    repository: Annotated[AISettingsRepository, Depends(get_ai_settings_repository)],
) -> AISettingsView:
    try:
        payload = await request.json()
        if not isinstance(payload, dict) or set(payload) != {"base_url", "model", "api_key"}:
            raise ValueError("invalid shape")
        if not all(isinstance(payload[field], str) for field in payload):
            raise ValueError("invalid types")
        settings = AISettings(**payload)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail="Invalid AI settings") from error
    repository.save(settings)
    return _view(settings)


@router.delete("/ai", response_model=AISettingsView)
def delete_ai_settings(
    repository: Annotated[AISettingsRepository, Depends(get_ai_settings_repository)],
    settings: Annotated[EffectiveAISettingsResolver, Depends(get_effective_ai_settings)],
) -> AISettingsView:
    repository.delete()
    return _view(settings.resolve())


@router.get("/data-sources", response_model=LocalSourceSettingsView)
def get_data_source_settings(
    repository: Annotated[
        LocalSourceSettingsRepository,
        Depends(get_local_source_settings_repository),
    ],
    discovery: Annotated[
        LocalTerminalDiscovery,
        Depends(get_local_terminal_discovery),
    ],
) -> LocalSourceSettingsView:
    record = repository.load()
    return _local_source_view(record, discovery.inspect(record.settings))


@router.post("/data-sources/detect", response_model=LocalSourceSettingsView)
def detect_data_sources(
    settings: LocalSourceSettings,
    repository: Annotated[
        LocalSourceSettingsRepository,
        Depends(get_local_source_settings_repository),
    ],
    discovery: Annotated[
        LocalTerminalDiscovery,
        Depends(get_local_terminal_discovery),
    ],
) -> LocalSourceSettingsView:
    state = repository.load().state
    record = LocalSourceSettingsRecord(settings=settings, state=state)
    return _local_source_view(record, discovery.inspect(settings))


@router.put("/data-sources", response_model=LocalSourceSettingsView)
def put_data_source_settings(
    settings: LocalSourceSettings,
    repository: Annotated[
        LocalSourceSettingsRepository,
        Depends(get_local_source_settings_repository),
    ],
    discovery: Annotated[
        LocalTerminalDiscovery,
        Depends(get_local_terminal_discovery),
    ],
) -> LocalSourceSettingsView:
    inspected = discovery.inspect(settings)
    invalid = _invalid_manual_paths(inspected)
    if invalid:
        paths = "、".join(str(path) for path in invalid)
        raise HTTPException(status_code=422, detail=f"通达信目录无效或缺少本地数据：{paths}")
    repository.save(settings)
    record = LocalSourceSettingsRecord(settings=settings, state="ready")
    return _local_source_view(record, inspected, restart_required=True)
