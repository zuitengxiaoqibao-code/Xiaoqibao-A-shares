from __future__ import annotations

import hashlib
import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from qibao_api.zhongshu.decision_ai import DecisionAIEvidence, DecisionAIRequest


class RealtimeAITriggerQueue:
    """Dedupe verified snapshot changes and produce evidence-bound explanations."""

    def __init__(
        self,
        bus,
        ai_gateway=None,
        *,
        observability=None,
        max_workers: int = 1,
        dedupe_seconds: int = 60,
    ) -> None:
        if max_workers < 1 or dedupe_seconds < 1:
            raise ValueError("max_workers and dedupe_seconds must be positive")
        self.bus = bus
        self.ai_gateway = ai_gateway
        self.observability = observability
        self.dedupe_seconds = dedupe_seconds
        self._subscription = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="realtime-ai")
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._previous: dict[str, dict[str, Any]] = {}
        self._dedupe: dict[str, float] = {}
        self._submitted = 0
        self._completed = 0
        self._failed = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._subscription = self.bus.subscribe({"market_overview", "quant_strategy", "company_research", "news_events", "late_session_candidates"})
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="realtime-ai-trigger", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._subscription is not None:
            self.bus.unsubscribe(self._subscription)
            self._subscription = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        self._executor.shutdown(wait=True, cancel_futures=True)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": "running" if self._thread is not None and self._thread.is_alive() else "stopped",
                "submitted": self._submitted,
                "completed": self._completed,
                "failed": self._failed,
                "dedupe_window_seconds": self.dedupe_seconds,
                "pending": max(0, self._submitted - self._completed - self._failed),
            }

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._subscription.get(timeout=0.5) if self._subscription is not None else None
            except queue.Empty:
                continue
            if event is None:
                continue
            trigger = self._build_trigger(event)
            if trigger is None:
                continue
            with self._lock:
                self._submitted += 1
            self._executor.submit(self._analyze, trigger)

    def _build_trigger(self, event: dict[str, Any]) -> dict[str, Any] | None:
        kind = str(event.get("kind") or "")
        payload = event.get("payload")
        if not kind or not isinstance(payload, dict):
            return None
        now = datetime.now(timezone.utc)
        snapshot_hash = _hash(payload)
        previous = self._previous.get(kind)
        fingerprint = _fingerprint(kind, payload)
        previous_fingerprint = previous.get("fingerprint") if previous else None
        if previous is not None and fingerprint == previous_fingerprint:
            self._previous[kind] = {"fingerprint": fingerprint, "hash": snapshot_hash, "payload": payload}
            return None
        reason = _trigger_reason(kind, payload, previous.get("payload") if previous else None)
        if reason is None:
            self._previous[kind] = {"fingerprint": fingerprint, "hash": snapshot_hash, "payload": payload}
            return None
        dedupe_key = f"{kind}:{reason}:{snapshot_hash}"
        now_mono = now.timestamp()
        last = self._dedupe.get(dedupe_key)
        if last is not None and now_mono - last < self.dedupe_seconds:
            return None
        self._dedupe[dedupe_key] = now_mono
        self._previous[kind] = {"fingerprint": fingerprint, "hash": snapshot_hash, "payload": payload}
        evidence, conclusions = _evidence(kind, payload, previous.get("payload") if previous else None, reason)
        return {
            "trigger_id": f"realtime-ai-{snapshot_hash[:24]}",
            "kind": kind,
            "reason": reason,
            "observed_at": event.get("observed_at") or now.isoformat(),
            "source": event.get("source") or "unknown",
            "freshness": event.get("freshness") or "unknown",
            "input_snapshot_hash": snapshot_hash,
            "previous_snapshot_hash": previous.get("hash") if previous else None,
            "formula_version": _formula_version(payload),
            "coverage_percent": _coverage(payload),
            "missing_fields": _missing_fields(payload),
            "evidence": evidence,
            "deterministic_conclusions": conclusions,
        }

    def _analyze(self, trigger: dict[str, Any]) -> None:
        try:
            request = DecisionAIRequest(
                generated_at=_parse_datetime(trigger["observed_at"]),
                evidence=tuple(DecisionAIEvidence(**item) for item in trigger["evidence"]),
                deterministic_conclusions=tuple(trigger["deterministic_conclusions"]),
            )
            if self.ai_gateway is None:
                result = None
            else:
                result = self.ai_gateway.explain(request)
            payload = {
                **trigger,
                "status": result.status if result is not None else "unavailable",
                "explanation": result.explanation if result is not None else None,
                "statements": [item.model_dump(mode="json") for item in result.statements] if result is not None else [],
                "provider": result.provider if result is not None else "unconfigured",
                "model": result.model if result is not None else "none",
                "prompt_version": result.prompt_version if result is not None else "realtime-ai-v1",
                "generated_at": result.generated_at.isoformat() if result is not None else datetime.now(timezone.utc).isoformat(),
                "evidence_ids": list(result.evidence_ids) if result is not None else [item["evidence_id"] for item in trigger["evidence"]],
                "fallback": result is None or result.status != "ready",
            }
            self.bus.publish(
                "ai_analysis",
                payload,
                observed_at=_parse_datetime(payload["generated_at"]),
                source=payload["provider"],
                freshness="live",
            )
            if self.observability is not None:
                self.observability.record(
                    "realtime_ai",
                    status="ready" if not payload["fallback"] else "unavailable",
                    observed_at=_parse_datetime(payload["generated_at"]),
                    coverage_percent=payload["coverage_percent"],
                    metadata={"kind": trigger["kind"], "reason": trigger["reason"], "input_snapshot_hash": trigger["input_snapshot_hash"]},
                )
            with self._lock:
                self._completed += 1
        except Exception as error:
            with self._lock:
                self._failed += 1
            if self.observability is not None:
                self.observability.record("realtime_ai", status="error", error_code=type(error).__name__, metadata={"trigger_id": trigger.get("trigger_id")})


def _hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fingerprint(kind: str, payload: dict[str, Any]) -> str:
    if kind == "market_overview":
        selected = {
            "as_of": payload.get("as_of"),
            "regime": payload.get("regime", {}).get("regime"),
            "risk": payload.get("regime", {}).get("risk_score"),
            "emotion": payload.get("regime", {}).get("emotion_score"),
            "anomalies": [item.get("anomaly_id") for item in payload.get("anomalies", [])[:20]],
            "news": [item.get("event_id") for item in payload.get("live_feed", [])[:20]],
        }
    elif kind == "quant_strategy":
        selected = {
            "as_of": payload.get("as_of"),
            "formula_version": payload.get("formula_version"),
            "regime": payload.get("regime", {}).get("regime"),
            "risk": payload.get("regime", {}).get("risk_score"),
            "candidates": [(item.get("symbol"), item.get("status"), item.get("strategy_score")) for item in payload.get("candidates", [])[:20]],
        }
    elif kind == "company_research":
        selected = {"symbol": payload.get("symbol"), "snapshot_id": payload.get("research_version", {}).get("snapshot_id")}
    elif kind == "late_session_candidates":
        selected = {
            "trading_date": payload.get("trading_date"),
            "monitor_stage": payload.get("monitor_stage"),
            "data_state": payload.get("data_state"),
            "candidates": [
                (item.get("quote", {}).get("symbol"), item.get("lifecycle_status"), item.get("rule_bitmap"), item.get("passed"))
                for item in payload.get("candidates", [])[:50]
            ],
            "invalidated": [item.get("quote", {}).get("symbol") for item in payload.get("invalidated_candidates", [])[:50]],
        }
    else:
        selected = {"event_ids": [item.get("event_id") for item in payload.get("events", [])[:50]], "snapshot_id": payload.get("snapshot_id")}
    return _hash(selected)


def _trigger_reason(kind: str, payload: dict[str, Any], previous: dict[str, Any] | None) -> str | None:
    if previous is None:
        return "initial_verified_snapshot"
    if kind == "market_overview" and payload.get("regime", {}).get("regime") != previous.get("regime", {}).get("regime"):
        return "market_regime_changed"
    if kind == "quant_strategy":
        current = payload.get("regime", {}).get("risk_score")
        old = previous.get("regime", {}).get("risk_score")
        try:
            if current is not None and old is not None and (float(current) < 45 <= float(old) or float(current) >= 65 > float(old) or float(current) >= 65 and float(old) < 65):
                return "risk_threshold_crossed"
        except (TypeError, ValueError):
            pass
        current_ids = {(item.get("symbol"), item.get("status")) for item in payload.get("candidates", [])}
        old_ids = {(item.get("symbol"), item.get("status")) for item in previous.get("candidates", [])}
        if current_ids != old_ids:
            return "candidate_status_changed"
    if kind == "company_research":
        return "research_version_changed"
    if kind == "late_session_candidates":
        current = {
            (item.get("quote", {}).get("symbol"), item.get("lifecycle_status"), item.get("rule_bitmap"), item.get("passed"))
            for item in payload.get("candidates", [])
        }
        old = {
            (item.get("quote", {}).get("symbol"), item.get("lifecycle_status"), item.get("rule_bitmap"), item.get("passed"))
            for item in previous.get("candidates", [])
        }
        if current != old:
            return "late_session_candidate_lifecycle_changed"
        invalidated = {item.get("quote", {}).get("symbol") for item in payload.get("invalidated_candidates", [])}
        old_invalidated = {item.get("quote", {}).get("symbol") for item in previous.get("invalidated_candidates", [])}
        if invalidated != old_invalidated:
            return "late_session_candidate_invalidated"
        return "late_session_stage_changed"
    if kind == "news_events":
        return "verified_news_changed"
    return "verified_snapshot_changed"


def _evidence(kind: str, payload: dict[str, Any], previous: dict[str, Any] | None, reason: str) -> tuple[list[dict[str, str]], list[str]]:
    evidence: list[dict[str, str]] = []
    if kind == "market_overview":
        fields = ("regime.regime", "regime.risk_score", "regime.emotion_score", "market_data.phase", "status")
    elif kind == "quant_strategy":
        fields = ("formula_version", "regime.regime", "regime.risk_score", "regime.coverage_percent", "candidate_funnel.completeness")
    elif kind == "company_research":
        fields = ("symbol", "as_of", "status", "research_version.snapshot_id", "evidence_coverage")
    elif kind == "late_session_candidates":
        fields = ("trading_date", "monitor_stage", "data_state", "source_quality", "candidates", "invalidated_candidates")
    else:
        fields = ("snapshot_id", "events")
    for field in fields:
        value = _path(payload, field)
        if value is not None:
            evidence.append({"evidence_id": f"{kind}:{field}", "summary": f"{field} = {json.dumps(value, ensure_ascii=False, sort_keys=True)}"})
    if previous is not None:
        evidence.append({"evidence_id": f"{kind}:change", "summary": f"本次变化原因：{reason}；输入快照已与上一版本比较"})
    conclusions = [f"{kind} 已产生经核验的 {reason} 变化。", "仅根据输入快照和来源证据解释，不生成交易指令。"]
    return evidence, conclusions


def _path(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _formula_version(payload: dict[str, Any]) -> str | None:
    return payload.get("formula_version") or payload.get("regime", {}).get("formula_version")


def _coverage(payload: dict[str, Any]) -> float | None:
    for path in ("regime.coverage_percent", "evidence_coverage", "evidence_ledger.0.coverage_percent"):
        value = _path(payload, path)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            continue
    return None


def _missing_fields(payload: dict[str, Any]) -> list[str]:
    values = payload.get("missing_data") or payload.get("warnings") or payload.get("reasons") or []
    return [str(item) for item in values if str(item).strip()]


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
