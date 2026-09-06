from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx


AIConnectionState = Literal[
    "unconfigured",
    "configured_unverified",
    "connected",
    "connection_failed",
    "output_invalid",
    "timeout",
    "rate_limited",
    "model_not_found",
]


@dataclass(frozen=True)
class AIConnectionStatus:
    state: AIConnectionState
    message: str


def classify_ai_exception(error: BaseException) -> AIConnectionStatus:
    """将 SDK/HTTP 异常映射为稳定、可展示的 AI 状态。"""
    if isinstance(error, (TimeoutError, httpx.TimeoutException)):
        return AIConnectionStatus("timeout", "AI 接口连接超时，已保留规则分析")
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code if error.response is not None else None
        if status == 429:
            return AIConnectionStatus("rate_limited", "AI 接口触发限流，稍后将自动重试")
        if status == 404:
            return AIConnectionStatus("model_not_found", "AI 模型不存在或接口路径不正确")
        return AIConnectionStatus("connection_failed", "AI 接口连接失败，已保留规则分析")
    return AIConnectionStatus("connection_failed", "AI 接口连接失败，已保留规则分析")


def classify_ai_status(
    *,
    configured: bool,
    verified: bool = False,
    http_status: int | None = None,
    error: BaseException | None = None,
) -> AIConnectionStatus:
    if not configured:
        return AIConnectionStatus("unconfigured", "尚未配置 AI 接口")
    if isinstance(error, TimeoutError):
        return AIConnectionStatus("timeout", "AI 接口连接超时，已保留规则分析")
    if http_status == 429:
        return AIConnectionStatus("rate_limited", "AI 接口触发限流，稍后将自动重试")
    if http_status == 404:
        return AIConnectionStatus("model_not_found", "AI 模型不存在或接口路径不正确")
    if error is not None or (http_status is not None and http_status >= 400):
        return AIConnectionStatus("connection_failed", "AI 接口连接失败，已保留规则分析")
    if verified:
        return AIConnectionStatus("connected", "AI 接口已连接")
    return AIConnectionStatus("configured_unverified", "AI 接口已配置，等待首次连接验证")
