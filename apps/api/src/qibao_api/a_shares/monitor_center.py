from __future__ import annotations

import hashlib
import json
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AlertDeliveryQueue:
    """Run each delivery independently so one channel cannot hide an alert."""

    def __init__(self, *, tts=None, feishu=None) -> None:
        self.tts = tts
        self.feishu = feishu

    def dispatch(self, alert: dict[str, Any]) -> dict[str, str]:
        states = {"in_app": "sent", "tts": "未配置", "feishu": "未配置"}
        for name, delivery in (("tts", self.tts), ("feishu", self.feishu)):
            if delivery is None:
                continue
            try:
                delivery(alert)
            except Exception:  # delivery failures are persisted per channel
                states[name] = "failed"
            else:
                states[name] = "sent"
        return states


class MonitorCenterService:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"rules": [], "alerts": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"rules": [], "alerts": []}

    def _save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def save_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        if not rule.get("id") or not rule.get("conditions"):
            raise ValueError("监控规则缺少标识或触发条件")
        value = {"enabled": True, "cooldown_seconds": 60, **rule}
        with self._lock:
            self._state["rules"] = [item for item in self._state["rules"] if item["id"] != value["id"]]
            self._state["rules"].append(value)
            self._save()
        return value

    @staticmethod
    def _matches(snapshot: dict[str, Any], conditions: dict[str, Any]) -> bool:
        for field, operators in conditions.items():
            value: Any = snapshot
            for segment in field.split("."):
                if not isinstance(value, dict) or segment not in value:
                    value = None
                    break
                value = value[segment]
            if value is None:
                return False
            for operator, expected in operators.items():
                if operator == "gte" and not value >= expected:
                    return False
                if operator == "gt" and not value > expected:
                    return False
                if operator == "lte" and not value <= expected:
                    return False
                if operator == "lt" and not value < expected:
                    return False
                if operator == "eq" and value != expected:
                    return False
        return True

    def evaluate(
        self,
        snapshot: dict[str, Any],
        observed_at: datetime,
        *,
        topic: str | None = None,
    ) -> dict[str, Any] | None:
        if observed_at.tzinfo is None:
            raise ValueError("观测时间必须带时区")
        with self._lock:
            for rule in self._state["rules"]:
                topics = rule.get("topics") or []
                if (
                    not rule.get("enabled", True)
                    or (topics and topic not in topics)
                    or not self._matches(snapshot, rule["conditions"])
                ):
                    continue
                identity = f"{rule['id']}|{snapshot.get('symbol', '')}|{json.dumps(snapshot, sort_keys=True, ensure_ascii=False)}"
                input_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
                prior = next((item for item in reversed(self._state["alerts"]) if item["rule_id"] == rule["id"] and item["symbol"] == snapshot.get("symbol")), None)
                if prior and prior["input_hash"] == input_hash:
                    elapsed = observed_at.timestamp() - datetime.fromisoformat(prior["observed_at"]).timestamp()
                    if elapsed < int(rule.get("cooldown_seconds", 60)):
                        return None
                channels = rule.get("channels")
                delivery = {"in_app": "pending", "tts": "pending", "feishu": "pending"}
                if isinstance(channels, dict):
                    if channels.get("in_app") is False:
                        delivery["in_app"] = "未配置"
                    if channels.get("tts") is False:
                        delivery["tts"] = "未配置"
                    if channels.get("feishu") is False:
                        delivery["feishu"] = "未配置"
                alert = {"alert_id": f"alert-{input_hash[:24]}", "rule_id": rule["id"], "topic": topic, "symbol": snapshot.get("symbol"), "observed_at": observed_at.astimezone(timezone.utc).isoformat(), "input_hash": input_hash, "snapshot": snapshot, "delivery": delivery}
                if isinstance(channels, dict) and channels.get("in_app") is True:
                    delivery["in_app"] = "sent"
                self._state["alerts"].append(alert)
                self._save()
                return alert
        return None

    def deliver(self, alert_id: str, *, feishu_configured: bool, tts_ok: bool = True) -> dict[str, str]:
        with self._lock:
            alert = next(item for item in self._state["alerts"] if item["alert_id"] == alert_id)
            alert["delivery"]["in_app"] = "sent"
            alert["delivery"]["tts"] = "sent" if tts_ok else "failed"
            alert["delivery"]["feishu"] = "queued" if feishu_configured else "未配置"
            self._save()
            return alert["delivery"]

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._state["alerts"][-max(1, limit):]))

    def pending_tts(
        self, limit: int = 10, *, max_age_seconds: int = 300
    ) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc).timestamp() - max(1, max_age_seconds)
        with self._lock:
            return [
                dict(item)
                for item in reversed(self._state["alerts"])
                if item["delivery"].get("tts") == "pending"
                and datetime.fromisoformat(item["observed_at"]).timestamp() >= cutoff
            ][: max(1, limit)]

    def complete_delivery(self, alert_id: str, channel: str, status: str, reason: str | None = None) -> dict[str, str]:
        if channel not in {"tts", "feishu", "in_app"}:
            raise ValueError("不支持的告警投递通道")
        if status not in {"pending", "playing", "sent", "failed", "未配置"}:
            raise ValueError("不支持的告警投递状态")
        with self._lock:
            alert = next((item for item in self._state["alerts"] if item["alert_id"] == alert_id), None)
            if alert is None:
                raise KeyError(alert_id)
            alert["delivery"][channel] = status
            if reason:
                alert.setdefault("delivery_reason", {})[channel] = reason
            self._save()
            return dict(alert["delivery"])


class MonitorRuntime:
    """Consume verified realtime snapshots and persist independent alerts."""

    def __init__(self, bus, service: MonitorCenterService, *, feishu=None) -> None:
        self.bus = bus
        self.service = service
        self.feishu = feishu
        self._subscription = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._subscription = self.bus.subscribe({"market_overview", "quant_strategy", "news_events", "late_session_candidates"})
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="monitor-runtime", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._subscription is not None:
            self.bus.unsubscribe(self._subscription)
            self._subscription = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._subscription.get(timeout=0.5) if self._subscription is not None else None
            except queue.Empty:
                continue
            if not event or not isinstance(event.get("payload"), dict):
                continue
            alert = self.service.evaluate(
                event["payload"],
                datetime.fromisoformat(event["observed_at"]),
                topic=event.get("kind"),
            )
            if (
                alert is None
                or self.feishu is None
                or alert["delivery"].get("feishu") != "pending"
            ):
                continue
            try:
                result = self.feishu.send(
                    title=f"A 股监控告警：{alert.get('symbol') or '全市场'}",
                    lines=(f"规则：{alert['rule_id']}", f"观测时间：{alert['observed_at']}", f"告警编号：{alert['alert_id']}"),
                )
                self.service.complete_delivery(alert["alert_id"], "feishu", result.status)
            except Exception as error:
                self.service.complete_delivery(alert["alert_id"], "feishu", "failed", str(error))
