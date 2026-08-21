from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
            value = snapshot.get(field)
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

    def evaluate(self, snapshot: dict[str, Any], observed_at: datetime) -> dict[str, Any] | None:
        if observed_at.tzinfo is None:
            raise ValueError("观测时间必须带时区")
        with self._lock:
            for rule in self._state["rules"]:
                if not rule.get("enabled", True) or not self._matches(snapshot, rule["conditions"]):
                    continue
                identity = f"{rule['id']}|{snapshot.get('symbol', '')}|{json.dumps(snapshot, sort_keys=True, ensure_ascii=False)}"
                input_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
                prior = next((item for item in reversed(self._state["alerts"]) if item["rule_id"] == rule["id"] and item["symbol"] == snapshot.get("symbol")), None)
                if prior and prior["input_hash"] == input_hash:
                    elapsed = observed_at.timestamp() - datetime.fromisoformat(prior["observed_at"]).timestamp()
                    if elapsed < int(rule.get("cooldown_seconds", 60)):
                        return None
                alert = {"alert_id": f"alert-{input_hash[:24]}", "rule_id": rule["id"], "symbol": snapshot.get("symbol"), "observed_at": observed_at.astimezone(timezone.utc).isoformat(), "input_hash": input_hash, "snapshot": snapshot, "delivery": {"in_app": "pending", "tts": "pending", "feishu": "pending"}}
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
