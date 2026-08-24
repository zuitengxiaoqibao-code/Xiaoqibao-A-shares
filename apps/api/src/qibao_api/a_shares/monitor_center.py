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
    SUPPORTED_OPERATORS = frozenset({"eq", "gt", "gte", "lt", "lte"})
    SUPPORTED_LOGIC = frozenset({"all", "any", "n_of"})

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        default = {"rules": [], "alerts": [], "active_conditions": {}, "condition_states": {}}
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
        state.setdefault("condition_states", {})
        normalized_rules = []
        for rule in state["rules"]:
            try:
                normalized_rules.append(self.validate_rule(rule))
            except ValueError:
                normalized_rules.append(rule)
        state["rules"] = normalized_rules
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
    def _parse_timestamp(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else None

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
        alert.setdefault("recovery_reason", None)
        alert.setdefault("recovery_alert_id", None)
        alert.setdefault("delivery", {})
        alert.setdefault("delivery_reason", {})
        alert.setdefault("retry_count", {})
        return alert

    def _save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    @classmethod
    def normalize_rule(cls, rule: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(rule, dict):
            raise ValueError("监控规则必须是对象")
        value = dict(rule)
        conditions = value.get("conditions")
        if isinstance(conditions, dict):
            normalized_conditions = []
            for field, operators in conditions.items():
                if not isinstance(operators, dict):
                    raise ValueError("规则条件格式不正确")
                for operator, expected in operators.items():
                    normalized_conditions.append({"field": field, "op": operator, "value": expected})
            conditions = normalized_conditions
        elif isinstance(conditions, list):
            conditions = [dict(item) if isinstance(item, dict) else item for item in conditions]
        value["conditions"] = conditions
        value.setdefault("logic", "all")
        value.setdefault("confirm_count", 1)
        value.setdefault("confirm_window_seconds", 10)
        value.setdefault("cooldown_seconds", 60)
        value.setdefault("freshness_seconds", 120)
        value.setdefault("require_freshness", False)
        value.setdefault("severity", "warning")
        value.setdefault("enabled", True)
        value.setdefault("topics", [])
        value.setdefault("channels", {})
        return value

    @classmethod
    def validate_rule(cls, rule: dict[str, Any]) -> dict[str, Any]:
        value = cls.normalize_rule(rule)
        if not str(value.get("id", "")).strip() or not str(value.get("name", "")).strip():
            raise ValueError("监控规则缺少标识或名称")
        conditions = value.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            raise ValueError("规则至少需要一个触发条件")
        logic = value.get("logic")
        if logic not in cls.SUPPORTED_LOGIC:
            raise ValueError("规则逻辑必须是 all、any 或 n_of")
        if logic == "n_of":
            try:
                n = int(value.get("n"))
            except (TypeError, ValueError) as error:
                raise ValueError("n_of 规则必须提供 n") from error
            if n < 1 or n > len(conditions):
                raise ValueError("n_of 规则的 n 必须在条件数量范围内")
            value["n"] = n
        for condition in conditions:
            if not isinstance(condition, dict) or not str(condition.get("field", "")).strip():
                raise ValueError("规则条件缺少字段路径")
            operator = condition.get("op", condition.get("operator"))
            if operator not in cls.SUPPORTED_OPERATORS:
                raise ValueError("不支持的规则比较符")
            if "value" not in condition and "expected" not in condition:
                raise ValueError("规则条件缺少阈值")
            condition["field"] = str(condition["field"]).strip()
            condition["op"] = operator
            condition["value"] = condition.get("value", condition.get("expected"))
        for field, minimum, message in (
            ("confirm_count", 1, "确认次数必须大于等于 1"),
            ("confirm_window_seconds", 1, "确认窗口必须大于等于 1 秒"),
            ("cooldown_seconds", 0, "冷却时间不能小于 0 秒"),
            ("freshness_seconds", 1, "数据新鲜度必须大于等于 1 秒"),
        ):
            try:
                number = int(value.get(field))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{field} 必须是数字") from error
            if number < minimum:
                raise ValueError(message)
            value[field] = number
        if value.get("severity") not in {"critical", "warning", "info"}:
            raise ValueError("告警级别必须是 critical、warning 或 info")
        return value

    def save_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        value = self.validate_rule(rule)
        with self._lock:
            self._state["rules"] = [item for item in self._state["rules"] if item["id"] != value["id"]]
            self._state["rules"].append(value)
            self._save()
        return value

    def _close_rule_alerts(self, rule_id: str, reason: str) -> None:
        recovered_at = datetime.now(timezone.utc).isoformat()
        for alert in self._state.get("alerts", []):
            if alert.get("rule_id") != rule_id or alert.get("state") != "active":
                continue
            alert["state"] = "recovered"
            alert["recovered_at"] = recovered_at
            alert["recovery_reason"] = reason
        for key in list(self._state.get("active_conditions", {})):
            if key.startswith(f"{rule_id}|"):
                self._state["active_conditions"].pop(key, None)
                self._state["condition_states"].pop(key, None)

    def set_rule_enabled(self, rule_id: str, enabled: bool) -> dict[str, Any]:
        if not isinstance(enabled, bool):
            raise ValueError("规则启用状态必须是布尔值")
        with self._lock:
            rule = next((item for item in self._state["rules"] if item.get("id") == rule_id), None)
            if rule is None:
                raise KeyError("监控规则不存在")
            rule["enabled"] = enabled
            if not enabled:
                self._close_rule_alerts(rule_id, "规则已暂停")
            self._save()
            return self.validate_rule(rule)

    def delete_rule(self, rule_id: str) -> dict[str, str]:
        with self._lock:
            if not any(item.get("id") == rule_id for item in self._state["rules"]):
                raise KeyError("监控规则不存在")
            self._close_rule_alerts(rule_id, "规则已删除")
            self._state["rules"] = [item for item in self._state["rules"] if item.get("id") != rule_id]
            self._save()
        return {"status": "deleted", "rule_id": rule_id}

    def rule_views(self) -> list[dict[str, Any]]:
        operator_names = {"eq": "等于", "gt": "大于", "gte": "大于等于", "lt": "小于", "lte": "小于等于"}
        with self._lock:
            views = []
            for stored in self._state.get("rules", []):
                try:
                    rule = self.validate_rule(stored)
                except ValueError as error:
                    view = dict(stored)
                    view["validation_state"] = "invalid"
                    view["validation_error"] = str(error)
                    views.append(view)
                    continue
                summaries = [
                    f"{item['field']} {operator_names[item['op']]} {item['value']}"
                    for item in rule["conditions"]
                ]
                view = dict(rule)
                view["validation_state"] = "valid"
                view["condition_summary"] = f" {rule['logic']} ".join(summaries)
                views.append(view)
            return views

    @classmethod
    def matches_rule(cls, snapshot: dict[str, Any], rule: dict[str, Any]) -> bool:
        conditions = rule.get("conditions", [])
        results = [cls._matches(snapshot, {item["field"]: {item["op"]: item["value"]}}) for item in conditions]
        logic = rule.get("logic", "all")
        if logic == "any":
            return any(results)
        if logic == "n_of":
            return sum(results) >= int(rule.get("n", 1))
        return all(results)

    @staticmethod
    def _is_fresh(snapshot: dict[str, Any], observed_at: datetime, rule: dict[str, Any]) -> bool:
        if not rule.get("require_freshness", False):
            return True
        raw_observed = snapshot.get("observed_at") or snapshot.get("as_of")
        if not raw_observed:
            return False
        try:
            snapshot_time = datetime.fromisoformat(str(raw_observed))
        except ValueError:
            return False
        if snapshot_time.tzinfo is None:
            return False
        age = observed_at.astimezone(timezone.utc).timestamp() - snapshot_time.astimezone(timezone.utc).timestamp()
        return age >= 0 and age <= int(rule.get("freshness_seconds", 120))

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
                    or not self._is_fresh(snapshot, observed_at, rule)
                    or not self.matches_rule(snapshot, rule)
                ):
                    continue
                state_key = self._condition_key(rule["id"], snapshot.get("symbol"), topic)
                condition_state = self._state["condition_states"].setdefault(state_key, {})
                previous_observed = self._parse_timestamp(condition_state.get("last_observed_at"))
                elapsed = observed_at.timestamp() - previous_observed.timestamp() if previous_observed else None
                if elapsed is None or elapsed < 0 or elapsed > int(rule.get("confirm_window_seconds", 10)):
                    condition_state["confirm_count"] = 1
                    condition_state["first_observed_at"] = observed_at.astimezone(timezone.utc).isoformat()
                else:
                    condition_state["confirm_count"] = int(condition_state.get("confirm_count", 0)) + 1
                condition_state["last_observed_at"] = observed_at.astimezone(timezone.utc).isoformat()
                last_triggered = self._parse_timestamp(condition_state.get("last_trigger_at"))
                self._save()
                if int(condition_state["confirm_count"]) < int(rule.get("confirm_count", 1)):
                    continue
                if last_triggered and observed_at.timestamp() - last_triggered.timestamp() < int(rule.get("cooldown_seconds", 60)):
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
                condition_state["last_trigger_at"] = alert["observed_at"]
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
                if rule is None or not self._is_fresh(snapshot, observed_at, rule):
                    continue
                recovery = rule.get("recovery")
                if isinstance(recovery, dict) and recovery.get("enabled", True):
                    recovery_rule = self.normalize_rule(
                        {
                            "id": rule["id"],
                            "name": rule.get("name", "恢复条件"),
                            "logic": recovery.get("logic", "all"),
                            "n": recovery.get("n"),
                            "conditions": recovery.get("conditions"),
                        }
                    )
                    if not self.matches_rule(snapshot, recovery_rule):
                        continue
                elif self.matches_rule(snapshot, rule):
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
                self._state["condition_states"].pop(key, None)
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
        self._subscription = self.bus.subscribe(
            {
                "market_overview",
                "quant_strategy",
                "news_events",
                "late_session_candidates",
                "stock_observation",
                "data_sources",
            }
        )
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
