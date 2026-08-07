from __future__ import annotations

import importlib.util
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import Lock
from typing import Any, Literal


class TdxProfessionalDataUnavailable(RuntimeError):
    """Raised when local TDX professional data is unavailable or invalid."""


@dataclass(frozen=True)
class TdxQuantPythonAvailability:
    status: Literal["detected_only", "unavailable"]
    detail: str
    module_path: str | None = None


_METHOD_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "get_financial_data": re.compile(r"^Fn\d+$", re.IGNORECASE),
    "get_financial_data_by_date": re.compile(r"^Fn\d+$", re.IGNORECASE),
    "get_gpjy_value": re.compile(r"^GP\d+$", re.IGNORECASE),
    "get_gpjy_value_by_date": re.compile(r"^GP\d+$", re.IGNORECASE),
    "get_bkjy_value": re.compile(r"^BK\d+$", re.IGNORECASE),
    "get_bkjy_value_by_date": re.compile(r"^BK\d+$", re.IGNORECASE),
    "get_scjy_value": re.compile(r"^SC\d+$", re.IGNORECASE),
    "get_scjy_value_by_date": re.compile(r"^SC\d+$", re.IGNORECASE),
    "get_gp_one_data": re.compile(r"^GO\d+$", re.IGNORECASE),
}

_STOCK_METHODS = {
    "get_financial_data",
    "get_financial_data_by_date",
    "get_gpjy_value",
    "get_gpjy_value_by_date",
    "get_bkjy_value",
    "get_bkjy_value_by_date",
    "get_gp_one_data",
}
_RANGE_METHODS = {
    "get_financial_data",
    "get_gpjy_value",
    "get_bkjy_value",
    "get_scjy_value",
}
_DATE_METHODS = {
    "get_financial_data_by_date",
    "get_gpjy_value_by_date",
    "get_bkjy_value_by_date",
    "get_scjy_value_by_date",
}


@dataclass(frozen=True)
class TdxProfessionalRow:
    method: str
    symbol: str | None
    values: dict[str, Decimal | str]
    fetched_at: datetime
    source: str = "tdx-local-rpc-professional"


def _canonical_field(method: str, field: str) -> str:
    digits = re.search(r"\d+$", field)
    if digits is None:
        return field
    if method.startswith("get_financial_data"):
        return f"Fn{digits.group()}"
    prefix = {
        "get_gpjy_value": "GP",
        "get_gpjy_value_by_date": "GP",
        "get_bkjy_value": "BK",
        "get_bkjy_value_by_date": "BK",
        "get_scjy_value": "SC",
        "get_scjy_value_by_date": "SC",
        "get_gp_one_data": "GO",
    }[method]
    return f"{prefix}{digits.group()}"


def validate_tdx_professional_fields(
    method: str,
    fields: tuple[str, ...],
) -> tuple[str, ...]:
    pattern = _METHOD_FIELD_PATTERNS.get(method)
    if pattern is None:
        raise ValueError("unsupported TDX professional method")
    if not fields:
        raise ValueError("TDX professional table_list must not be empty")
    result: list[str] = []
    seen: set[str] = set()
    for raw in fields:
        field = str(raw).strip()
        if not pattern.fullmatch(field):
            raise ValueError("invalid TDX professional field")
        canonical = _canonical_field(method, field)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return tuple(result)


def _symbol(value: Any) -> str | None:
    if value in (None, "", "--", "-"):
        return None
    text = str(value).strip().split(".", 1)[0]
    return text if len(text) == 6 and text.isdigit() else None


def _value(value: Any) -> Decimal | str | None:
    if value in (None, "", "--", "-"):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        text = str(value).strip()
        return text or None
    return number if number.is_finite() else None


def _rows_from_value(value: Any) -> tuple[Mapping[str, Any], ...]:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            records = value.to_dict(orient="records")
        except (TypeError, ValueError):
            records = None
        if isinstance(records, list):
            return tuple(item for item in records if isinstance(item, Mapping))
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, Mapping))
    if not isinstance(value, Mapping):
        return ()
    for nested_key in ("Data", "Rows", "Value"):
        nested = value.get(nested_key)
        if nested is not None and nested is not value:
            rows = _rows_from_value(nested)
            if rows:
                return rows
    rows: list[Mapping[str, Any]] = []
    for key, item in value.items():
        code = _symbol(key)
        if code is None:
            continue
        if isinstance(item, list):
            rows.extend(
                {"Code": key, **dict(row)}
                for row in item
                if isinstance(row, Mapping)
            )
            continue
        if hasattr(item, "to_dict") and callable(item.to_dict):
            try:
                records = item.to_dict(orient="records")
            except (TypeError, ValueError):
                records = None
            if isinstance(records, list):
                rows.extend(
                    {"Code": key, **dict(row)}
                    for row in records
                    if isinstance(row, Mapping)
                )
            continue
        if not isinstance(item, Mapping):
            continue
        list_lengths = {
            len(column) for column in item.values() if isinstance(column, list)
        }
        if len(list_lengths) == 1 and list_lengths:
            count = next(iter(list_lengths))
            for index in range(count):
                row = {"Code": key}
                for field, column in item.items():
                    row[field] = column[index] if isinstance(column, list) else column
                rows.append(row)
        else:
            rows.append({"Code": key, **dict(item)})
    return tuple(rows)


def parse_tdx_professional_rows(
    payload: Any,
    *,
    method: str,
    fetched_at: datetime,
    source: str = "tdx-local-rpc-professional",
) -> tuple[TdxProfessionalRow, ...]:
    pattern = _METHOD_FIELD_PATTERNS.get(method)
    if pattern is None:
        raise ValueError("unsupported TDX professional method")
    if isinstance(payload, Mapping) and "ErrorId" in payload:
        if str(payload.get("ErrorId")) != "0":
            raise TdxProfessionalDataUnavailable("TDX professional response is invalid")
        value = payload.get("Value")
    else:
        value = payload
    rows = _rows_from_value(value)
    if not rows:
        raise TdxProfessionalDataUnavailable("TDX professional response is empty")
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    parsed: list[TdxProfessionalRow] = []
    for row in rows:
        values: dict[str, Decimal | str] = {}
        for key, raw in row.items():
            field = str(key).strip()
            if not pattern.fullmatch(field):
                continue
            value = _value(raw)
            if value is not None:
                values[_canonical_field(method, field)] = value
        if not values:
            continue
        parsed.append(TdxProfessionalRow(
            method=method,
            symbol=_symbol(
                row.get("Code")
                or row.get("StockCode")
                or row.get("Symbol")
                or row.get("证券代码")
            ),
            values=values,
            fetched_at=fetched_at,
            source=source,
        ))
    if not parsed:
        raise TdxProfessionalDataUnavailable(
            "TDX professional response has no verified table fields"
        )
    return tuple(parsed)


def _stock_code(value: str) -> str:
    text = str(value).strip().upper()
    if re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", text):
        return text
    if not re.fullmatch(r"\d{6}", text):
        raise ValueError("invalid TDX stock code")
    exchange = "SH" if text.startswith(("6", "9")) else "BJ" if text.startswith(("4", "8")) else "SZ"
    return f"{text}.{exchange}"


def _time(value: str) -> str:
    text = str(value).strip().replace("-", "").replace("/", "")
    if not text:
        return ""
    if re.fullmatch(r"\d{8}", text):
        return f"{text}000000"
    if re.fullmatch(r"\d{14}", text):
        return text
    raise ValueError("invalid TDX professional time")


class TdxLocalProfessionalSource:
    """Read-only adapter for TdxQuant professional table methods."""

    def __init__(
        self,
        rpc_factory,
        *,
        fallback=None,
        clock=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.rpc_factory = rpc_factory
        self.fallback = fallback
        self.clock = clock

    def fetch(
        self,
        *,
        method: str,
        fields: tuple[str, ...],
        stock_codes: tuple[str, ...] = (),
        start_time: str = "",
        end_time: str = "",
        report_type: str = "report_time",
        year: int = 0,
        mmdd: int = 0,
    ) -> tuple[TdxProfessionalRow, ...]:
        table_list = validate_tdx_professional_fields(method, fields)
        if method in _STOCK_METHODS and not stock_codes:
            raise ValueError("TDX professional stock_list must not be empty")
        params: dict[str, Any] = {"table_list": list(table_list)}
        if method in _STOCK_METHODS:
            params["stock_list"] = [_stock_code(code) for code in stock_codes]
        if method in _RANGE_METHODS:
            params["start_time"] = _time(start_time)
            params["end_time"] = _time(end_time)
        if method == "get_financial_data":
            if report_type not in {"report_time", "announce_time"}:
                raise ValueError("invalid TDX financial report_type")
            params["report_type"] = report_type
        if method in _DATE_METHODS:
            params["year"] = int(year)
            params["mmdd"] = int(mmdd)
        rpc = self.rpc_factory()
        if rpc is None or not getattr(rpc, "available", lambda: False)():
            close = getattr(rpc, "close", None)
            if callable(close):
                close()
            if self.fallback is not None:
                return self.fallback.fetch(
                    method=method,
                    fields=table_list,
                    stock_codes=stock_codes,
                    start_time=start_time,
                    end_time=end_time,
                    report_type=report_type,
                    year=year,
                    mmdd=mmdd,
                )
            raise TdxProfessionalDataUnavailable("TDX local bridge unavailable")

        try:
            payload = rpc.call(method, params)
            return parse_tdx_professional_rows(
                payload,
                method=method,
                fetched_at=self.clock(),
            )
        except Exception as error:
            if self.fallback is None:
                if isinstance(error, TdxProfessionalDataUnavailable):
                    raise
                raise TdxProfessionalDataUnavailable(
                    "TDX local bridge call unavailable"
                ) from error
            close = getattr(rpc, "close", None)
            if callable(close):
                close()
            return self.fallback.fetch(
                method=method,
                fields=table_list,
                stock_codes=stock_codes,
                start_time=start_time,
                end_time=end_time,
                report_type=report_type,
                year=year,
                mmdd=mmdd,
            )
        finally:
            close = getattr(rpc, "close", None)
            if callable(close):
                close()


class TdxQuantPythonSource:
    """Lazy read-only adapter for the official local TdxQuant Python module."""

    _ALLOWED_METHODS = frozenset(_METHOD_FIELD_PATTERNS)

    def __init__(
        self,
        roots: tuple[str | Path, ...],
        *,
        module_loader=None,
        clock=lambda: datetime.now(timezone.utc),
        failure_cooldown: timedelta = timedelta(seconds=10),
    ) -> None:
        self.roots = tuple(Path(root) for root in roots)
        self._custom_module_loader = module_loader is not None
        self.module_loader = module_loader or self._load_module
        self.clock = clock
        self.failure_cooldown = failure_cooldown
        self._module_cache: dict[Path, Any] = {}
        self._module_cache_lock = Lock()
        self._failure_until: datetime | None = None
        self._failure_lock = Lock()

    @staticmethod
    def _load_module(path: Path):
        spec = importlib.util.spec_from_file_location(
            f"qibao_tdx_quant_{abs(hash(str(path)))}",
            path,
        )
        if spec is None or spec.loader is None:
            raise TdxProfessionalDataUnavailable("TDX Python module cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _module_path(self) -> Path | None:
        for root in self.roots:
            for relative in (
                Path("PYPlugins/user/tqcenter.py"),
                Path("PYPlugins/sys/tqcenter.py"),
            ):
                path = root / relative
                dll_path = path.parents[1] / "TPythClient.dll"
                if path.is_file() and dll_path.is_file():
                    return path
                if self._custom_module_loader and path.parent.exists():
                    # Tests and embedders may provide a loader that does not need
                    # the vendor DLL or a real Python module on disk.
                    return path
        if self._custom_module_loader and self.roots:
            return self.roots[0] / "PYPlugins/user/tqcenter.py"
        return None

    def fetch(
        self,
        *,
        method: str,
        fields: tuple[str, ...],
        stock_codes: tuple[str, ...] = (),
        start_time: str = "",
        end_time: str = "",
        report_type: str = "report_time",
        year: int = 0,
        mmdd: int = 0,
    ) -> tuple[TdxProfessionalRow, ...]:
        if method not in self._ALLOWED_METHODS:
            raise ValueError("unsupported TDX professional method")
        table_list = validate_tdx_professional_fields(method, fields)
        if method in _STOCK_METHODS and not stock_codes:
            raise ValueError("TDX professional stock_list must not be empty")
        path = self._module_path()
        if path is None:
            raise TdxProfessionalDataUnavailable(
                "TDX Python professional module unavailable"
            )
        self._raise_if_failure_cooling_down()
        try:
            module = self._load_cached_module(path)
        except TdxProfessionalDataUnavailable:
            raise
        except Exception as error:
            raise TdxProfessionalDataUnavailable(
                "TDX Python professional module unavailable"
            ) from error
        tq = getattr(module, "tq", None)
        if tq is None:
            raise TdxProfessionalDataUnavailable(
                "TDX Python professional client unavailable"
            )
        try:
            tq.initialize(str(path))
            function = getattr(tq, method, None)
            if not callable(function):
                raise TdxProfessionalDataUnavailable(
                    "TDX Python professional method unavailable"
                )
            kwargs: dict[str, Any] = {"field_list": list(table_list)}
            if method in _STOCK_METHODS:
                kwargs["stock_list"] = [_stock_code(code) for code in stock_codes]
            if method in _RANGE_METHODS:
                kwargs["start_time"] = start_time
                kwargs["end_time"] = end_time
            if method == "get_financial_data":
                if report_type not in {"report_time", "announce_time"}:
                    raise ValueError("invalid TDX financial report_type")
                kwargs["report_type"] = report_type
            if method in _DATE_METHODS:
                kwargs["year"] = int(year)
                kwargs["mmdd"] = int(mmdd)
            payload = function(**kwargs)
            rows = parse_tdx_professional_rows(
                payload,
                method=method,
                fetched_at=self.clock(),
                source="tdx-python-professional",
            )
            self._clear_failure_cooldown()
            return rows
        except TdxProfessionalDataUnavailable:
            self._remember_failure()
            raise
        except Exception as error:
            self._remember_failure()
            raise TdxProfessionalDataUnavailable(
                "TDX Python professional call unavailable"
            ) from error
        finally:
            close = getattr(tq, "close", None)
            if callable(close):
                close()

    def _load_cached_module(self, path: Path):
        cache_key = path.resolve(strict=False)
        with self._module_cache_lock:
            cached = self._module_cache.get(cache_key)
            if cached is not None:
                return cached
            module = self.module_loader(path)
            self._module_cache[cache_key] = module
            return module

    def _raise_if_failure_cooling_down(self) -> None:
        with self._failure_lock:
            if self._failure_until is not None and self.clock() < self._failure_until:
                raise TdxProfessionalDataUnavailable(
                    "TDX Python professional call unavailable"
                )

    def _remember_failure(self) -> None:
        with self._failure_lock:
            self._failure_until = self.clock() + self.failure_cooldown

    def _clear_failure_cooldown(self) -> None:
        with self._failure_lock:
            self._failure_until = None


def inspect_tdx_quant_python_roots(
    roots: tuple[str | Path, ...],
) -> TdxQuantPythonAvailability:
    """Report whether the official read-only Python module is discoverable.

    Discovery is intentionally filesystem-only.  It does not import the vendor
    module or initialize a TDX connection, so settings pages remain fast and do
    not turn a detected DLL into a false ``ready`` data claim.
    """
    source = TdxQuantPythonSource(tuple(roots))
    path = source._module_path()
    if path is None:
        return TdxQuantPythonAvailability(
            status="unavailable",
            detail="未发现官方 TdxQuant Python 模块和配套 DLL",
        )
    return TdxQuantPythonAvailability(
        status="detected_only",
        detail="已发现官方模块；等待通达信进程返回可验证专业字段",
        module_path=str(path),
    )
