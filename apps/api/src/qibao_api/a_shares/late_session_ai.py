import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from time import monotonic
from typing import Any

import httpx

from qibao_api.contracts.late_session_selection import (
    LateSessionAIAnalysis,
    LateSessionSelectionResponse,
)
from qibao_api.settings_repository import AISettings, EffectiveAISettingsResolver


logger = logging.getLogger(__name__)
LATE_SESSION_AI_TIMEOUT_SECONDS = 60


_TRADING_INSTRUCTION_PATTERN = re.compile(
    r"(?:买入|卖出|加仓|减仓|止损|止盈|仓位|建仓|追高|抄底)|\b(?:buy|sell|stop[- ]?loss|take[- ]?profit)\b",
    re.IGNORECASE,
)


class LateSessionAIAnalyzer:
    """Analyze only the server-verified late-session result; never invent candidates."""

    def __init__(self, settings: EffectiveAISettingsResolver | None, *, timeout: float = LATE_SESSION_AI_TIMEOUT_SECONDS) -> None:
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
        started = monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{configured.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {configured.api_key}"},
                    json=self._request(selection, configured.model),
                )
                response.raise_for_status()
                payload = response.json()
                choice = payload["choices"][0]
                content = choice["message"]["content"]
                if not content and choice.get("finish_reason") == "length":
                    raise ValueError("模型输出额度已用尽，未返回最终分析")
                parsed = self._parse_content(content)
                analysis = self._validate_ai_payload(parsed, selection)
                return analysis
        except (httpx.HTTPError, TimeoutError) as exc:
            logger.warning(
                "late-session AI unavailable provider=%s model=%s error_type=%s elapsed_ms=%s",
                configured.base_url,
                configured.model,
                type(exc).__name__,
                round((monotonic() - started) * 1000),
            )
            fallback = self._fallback(selection, status="error")
            return fallback.model_copy(update={"reason": f"AI 接口调用失败，已回退规则解析：{type(exc).__name__}"})
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning(
                "late-session AI invalid output provider=%s model=%s error_type=%s elapsed_ms=%s",
                configured.base_url,
                configured.model,
                type(exc).__name__,
                round((monotonic() - started) * 1000),
            )
            fallback = self._fallback(selection, status="output_invalid")
            reason = str(exc).strip() if str(exc).strip() else type(exc).__name__
            return fallback.model_copy(update={"reason": f"模型没有返回可解析结论：{reason}"})

    def _request(self, selection: LateSessionSelectionResponse, model: str) -> dict[str, Any]:
        candidates = selection.candidates
        risk_note_counts = Counter(note for item in candidates for note in item.risk_notes if note)
        behavior_tag_counts = Counter(tag for item in candidates for tag in item.behavior_tags if tag)
        pending_count = sum(item.lifecycle_status == "data_pending" for item in candidates)
        strict_count = sum(item.passed for item in candidates)
        available_volume_ratio_count = sum(item.quote.volume_ratio is not None for item in candidates)
        available_intraday_average_count = sum(
            item.quote.intraday_average_price is not None for item in candidates
        )
        return {
            "model": model,
            "temperature": 0,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 A 股尾盘筛选结果解释器。只能根据输入的真实候选和规则证据总结，"
                        "不得新增股票、不得编造字段、不得给出买卖、仓位、止损或止盈指令。"
                        "只返回 JSON：summary、key_points、risk_points、data_gaps。"
                        "每个列表最多 4 条，每条不超过 40 个汉字；重复原因必须合并计数。"
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
                            "candidate_summary": {
                                "total": len(candidates),
                                "strict_passed": strict_count,
                                "observation_candidates": len(candidates) - strict_count,
                                "data_pending": pending_count,
                                "volume_ratio_available": available_volume_ratio_count,
                                "intraday_average_available": available_intraday_average_count,
                            },
                            "risk_note_counts": dict(sorted(risk_note_counts.items())),
                            "behavior_tag_counts": dict(sorted(behavior_tag_counts.items())),
                            "limitations": tuple(dict.fromkeys(selection.limitations)),
                            "source_evidence": tuple(dict.fromkeys(selection.source_evidence)),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

    @staticmethod
    def _parse_content(content: Any) -> Any:
        if not isinstance(content, str):
            return content
        text = content.strip()
        if not text:
            raise ValueError("模型没有返回最终分析内容")
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().lower() in {"```", "```json"}:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        object_start = text.find("{")
        if object_start < 0:
            raise ValueError("模型返回内容中没有 JSON 对象")
        parsed, _ = json.JSONDecoder().raw_decode(text[object_start:])
        return parsed

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
        risk_counts = Counter(note for item in candidates for note in item.risk_notes if note)
        risks = tuple(
            f"{note}：{count} 只" if count > 1 else note
            for note, count in sorted(risk_counts.items())
        )
        key_points = (
            f"当前筛选保留 {len(candidates)} 只股票，均来自真实行情快照。",
            f"其中 {positive} 只带有尾盘强势或溢价观察标签。",
            "候选排序只反映当前规则通过结果，不代表未来收益预测。",
        )
        title = {
            "unconfigured": "AI 未配置 · 已输出规则解析",
            "output_invalid": "AI 返回格式异常 · 已输出规则解析",
            "error": "AI 接口暂不可用 · 已输出规则解析",
        }.get(status, "已输出规则解析")
        return LateSessionAIAnalysis(
            status=status,
            mode="rule_interpretation",
            title=title,
            summary="当前结果已按筛选规则、字段完整性和尾盘行为标签完成结构化解析；未将规则通过误写成买卖结论。",
            key_points=key_points,
            risk_points=risks or ("需结合后续真实分时数据继续核验。",),
            data_gaps=tuple(dict.fromkeys(selection.limitations)),
            candidate_count=len(candidates),
            source_evidence=selection.source_evidence,
            observed_at=selection.server_time,
            reason="未配置 OpenAI 兼容接口" if status == "unconfigured" else None,
        )
