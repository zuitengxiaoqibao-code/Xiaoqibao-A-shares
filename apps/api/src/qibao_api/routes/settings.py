from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from qibao_api.ai_status import AIConnectionState, classify_ai_status

from qibao_api.settings_repository import (
    AISettings,
    AISettingsRepository,
    EffectiveAISettingsResolver,
)
from qibao_api.local_sources.discovery import (
    LocalTerminalDiscovery,
    LocalTerminalDiscoveryResult,
    LocalTerminalStatus,
    running_tdx_process_paths,
)
from qibao_api.local_sources.models import LocalSourceSettings
from qibao_api.local_sources.repository import (
    LocalSourceSettingsRepository,
    LocalSourceSettingsRecord,
)
from qibao_api.gongbu.tdx_local_overview import (
    TdxJsonRpcClient,
    probe_tdx_capabilities,
    tdx_read_only_capability_catalog,
)
from qibao_api.gongbu.tdx_local_professional import inspect_tdx_quant_python_roots
from qibao_api.external_sources import ExternalDataSourceRepository, ExternalDataSourceService, BUILTIN_EXTERNAL_SOURCES


# Local-admin trust boundary: the application binds locally and intentionally supports
# localhost/private OpenAI-compatible providers. Deployment authentication is out of scope here.
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class ExternalDataSourceView(BaseModel):
    source_id: str
    name: str
    description: str
    capabilities: list[str]
    key_label: str
    key_url: str
    configured: bool
    enabled: bool
    api_key_hint: str | None
    status: str
    capability_checks: list[dict[str, str | None]] = Field(default_factory=list)
    last_tested_at: str | None = None
    last_error: str | None = None
    reason: str | None = None


class ExternalDataSourceListView(BaseModel):
    sources: list[ExternalDataSourceView]


class ExternalDataSourceInput(BaseModel):
    api_key: str
    enabled: bool = True


def get_external_data_source_repository(request: Request) -> ExternalDataSourceRepository:
    return request.app.state.external_data_source_repository


def get_external_data_source_service(request: Request) -> ExternalDataSourceService:
    return request.app.state.external_data_source_service


def _external_views(repository: ExternalDataSourceRepository) -> ExternalDataSourceListView:
    return ExternalDataSourceListView(sources=[ExternalDataSourceView(**item) for item in repository.list_views()])


@router.get("/external-data-sources", response_model=ExternalDataSourceListView)
def get_external_data_sources(
    repository: Annotated[ExternalDataSourceRepository, Depends(get_external_data_source_repository)],
) -> ExternalDataSourceListView:
    return _external_views(repository)


@router.put("/external-data-sources/{source_id}", response_model=ExternalDataSourceView)
def put_external_data_source(
    source_id: str,
    payload: ExternalDataSourceInput,
    repository: Annotated[ExternalDataSourceRepository, Depends(get_external_data_source_repository)],
) -> ExternalDataSourceView:
    try:
        return ExternalDataSourceView(**repository.save(source_id, api_key=payload.api_key, enabled=payload.enabled))
    except KeyError as error:
        raise HTTPException(status_code=404, detail="未知数据源") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/external-data-sources/{source_id}", response_model=ExternalDataSourceView)
def delete_external_data_source(
    source_id: str,
    repository: Annotated[ExternalDataSourceRepository, Depends(get_external_data_source_repository)],
) -> ExternalDataSourceView:
    try:
        return ExternalDataSourceView(**repository.clear(source_id))
    except KeyError as error:
        raise HTTPException(status_code=404, detail="未知数据源") from error


@router.post("/external-data-sources/{source_id}/test", response_model=ExternalDataSourceView)
def test_external_data_source(
    source_id: str,
    repository: Annotated[ExternalDataSourceRepository, Depends(get_external_data_source_repository)],
    service: Annotated[ExternalDataSourceService, Depends(get_external_data_source_service)],
) -> ExternalDataSourceView:
    try:
        return ExternalDataSourceView(**service.test(source_id))
    except KeyError as error:
        raise HTTPException(status_code=404, detail="未知数据源") from error


class AISettingsView(BaseModel):
    configured: bool
    state: AIConnectionState
    message: str
    base_url: str | None
    model: str | None
    api_key_hint: str | None


class LocalSourceSettingsView(BaseModel):
    settings_state: Literal["ready", "default", "invalid_local_config"]
    settings: LocalSourceSettings
    scanned_at: str
    terminals: tuple[LocalTerminalStatus, ...]
    active_tdx_vipdoc: Path | None
    tdx_rpc: "TdxRpcStatus"
    restart_required: bool = False


class TdxDirectoryCandidateView(BaseModel):
    root: Path
    vipdoc_path: Path | None = None
    display_name: str
    latest_trade_date: str | None = None
    day_file_count: int = 0
    readable_day_file_count: int = 0
    a_share_coverage_percent: float = 0.0
    score: float = 0.0
    state: Literal["ready", "partial", "unavailable"]
    reasons: tuple[str, ...] = ()


class TdxDirectoriesView(BaseModel):
    active_mode: Literal["auto", "manual"]
    active_root: Path | None
    scanned_at: str
    state: Literal["ready", "partial", "unavailable"]
    candidates: tuple[TdxDirectoryCandidateView, ...] = ()


class TdxDirectorySelectionInput(BaseModel):
    root: Path | None = None


class TdxRpcCapability(BaseModel):
    key: str
    label: str
    method: str
    status: Literal["ready", "unavailable", "disabled"]
    semantic_status: Literal["not_applicable", "detected_only", "verified"] = "not_applicable"
    reason_code: str = "unknown"
    detail: str


class TdxDirectPythonStatus(BaseModel):
    status: Literal["detected_only", "unavailable"]
    detail: str
    module_path: str | None = None


class TdxClientStatus(BaseModel):
    status: Literal["running", "not_running", "unknown"]
    executable_path: Path | None = None
    detail: str


class TdxRecoveryStep(BaseModel):
    key: str
    label: str
    status: Literal["ready", "detected_only", "unavailable", "disabled"]
    detail: str


class TdxRpcStatus(BaseModel):
    status: Literal["ready", "partial", "unavailable", "disabled"]
    reachable: bool
    endpoint: str | None
    observed_at: str
    capabilities: tuple[TdxRpcCapability, ...]
    direct_python: TdxDirectPythonStatus
    client: TdxClientStatus
    recovery_steps: tuple[TdxRecoveryStep, ...] = ()


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


def get_local_source_discovery_snapshot(request: Request) -> LocalTerminalDiscoveryResult | None:
    return getattr(request.app.state, "local_source_discovery_result", None)


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
        tdx_rpc=_tdx_rpc_view(record.settings, discovery),
        restart_required=restart_required,
    )


def _tdx_directories_view(
    record: LocalSourceSettingsRecord,
    discovery: LocalTerminalDiscoveryResult,
) -> TdxDirectoriesView:
    candidates = tuple(
        TdxDirectoryCandidateView(
            root=item.install_path,
            vipdoc_path=item.data_path,
            display_name=item.install_path.name or str(item.install_path),
            latest_trade_date=(item.latest_trade_date.isoformat() if item.latest_trade_date else None),
            day_file_count=item.day_file_count or item.sh_daily_count + item.sz_daily_count,
            readable_day_file_count=item.readable_day_file_count,
            a_share_coverage_percent=item.a_share_coverage_percent,
            score=item.source_score,
            state=("unavailable" if item.status == "invalid" else "ready" if item.status == "ready" and item.readable_day_file_count >= item.day_file_count else "partial"),
            reasons=item.source_reasons,
        )
        for item in discovery.terminals
        if item.vendor == "tdx"
    )
    active_root = (
        discovery.active_tdx_vipdoc.parent
        if discovery.active_tdx_vipdoc is not None
        else None
    )
    return TdxDirectoriesView(
        active_mode="manual" if record.settings.tdx_install_paths else "auto",
        active_root=active_root,
        scanned_at=discovery.scanned_at.isoformat(),
        state="ready" if candidates and active_root else "partial" if candidates else "unavailable",
        candidates=candidates,
    )


def _bridge_port_label(endpoint: str | None) -> str:
    if not endpoint:
        return "本地桥接端口"
    try:
        parsed = urlparse(endpoint)
        if parsed.port is not None:
            return str(parsed.port)
    except ValueError:
        pass
    return "本地桥接端口"


def _tdx_rpc_view(
    settings: LocalSourceSettings,
    discovery: LocalTerminalDiscoveryResult,
) -> TdxRpcStatus:
    observed_at = datetime.now(timezone.utc).isoformat()
    catalog = tdx_read_only_capability_catalog()
    bridge_port = _bridge_port_label(settings.tdx_rpc_url)
    process_paths = running_tdx_process_paths()
    client = TdxClientStatus(
        status="running" if process_paths else "not_running",
        executable_path=process_paths[0] if process_paths else None,
        detail=(
            f"检测到通达信客户端进程；这不代表 {bridge_port} JSON-RPC 桥已经监听"
            if process_paths
            else "未检测到通达信客户端进程；目录或缓存文件存在不代表客户端已运行"
        ),
    )
    direct = inspect_tdx_quant_python_roots(tuple(
        terminal.install_path
        for terminal in discovery.terminals
        if (
            terminal.vendor == "tdx"
            and terminal.status == "ready"
            and terminal.selection_eligible
        )
    ))
    direct_python = TdxDirectPythonStatus(
        status=direct.status,
        detail=direct.detail,
        module_path=direct.module_path,
    )
    if not settings.tdx_rpc_enabled or settings.tdx_rpc_url is None:
        recovery_steps = _tdx_recovery_steps(
            discovery=discovery,
            client=client,
            direct_python=direct_python,
            reachable=False,
            capabilities=(),
            disabled=True,
        )
        return TdxRpcStatus(
            status="disabled",
            reachable=False,
            endpoint=settings.tdx_rpc_url,
            observed_at=observed_at,
            capabilities=tuple(
                TdxRpcCapability(**item, status="disabled", detail="本地通达信桥接未启用")
                for item in catalog
            ),
            direct_python=direct_python,
            client=client,
            recovery_steps=recovery_steps,
        )

    rpc = TdxJsonRpcClient(endpoint=settings.tdx_rpc_url)
    try:
        report = probe_tdx_capabilities(rpc)
    finally:
        rpc.close()
    recovery_steps = _tdx_recovery_steps(
        discovery=discovery,
        client=client,
        direct_python=direct_python,
        reachable=bool(report["reachable"]),
        capabilities=tuple(report["capabilities"]),
        disabled=False,
    )
    return TdxRpcStatus(
        status=report["status"],
        reachable=bool(report["reachable"]),
        endpoint=settings.tdx_rpc_url,
        observed_at=observed_at,
        capabilities=tuple(TdxRpcCapability(**item) for item in report["capabilities"]),
        direct_python=direct_python,
        client=client,
        recovery_steps=recovery_steps,
    )


def _tdx_recovery_steps(
    *,
    discovery: LocalTerminalDiscoveryResult,
    client: TdxClientStatus,
    direct_python: TdxDirectPythonStatus,
    reachable: bool,
    capabilities: tuple[dict, ...],
    disabled: bool,
) -> tuple[TdxRecoveryStep, ...]:
    ready_terminal = any(
        item.vendor == "tdx" and item.status == "ready" and item.selection_eligible
        for item in discovery.terminals
    )
    professional = [item for item in capabilities if item["key"].startswith("professional_")]
    professional_verified = any(item.get("semantic_status") == "verified" for item in professional)
    professional_detected = any(item.get("semantic_status") == "detected_only" for item in professional)
    return (
        TdxRecoveryStep(
            key="install_directory", label="安装目录",
            status="ready" if ready_terminal else "unavailable",
            detail="已发现可选用的通达信数据目录" if ready_terminal else "未发现可读取的通达信目录或 vipdoc",
        ),
        TdxRecoveryStep(
            key="plugin_dll", label="插件 / DLL",
            status=direct_python.status,
            detail=direct_python.detail,
        ),
        TdxRecoveryStep(
            key="process", label="通达信进程",
            status="ready" if client.status == "running" else "unavailable",
            detail=client.detail,
        ),
        TdxRecoveryStep(
            key="rpc", label="RPC 可达",
            status="disabled" if disabled else "ready" if reachable else "unavailable",
            detail="桥接未启用" if disabled else "本地 JSON-RPC 端口可达" if reachable else "本地 JSON-RPC 端口不可达",
        ),
        TdxRecoveryStep(
            key="capability_call", label="能力调用",
            status="disabled" if disabled else "ready" if any(item.get("status") == "ready" for item in capabilities) else "unavailable",
            detail="等待桥接启用" if disabled else "至少一项只读接口返回结构化响应" if any(item.get("status") == "ready" for item in capabilities) else "没有只读接口返回可用响应",
        ),
        TdxRecoveryStep(
            key="field_completeness", label="字段完整性",
            status="ready" if professional_verified else "detected_only" if professional_detected else "disabled" if disabled else "unavailable",
            detail="专业字段语义已验证" if professional_verified else "已返回专业结构，但字段语义/单位仍未映射" if professional_detected else "等待专业字段返回" if not disabled else "桥接未启用",
        ),
    )


def _invalid_manual_paths(discovery: LocalTerminalDiscoveryResult) -> list[Path]:
    return [
        item.install_path
        for item in discovery.terminals
        if item.origin == "manual" and item.status == "invalid"
    ]


def _view(settings: AISettings | object) -> AISettingsView:
    if not isinstance(settings, AISettings):
        status = classify_ai_status(configured=False)
        return AISettingsView(
            configured=False, state=status.state, message=status.message,
            base_url=None, model=None, api_key_hint=None
        )
    status = classify_ai_status(configured=True)
    visible_count = min(4, max(0, len(settings.api_key) - 1))
    suffix = settings.api_key[-visible_count:] if visible_count else ""
    return AISettingsView(
        configured=True,
        state=status.state,
        message=status.message,
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
    request: Request,
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
    cached = get_local_source_discovery_snapshot(request)
    return _local_source_view(record, cached or discovery.inspect(record.settings))


@router.get("/tdx-directories", response_model=TdxDirectoriesView)
def get_tdx_directories(
    request: Request,
    repository: Annotated[
        LocalSourceSettingsRepository,
        Depends(get_local_source_settings_repository),
    ],
    discovery: Annotated[
        LocalTerminalDiscovery,
        Depends(get_local_terminal_discovery),
    ],
) -> TdxDirectoriesView:
    record = repository.load()
    cached = get_local_source_discovery_snapshot(request)
    return _tdx_directories_view(record, cached or discovery.inspect(record.settings))


@router.post("/tdx-directories/select", response_model=TdxDirectoriesView)
def select_tdx_directory(
    payload: TdxDirectorySelectionInput,
    request: Request,
    repository: Annotated[
        LocalSourceSettingsRepository,
        Depends(get_local_source_settings_repository),
    ],
    discovery: Annotated[
        LocalTerminalDiscovery,
        Depends(get_local_terminal_discovery),
    ],
) -> TdxDirectoriesView:
    current = repository.load()
    if payload.root is None:
        settings = current.settings.model_copy(update={
            "auto_discovery": True,
            "tdx_install_paths": (),
        })
    else:
        root = payload.root.expanduser().resolve(strict=False)
        settings = current.settings.model_copy(update={
            "auto_discovery": False,
            "tdx_install_paths": (root,),
        })
    inspected = discovery.inspect(settings)
    invalid = _invalid_manual_paths(inspected)
    if invalid:
        raise HTTPException(status_code=422, detail=f"通达信目录无效或缺少本地数据：{'、'.join(str(path) for path in invalid)}")
    repository.save(settings)
    request.app.state.local_source_discovery_result = inspected
    return _tdx_directories_view(
        LocalSourceSettingsRecord(settings=settings, state="ready"), inspected
    )


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
    request: Request,
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
    request.app.state.local_source_discovery_result = inspected
    record = LocalSourceSettingsRecord(settings=settings, state="ready")
    return _local_source_view(record, inspected, restart_required=True)
