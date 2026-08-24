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
        default = {"rules": [], "alerts": [], "active_conditions": {}}
        if not self.path.exists():
            return default
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default
        if not isinstance(state, dict):
            return default
        state.setdefault("rules", [])
        state.setdefault("alerts", [])
        state.setdefault("active_conditions", {})
        for alert in state["alerts"]:
            self._normalize_alert(alert)
            if alert.get("state") == "active":
                key = self._condition_key(alert.get("rule_id"), alert.get("symbol"), alert.get("topic"))
                state["active_conditions"].setdefault(
                    key,
                    {
                        "input_hash": alert.get("input_hash"),
                        "alert_id": alert.get("alert_id"),
                        "rule_id": alert.get("rule_id"),
                        "symbol": alert.get("symbol"),
                        "topic": alert.get("topic"),
                    },
                )
        return state

    @staticmethod
    def _condition_key(rule_id: str | None, symbol: str | None, topic: str | None) -> str:
        return "|".join((str(rule_id or ""), str(symbol or ""), str(topic or "")))

    @staticmethod
    def _normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
        severity = alert.get("severity")
        alert["severity"] = severity if severity in {"critical", "warning", "info"} else "warning"
        state = alert.get("state")
        alert["state"] = state if state in {"active", "recovered"} else "active"
        alert["confirmed"] = bool(alert.get("confirmed", False))
        alert.setdefault("confirmed_at", None)
        alert.setdefault("confirmed_by", None)
        alert["trigger_count"] = max(1, int(alert.get("trigger_count", 1)))
        alert.setdefault("recovered_at", None)
        alert.setdefault("recovery_alert_id", None)
        alert.setdefault("delivery", {})
        alert.setdefault("delivery_reason", {})
        alert.setdefault("retry_count", {})
        return alert

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
                prior_count = int(prior.get("trigger_count", 0)) if prior else 0
                severity = rule.get("severity", "warning")
                if severity not in {"critical", "warning", "info"}:
                    severity = "warning"
                alert = {
                    "alert_id": f"alert-{input_hash[:24]}",
                    "rule_id": rule["id"],
                    "topic": topic,
                    "symbol": snapshot.get("symbol"),
                    "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
                    "input_hash": input_hash,
                    "snapshot": snapshot,
                    "delivery": delivery,
                    "severity": severity,
                    "state": "active",
                    "confirmed": False,
                    "confirmed_at": None,
                    "confirmed_by": None,
                    "trigger_count": prior_count + 1,
                    "recovered_at": None,
                    "recovery_alert_id": None,
                    "delivery_reason": {},
                    "retry_count": {},
                }
                if isinstance(channels, dict) and channels.get("in_app") is True:
                    delivery["in_app"] = "sent"
                self._state["alerts"].append(alert)
                self._state["active_conditions"][self._condition_key(rule["id"], alert["symbol"], topic)] = {
                    "input_hash": input_hash,
                    "alert_id": alert["alert_id"],
                    "rule_id": rule["id"],
                    "symbol": alert["symbol"],
                    "topic": topic,
                }
                self._save()
                return alert
        return None

    def evaluate_recovery(
        self,
        snapshot: dict[str, Any],
        observed_at: datetime,
        *,
        topic: str | None = None,
    ) -> dict[str, Any] | None:
        if observed_at.tzinfo is None:
            raise ValueError("观测时间必须带时区")
        symbol = snapshot.get("symbol")
        with self._lock:
            active = list(self._state.get("active_conditions", {}).items())
            for key, condition in active:
                if condition.get("symbol") != symbol or (
                    topic is not None and condition.get("topic") != topic
                ):
                    continue
                rule = next((item for item in self._state["rules"] if item.get("id") == condition.get("rule_id")), None)
                if rule is None or self._matches(snapshot, rule.get("conditions", {})):
                    continue
                original = next((item for item in self._state["alerts"] if item.get("alert_id") == condition.get("alert_id")), None)
                if original is None or original.get("state") != "active":
                    self._state["active_conditions"].pop(key, None)
                    continue
                recovered_at = observed_at.astimezone(timezone.utc).isoformat()
                original["state"] = "recovered"
                original["recovered_at"] = recovered_at
                recovery_hash = hashlib.sha256(
                    f"recovery|{original['alert_id']}|{recovered_at}".encode("utf-8")
                ).hexdigest()
                recovery = {
                    "alert_id": f"recovery-{recovery_hash[:24]}",
                    "rule_id": original["rule_id"],
                    "topic": original.get("topic"),
                    "symbol": symbol,
                    "observed_at": recovered_at,
                    "input_hash": recovery_hash,
                    "snapshot": snapshot,
                    "delivery": {"in_app": "sent", "tts": "未配置", "feishu": "未配置"},
                    "severity": "info",
                    "state": "recovered",
                    "confirmed": False,
                    "confirmed_at": None,
                    "confirmed_by": None,
                    "trigger_count": 1,
                    "recovered_at": recovered_at,
                    "recovery_alert_id": original["alert_id"],
                    "delivery_reason": {},
                    "retry_count": {},
                }
                self._state["alerts"].append(recovery)
                self._state["active_conditions"].pop(key, None)
                self._save()
                return recovery
        return None

    def summary(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("摘要时间必须带时区")
        with self._lock:
            alerts = [self._normalize_alert(item) for item in self._state.get("alerts", [])]
            rules = self._state.get("rules", [])
            active = [item for item in alerts if item.get("state") == "active"]
            latest = max(alerts, key=lambda item: item.get("observed_at", ""), default=None)
            failed = sum(1 for item in alerts for status in item.get("delivery", {}).values() if status == "failed")
            pending = sum(1 for item in alerts for status in item.get("delivery", {}).values() if status in {"pending", "queued", "playing"})
            topic_names = {str(item.get("topic")) for item in alerts if item.get("topic")}
            topic_names.update(str(topic) for rule in rules for topic in rule.get("topics", []) if topic)
            topic_names.update(
                {
                    "market_overview",
                    "quant_strategy",
                    "news_events",
                    "late_session_candidates",
                    "stock_observation",
                    "company_research",
                    "data_sources",
                }
            )
            topics = []
            for topic in sorted(topic_names):
                topic_alerts = [item for item in alerts if item.get("topic") == topic]
                topic_active = [item for item in topic_alerts if item.get("state") == "active"]
                severity = "critical" if any(item.get("severity") == "critical" for item in topic_active) else "warning" if topic_active else "ok" if topic_alerts else "no_data"
                topics.append({
                    "topic": topic,
                    "status": severity,
                    "alert_count": len(topic_alerts),
                    "active_count": len(topic_active),
                    "last_alert_at": max((item.get("observed_at") for item in topic_alerts), default=None),
                })
            heartbeat = latest.get("observed_at") if latest else None
            latency_ms = None
            if heartbeat:
                latency_ms = max(0, round((current.astimezone(timezone.utc).timestamp() - datetime.fromisoformat(heartbeat).timestamp()) * 1000, 2))
            return {
                "generated_at": current.astimezone(timezone.utc).isoformat(),
                "service": {
                    "status": "degraded" if failed else "healthy",
                    "last_heartbeat_at": heartbeat,
                    "latency_ms": latency_ms,
                },
                "rules": {"total": len(rules), "enabled": sum(1 for rule in rules if rule.get("enabled", True))},
                "alerts": {
                    "total": len(alerts),
                    "active": len(active),
                    "critical": sum(1 for item in active if item.get("severity") == "critical"),
                    "unconfirmed": sum(1 for item in active if not item.get("confirmed")),
                    "recovered": sum(1 for item in alerts if item.get("state") == "recovered"),
                },
                "delivery": {"pending": pending, "failed": failed},
                "topics": topics,
                "recent_alerts": list(reversed(alerts[-10:])),
            }

    def confirm(self, alert_id: str, *, confirmed_by: str = "用户") -> dict[str, Any]:
        with self._lock:
            alert = next((item for item in self._state["alerts"] if item.get("alert_id") == alert_id), None)
            if alert is None:
                raise KeyError(alert_id)
            alert["confirmed"] = True
            alert["confirmed_at"] = datetime.now(timezone.utc).isoformat()
            alert["confirmed_by"] = confirmed_by.strip() or "用户"
            self._normalize_alert(alert)
            self._save()
            return dict(alert)

    def retry_delivery(self, alert_id: str, channel: str) -> dict[str, Any]:
        if channel not in {"tts", "feishu", "in_app"}:
            raise ValueError("不支持的告警投递通道")
        with self._lock:
            alert = next((item for item in self._state["alerts"] if item.get("alert_id") == alert_id), None)
            if alert is None:
                raise KeyError(alert_id)
            alert.setdefault("retry_count", {})[channel] = int(alert.get("retry_count", {}).get(channel, 0)) + 1
            alert.setdefault("delivery_reason", {}).pop(channel, None)
            alert["delivery"][channel] = "pending"
            self._save()
            return {"delivery": dict(alert["delivery"]), "retry_count": dict(alert["retry_count"]), "delivery_reason": dict(alert.get("delivery_reason", {}))}

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
            if alert is None:
                self.service.evaluate_recovery(
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
