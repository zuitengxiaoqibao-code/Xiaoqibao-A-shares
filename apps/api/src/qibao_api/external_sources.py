from __future__ import annotations

import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from qibao_api.credential_protection import CredentialProtector


@dataclass(frozen=True, slots=True)
class ExternalSourceDefinition:
    source_id: str
    name: str
    description: str
    capabilities: tuple[str, ...]
    key_label: str
    key_url: str
    base_url: str


@dataclass(frozen=True, slots=True)
class ExternalCapabilityDefinition:
    key: str
    label: str


ExternalCapabilityStatus = Literal["ready", "limited", "unavailable", "unverified"]


EXTERNAL_CAPABILITY_DEFINITIONS: dict[str, tuple[ExternalCapabilityDefinition, ...]] = {
    "tickflow": (
        ExternalCapabilityDefinition("realtime_quotes", "实时行情"),
        ExternalCapabilityDefinition("daily_klines", "日线 K 线"),
        ExternalCapabilityDefinition("minute_klines", "分钟 K 线"),
        ExternalCapabilityDefinition("intraday", "分时"),
        ExternalCapabilityDefinition("ex_factors", "除权因子"),
        ExternalCapabilityDefinition("financials", "财务数据"),
        ExternalCapabilityDefinition("market_depth", "五档行情"),
    ),
    "fuyao": (
        ExternalCapabilityDefinition("realtime_quotes", "实时行情"),
        ExternalCapabilityDefinition("daily_klines", "日线 K 线"),
        ExternalCapabilityDefinition("minute_klines", "分钟 K 线"),
        ExternalCapabilityDefinition("financials", "财务数据"),
    ),
    "tushare": (
        ExternalCapabilityDefinition("realtime_quotes", "实时行情"),
        ExternalCapabilityDefinition("daily_klines", "日线 K 线"),
        ExternalCapabilityDefinition("minute_klines", "分钟 K 线"),
        ExternalCapabilityDefinition("intraday", "分时"),
        ExternalCapabilityDefinition("ex_factors", "除权因子"),
        ExternalCapabilityDefinition("financials", "财务数据"),
    ),
}


BUILTIN_EXTERNAL_SOURCES: tuple[ExternalSourceDefinition, ...] = (
    ExternalSourceDefinition(
        "tickflow", "TickFlow", "实时行情、日线与分钟线、分时、除权因子、财务和五档行情备用接口。",
        ("实时行情", "日线 K 线", "分钟 K 线", "分时", "除权因子", "财务数据", "五档行情"),
        "TickFlow API Key", "https://docs.tickflow.org/zh-Hans", "https://api.tickflow.org/v1",
    ),
    ExternalSourceDefinition(
        "fuyao", "扶摇", "同花顺风格 REST 数据备用接口，支持行情、K 线和财务等能力。",
        ("实时行情", "日线 K 线", "分钟 K 线", "财务数据"),
        "扶摇 API Key", "https://fuyao.ai", "https://api.fuyao.ai/v1",
    ),
    ExternalSourceDefinition(
        "tushare", "Tushare", "标准化证券数据备用接口，支持行情、日线、分钟线、财务和复权数据。",
        ("实时行情", "日线 K 线", "分钟 K 线", "分时", "除权因子", "财务数据"),
        "Tushare Token", "https://tushare.pro/document/1?doc_id=130", "https://api.tushare.pro",
    ),
)


class ExternalDataSourceRepository:
    def __init__(self, path: Path, *, protector: CredentialProtector | None = None) -> None:
        self.path = path
        self.protector = protector
        self._lock = threading.RLock()
        self._values: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._values is not None:
            return self._values
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._values = raw if isinstance(raw, dict) else {}
        except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
            self._values = {}
        return self._values

    @staticmethod
    def _definition(source_id: str) -> ExternalSourceDefinition:
        for item in BUILTIN_EXTERNAL_SOURCES:
            if item.source_id == source_id:
                return item
        raise KeyError(source_id)

    def _key(self, source_id: str) -> str | None:
        item = self._load().get(source_id, {})
        protected = item.get("api_key_protected")
        if isinstance(protected, str) and self.protector is not None:
            try:
                return self.protector.unprotect(protected)
            except (OSError, ValueError):
                return None
        value = item.get("api_key")
        return value if isinstance(value, str) and value.strip() else None

    def enabled_key(self, source_id: str) -> str | None:
        """Return a credential for internal adapters only when explicitly enabled."""
        self._definition(source_id)
        with self._lock:
            item = self._load().get(source_id, {})
            if not bool(item.get("enabled")):
                return None
            return self._key(source_id)

    @staticmethod
    def _capability_checks(
        definition: ExternalSourceDefinition,
        saved: dict[str, Any],
        key: str | None,
    ) -> list[dict[str, Any]]:
        persisted = saved.get("capability_checks")
        by_key = {
            str(item.get("key")): item
            for item in persisted
            if isinstance(item, dict) and item.get("key")
        } if isinstance(persisted, list) else {}
        default_status: ExternalCapabilityStatus = "unverified"
        default_detail = "尚未进行接口权限检测" if key else "请先填写 API Key，再检测接口权限"
        output: list[dict[str, Any]] = []
        for capability in EXTERNAL_CAPABILITY_DEFINITIONS[definition.source_id]:
            item = by_key.get(capability.key, {})
            status = item.get("status")
            if status not in {"ready", "limited", "unavailable", "unverified"}:
                status = default_status
            output.append({
                "key": capability.key,
                "label": capability.label,
                "status": status,
                "detail": str(item.get("detail") or default_detail),
                "reason_code": str(item.get("reason_code") or "not_tested"),
                "tested_at": item.get("tested_at"),
            })
        return output

    def list_views(self) -> list[dict[str, Any]]:
        with self._lock:
            values = self._load()
            output = []
            for definition in BUILTIN_EXTERNAL_SOURCES:
                saved = values.get(definition.source_id, {})
                key = self._key(definition.source_id)
                last_status = saved.get("last_status")
                status = last_status if key and last_status in {"ready", "limited", "unavailable"} else ("configured" if key else "unconfigured")
                output.append({
                    "source_id": definition.source_id,
                    "name": definition.name,
                    "description": definition.description,
                    "capabilities": list(definition.capabilities),
                    "key_label": definition.key_label,
                    "key_url": definition.key_url,
                    "configured": bool(key),
                    "enabled": bool(saved.get("enabled", bool(key))),
                    "api_key_hint": f"****{key[-4:]}" if key else None,
                    "status": status,
                    "capability_checks": self._capability_checks(definition, saved, key),
                    "last_tested_at": saved.get("last_tested_at"),
                    "last_error": saved.get("last_error"),
                })
            return output

    def save(self, source_id: str, *, api_key: str, enabled: bool) -> dict[str, Any]:
        definition = self._definition(source_id)
        key = api_key.strip()
        if not key:
            raise ValueError("API Key 不能为空")
        with self._lock:
            values = self._load()
            payload: dict[str, Any] = {"enabled": bool(enabled)}
            if self.protector is None:
                payload["api_key"] = key
            else:
                payload["api_key_protected"] = self.protector.protect(key)
            values[definition.source_id] = payload
            self._write(values)
            return next(item for item in self.list_views() if item["source_id"] == source_id)

    def clear(self, source_id: str) -> dict[str, Any]:
        self._definition(source_id)
        with self._lock:
            values = self._load()
            values.pop(source_id, None)
            self._write(values)
            return next(item for item in self.list_views() if item["source_id"] == source_id)

    def update_test(
        self,
        source_id: str,
        *,
        status: str,
        reason: str | None,
        capability_checks: list[dict[str, Any]] | None = None,
    ) -> None:
        with self._lock:
            values = self._load()
            item = values.setdefault(source_id, {})
            item["last_tested_at"] = datetime.now(timezone.utc).isoformat()
            item["last_error"] = reason
            item["last_status"] = status
            if capability_checks is not None:
                item["capability_checks"] = capability_checks
            self._write(values)

    def _write(self, values: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(values, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary_path.unlink(missing_ok=True)
            raise


class ExternalDataSourceService:
    _PROBE_TIMEOUT_SECONDS = 5

    def __init__(self, repository: ExternalDataSourceRepository) -> None:
        self.repository = repository

    @staticmethod
    def _tickflow_quotes_url(base_url: str) -> str:
        """Accept either the documented API root or its ``/v1`` form."""
        return ExternalDataSourceService._tickflow_api_url(base_url, "quotes", {"symbols": "000001.SH"})

    @staticmethod
    def _tickflow_api_url(base_url: str, path: str, params: dict[str, Any]) -> str:
        normalized = base_url.rstrip("/")
        if not normalized.lower().endswith("/v1"):
            normalized = f"{normalized}/v1"
        query = urllib.parse.urlencode(params)
        return f"{normalized}/{path.lstrip('/')}?{query}" if query else f"{normalized}/{path.lstrip('/')}"

    @staticmethod
    def _is_permission_limited(source_id: str, reason: str | None) -> bool:
        if not reason:
            return False
        lowered = reason.casefold()
        return any(marker in lowered for marker in (
            "permission", "access denied", "forbidden", "unauthoriz",
            "权限", "没有接口", "无权限", "未开通",
        ))

    @staticmethod
    def _payload_message(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        for field in ("message", "msg", "detail", "error"):
            value = payload.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @classmethod
    def _decode_payload(cls, raw: bytes | str) -> Any:
        try:
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            return json.loads(text) if text else {}
        except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError):
            return None

    @classmethod
    def _http_error_reason(cls, error: urllib.error.HTTPError) -> str:
        message = None
        try:
            payload = cls._decode_payload(error.read())
            message = cls._payload_message(payload)
        except (OSError, ValueError):
            pass
        return f"接口返回 HTTP {error.code}：{message}" if message else f"接口返回 HTTP {error.code}"

    @classmethod
    def _classify_failure(
        cls,
        reason: str,
        *,
        status_code: int | None = None,
    ) -> tuple[ExternalCapabilityStatus, str, str]:
        detail = reason.strip()[:240] or "接口检测失败"
        if status_code in {401, 403} or cls._is_permission_limited("", detail):
            return "limited", detail, "permission_denied"
        if status_code == 404 or any(marker in detail.casefold() for marker in (
            "not found", "不存在", "未找到", "unsupported", "not enabled", "接口不存在",
        )):
            return "unavailable", detail, "endpoint_unavailable"
        return "unavailable", detail, "request_failed"

    @classmethod
    def _perform_probe(
        cls,
        request: urllib.request.Request,
        *,
        key: str,
    ) -> tuple[ExternalCapabilityStatus, str, str]:
        try:
            with urllib.request.urlopen(request, timeout=cls._PROBE_TIMEOUT_SECONDS) as response:
                status_code = int(getattr(response, "status", 200))
                payload = cls._decode_payload(response.read())
                if not 200 <= status_code < 300:
                    return cls._classify_failure(
                        f"接口返回 HTTP {status_code}",
                        status_code=status_code,
                    )
                if not isinstance(payload, dict):
                    return "unavailable", "接口响应不是 JSON 对象", "invalid_response"
                code = payload.get("code")
                if code not in (None, 0, "0"):
                    return cls._classify_failure(cls._payload_message(payload) or f"接口返回错误 {code}")
                if "data" not in payload:
                    return "unavailable", "接口响应缺少 data 字段", "invalid_response"
                return "ready", "接口响应正常", "ok"
        except urllib.error.HTTPError as error:
            status, detail, reason_code = cls._classify_failure(cls._http_error_reason(error), status_code=error.code)
            return status, detail.replace(key, "[已隐藏]"), reason_code
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason = str(error.reason if isinstance(error, urllib.error.URLError) else error) or "网络不可达"
            status, detail, reason_code = cls._classify_failure(reason)
            return status, detail.replace(key, "[已隐藏]"), reason_code

    @staticmethod
    def _tickflow_probe_request(source: ExternalSourceDefinition, capability_key: str, key: str) -> urllib.request.Request:
        probes: dict[str, tuple[str, dict[str, Any]]] = {
            "realtime_quotes": ("quotes", {"symbols": "000001.SH"}),
            "daily_klines": ("klines", {"symbol": "000001.SH", "period": "1d", "count": 1}),
            "minute_klines": ("klines", {"symbol": "000001.SH", "period": "5m", "count": 1}),
            "intraday": ("klines/intraday", {"symbol": "000001.SH", "period": "1m", "count": 1}),
            "ex_factors": ("klines/ex-factors", {"symbols": "000001.SH"}),
            "financials": ("financials/metrics", {"symbols": "000001.SH", "latest": "true"}),
            "market_depth": ("depth", {"symbol": "000001.SH"}),
        }
        path, params = probes[capability_key]
        headers = {"User-Agent": "XiaoQiBao/1.0", "Accept": "application/json", "x-api-key": key}
        return urllib.request.Request(
            ExternalDataSourceService._tickflow_api_url(source.base_url, path, params),
            headers=headers,
            method="GET",
        )

    @staticmethod
    def _tushare_probe_request(source: ExternalSourceDefinition, capability_key: str, key: str) -> urllib.request.Request:
        specs: dict[str, tuple[str, dict[str, Any], str]] = {
            "realtime_quotes": ("rt_k", {"ts_code": "000001.SZ"}, "ts_code,last_price"),
            "daily_klines": ("daily", {"ts_code": "000001.SZ", "start_date": "20240101", "end_date": "20240102"}, "ts_code,trade_date,close"),
            "minute_klines": ("stk_mins", {"ts_code": "000001.SZ", "start_date": "20240101", "end_date": "20240102", "freq": "5min"}, "ts_code,trade_time,close"),
            "intraday": ("stk_mins", {"ts_code": "000001.SZ", "start_date": "20240101", "end_date": "20240102", "freq": "1min"}, "ts_code,trade_time,close"),
            "ex_factors": ("adj_factor", {"ts_code": "000001.SZ", "start_date": "20240101", "end_date": "20240102"}, "ts_code,trade_date,adj_factor"),
            "financials": ("fina_indicator", {"ts_code": "000001.SZ", "period": "20231231"}, "ts_code,end_date,eps"),
        }
        api_name, params, fields = specs[capability_key]
        body = json.dumps({"api_name": api_name, "token": key, "params": params, "fields": fields}).encode("utf-8")
        headers = {"User-Agent": "XiaoQiBao/1.0", "Accept": "application/json", "Content-Type": "application/json"}
        return urllib.request.Request(source.base_url, data=body, headers=headers, method="POST")

    def _probe_capability(self, source: ExternalSourceDefinition, key: str, capability: ExternalCapabilityDefinition) -> dict[str, Any]:
        tested_at = datetime.now(timezone.utc).isoformat()
        if source.source_id == "fuyao":
            return {
                "key": capability.key,
                "label": capability.label,
                "status": "unverified",
                "detail": "扶摇公开接口协议尚未核验，暂不探测权限",
                "reason_code": "protocol_unverified",
                "tested_at": tested_at,
            }
        try:
            request = (
                self._tickflow_probe_request(source, capability.key, key)
                if source.source_id == "tickflow"
                else self._tushare_probe_request(source, capability.key, key)
            )
            status, detail, reason_code = self._perform_probe(request, key=key)
        except Exception as error:  # noqa: BLE001
            status, detail, reason_code = self._classify_failure(str(error) or "接口检测失败")
        return {
            "key": capability.key,
            "label": capability.label,
            "status": status,
            "detail": detail,
            "reason_code": reason_code,
            "tested_at": tested_at,
        }

    def _probe_capabilities(self, source: ExternalSourceDefinition, key: str) -> list[dict[str, Any]]:
        definitions = EXTERNAL_CAPABILITY_DEFINITIONS[source.source_id]
        with ThreadPoolExecutor(max_workers=min(7, len(definitions)), thread_name_prefix="external-capability") as executor:
            futures = [executor.submit(self._probe_capability, source, key, capability) for capability in definitions]
            return [future.result() for future in futures]

    def _compatibility_checks(
        self,
        source: ExternalSourceDefinition,
        *,
        ok: bool,
        reason: str | None,
    ) -> list[dict[str, Any]]:
        status: ExternalCapabilityStatus = "ready" if ok else "limited" if self._is_permission_limited(source.source_id, reason) else "unavailable"
        detail = "接口响应正常" if ok else (reason or "接口检测失败")
        return [
            {
                "key": capability.key,
                "label": capability.label,
                "status": status,
                "detail": detail[:240],
                "reason_code": "ok" if ok else "permission_denied" if status == "limited" else "request_failed",
                "tested_at": datetime.now(timezone.utc).isoformat(),
            }
            for capability in EXTERNAL_CAPABILITY_DEFINITIONS[source.source_id]
        ]

    @staticmethod
    def _aggregate_status(source: ExternalSourceDefinition, key: str, checks: list[dict[str, Any]]) -> str:
        if not key:
            return "unconfigured"
        statuses = [item.get("status") for item in checks]
        if statuses and all(status == "ready" for status in statuses):
            return "ready"
        if "limited" in statuses:
            return "limited"
        if "unavailable" in statuses:
            return "unavailable"
        return "configured"

    @staticmethod
    def _aggregate_reason(checks: list[dict[str, Any]]) -> str | None:
        failed = [item for item in checks if item.get("status") not in {"ready", "unverified"}]
        if not failed:
            return None
        details = {str(item.get("detail") or "接口检测失败") for item in failed}
        statuses = {item.get("status") for item in failed}
        if len(details) == 1 and statuses == {"unavailable"}:
            return next(iter(details))
        limited = sum(item.get("status") == "limited" for item in failed)
        unavailable = sum(item.get("status") == "unavailable" for item in failed)
        parts = []
        if limited:
            parts.append(f"{limited} 项无权限")
        if unavailable:
            parts.append(f"{unavailable} 项不可用")
        first_detail = str(failed[0].get("detail") or "接口检测失败")
        return f"权限检测：{'、'.join(parts)}；{first_detail}"

    def _probe(self, source: ExternalSourceDefinition, key: str) -> tuple[bool, str | None]:
        capability = EXTERNAL_CAPABILITY_DEFINITIONS[source.source_id][0]
        result = self._probe_capability(source, key, capability)
        return result["status"] == "ready", None if result["status"] == "ready" else str(result["detail"])

    def test(self, source_id: str) -> dict[str, Any]:
        definition = self.repository._definition(source_id)
        view = next(item for item in self.repository.list_views() if item["source_id"] == source_id)
        key = self.repository._key(source_id)
        if not key:
            return {**view, "status": "unconfigured", "reason": "尚未填写 API Key"}
        # Keep compatibility with callers that override the legacy single-probe hook.
        if getattr(self._probe, "__func__", None) is ExternalDataSourceService._probe:
            checks = self._probe_capabilities(definition, key)
        else:
            try:
                ok, reason = self._probe(definition, key)
            except Exception as error:  # noqa: BLE001
                ok, reason = False, str(error) or "接口检测失败"
            checks = self._compatibility_checks(definition, ok=ok, reason=reason)
        status = self._aggregate_status(definition, key, checks)
        reason = self._aggregate_reason(checks)
        self.repository.update_test(
            source_id,
            status=status,
            reason=reason,
            capability_checks=checks,
        )
        return {**next(item for item in self.repository.list_views() if item["source_id"] == source_id), "status": status, "reason": reason}
