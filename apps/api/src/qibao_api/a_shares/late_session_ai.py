import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from qibao_api.contracts.late_session_selection import (
    LateSessionAIAnalysis,
    LateSessionSelectionResponse,
)
from qibao_api.settings_repository import AISettings, EffectiveAISettingsResolver


_TRADING_INSTRUCTION_PATTERN = re.compile(
    r"(?:买入|卖出|加仓|减仓|止损|止盈|仓位|建仓|追高|抄底)|\b(?:buy|sell|stop[- ]?loss|take[- ]?profit)\b",
    re.IGNORECASE,
)


class LateSessionAIAnalyzer:
    """Analyze only the server-verified late-session result; never invent candidates."""

    def __init__(self, settings: EffectiveAISettingsResolver | None, *, timeout: float = 25) -> None:
        self.settings = settings
        self.timeout = timeout

    def analyze_sync(self, selection: LateSessionSelectionResponse) -> LateSessionAIAnalysis:
        return self._fallback(selection, status="no_candidates" if selection.candidate_count == 0 else "unconfigured")

    async def analyze(self, selection: LateSessionSelectionResponse) -> LateSessionAIAnalysis:
        if selection.candidate_count == 0:
            return self._fallback(selection, status="no_candidates")
        if self.settings is None:
            return self._fallback(selection, status="unconfigured")
        configured = self.settings.resolve()
        if not isinstance(configured, AISettings):
            return self._fallback(selection, status="unconfigured")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{configured.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {configured.api_key}"},
                    json=self._request(selection, configured.model),
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                parsed = json.loads(content) if isinstance(content, str) else content
                analysis = self._validate_ai_payload(parsed, selection)
                return analysis
        except (httpx.HTTPError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            fallback = self._fallback(selection, status="error")
            return fallback.model_copy(update={"reason": f"AI 分析调用失败，已回退规则解析：{type(exc).__name__}"})

    def _request(self, selection: LateSessionSelectionResponse, model: str) -> dict[str, Any]:
        candidates = [
            {
                "symbol": item.quote.symbol,
                "name": item.quote.name,
                "change_percent": str(item.quote.change_percent),
                "volume_ratio": str(item.quote.volume_ratio) if item.quote.volume_ratio is not None else None,
                "turnover_rate": str(item.quote.turnover_rate) if item.quote.turnover_rate is not None else None,
                "market_cap_yi": str(item.quote.market_cap_yi) if item.quote.market_cap_yi is not None else None,
                "behavior_tags": item.behavior_tags,
                "risk_notes": item.risk_notes,
            }
            for item in selection.candidates
        ]
        return {
            "model": model,
            "temperature": 0,
            "max_tokens": 1400,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 A 股尾盘筛选结果解释器。只能根据输入的真实候选和规则证据总结，"
                        "不得新增股票、不得编造字段、不得给出买卖、仓位、止损或止盈指令。"
                        "只返回 JSON：summary、key_points、risk_points、data_gaps。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "trading_date": selection.trading_date.isoformat(),
                            "phase": selection.phase,
                            "candidate_count": selection.candidate_count,
                            "rules": [rule.model_dump(mode="json") for rule in selection.rules],
                            "candidates": candidates,
                            "limitations": selection.limitations,
                            "source_evidence": selection.source_evidence,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

    def _validate_ai_payload(self, payload: Any, selection: LateSessionSelectionResponse) -> LateSessionAIAnalysis:
        if not isinstance(payload, dict):
            raise ValueError("AI 返回不是对象")
        values: dict[str, Any] = {}
        for key in ("summary", "key_points", "risk_points", "data_gaps"):
            value = payload.get(key)
            if key == "summary":
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("AI summary 无效")
                values[key] = value.strip()
            else:
                if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                    raise ValueError(f"AI {key} 无效")
                values[key] = tuple(item.strip() for item in value if item.strip())
        text = " ".join((values["summary"], *values["key_points"], *values["risk_points"], *values["data_gaps"]))
        if _TRADING_INSTRUCTION_PATTERN.search(text):
            raise ValueError("AI 返回包含交易指令")
        return LateSessionAIAnalysis(
            status="ready",
            mode="ai",
            title="AI 结果解析",
            summary=values["summary"],
            key_points=values["key_points"],
            risk_points=values["risk_points"],
            data_gaps=values["data_gaps"],
            candidate_count=selection.candidate_count,
            source_evidence=selection.source_evidence,
            observed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _fallback(selection: LateSessionSelectionResponse, *, status: str) -> LateSessionAIAnalysis:
        if selection.candidate_count == 0:
            reason = selection.no_data_reason or "当前规则下没有产生候选股票"
            return LateSessionAIAnalysis(
                status="no_candidates",
                mode="unavailable",
                title="暂不生成 AI 结论",
                summary=f"当前没有产生候选股票，不能对不存在的结果进行 AI 分析。{reason}。",
                data_gaps=selection.limitations,
                candidate_count=0,
                source_evidence=selection.source_evidence,
                observed_at=selection.server_time,
                reason=reason,
            )
        candidates = selection.candidates
        positive = sum(1 for item in candidates if any("溢价" in tag or "观察" in tag for tag in item.behavior_tags))
        risks = tuple(note for item in candidates for note in item.risk_notes)
        key_points = (
            f"当前筛选保留 {len(candidates)} 只股票，均来自真实行情快照。",
            f"其中 {positive} 只带有尾盘强势或溢价观察标签。",
            "候选排序只反映当前规则通过结果，不代表未来收益预测。",
        )
        return LateSessionAIAnalysis(
            status=status,
            mode="rule_interpretation",
            title="AI 未配置 · 已输出规则解析" if status == "unconfigured" else "AI 暂不可用 · 已输出规则解析",
            summary="当前结果已按筛选规则、字段完整性和尾盘行为标签完成结构化解析；未将规则通过误写成买卖结论。",
            key_points=key_points,
            risk_points=risks or ("需结合后续真实分时数据继续核验。",),
            data_gaps=selection.limitations,
            candidate_count=len(candidates),
            source_evidence=selection.source_evidence,
            observed_at=selection.server_time,
            reason="未配置 OpenAI 兼容接口" if status == "unconfigured" else None,
        )
