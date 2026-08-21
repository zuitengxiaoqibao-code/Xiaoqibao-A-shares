from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from qibao_api.contracts.data_source import NormalizedBatch


SUPPORTED_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".parquet", ".sqlite", ".sqlite3", ".db", ".duckdb", ".xls", ".xlsx", ".zip"}
_CODE_RE = re.compile(r"^\d{6}(?:\.(?:SH|SZ|BJ))?$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ImportPreview:
    path: str
    format: str
    columns: tuple[str, ...]
    row_count: int
    preview_rows: tuple[dict[str, Any], ...]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ImportResult:
    batch: NormalizedBatch
    quarantined_rows: int
    quarantine_reasons: tuple[str, ...]
    task_id: str


class FileImportService:
    def __init__(self, root: Path, *, max_bytes: int = 250 * 1024 * 1024) -> None:
        self.root = root
        self.max_bytes = max_bytes

    def inspect(self, path: Path) -> ImportPreview:
        path = Path(path)
        self._check_file(path)
        temp_root: Path | None = None
        try:
            candidate = self._unwrap_zip(path)
            if candidate != path:
                temp_root = candidate.parent
            rows, fmt = self._read_rows(candidate)
            if path.suffix.lower() == ".zip":
                fmt = "zip"
            columns = tuple(dict.fromkeys(key for row in rows for key in row))
            return ImportPreview(
                path=str(path), format=fmt, columns=columns, row_count=len(rows),
                preview_rows=tuple(rows[:5]),
            )
        except Exception as error:  # noqa: BLE001
            return ImportPreview(
                path=str(path), format=self._format(path), columns=(), row_count=0,
                preview_rows=(), error=self._message(error),
            )
        finally:
            if temp_root is not None:
                shutil.rmtree(temp_root, ignore_errors=True)

    def ingest(self, path: Path, mapping: dict[str, str], *, task_id: str | None = None) -> ImportResult:
        path = Path(path)
        self._check_file(path)
        task_id = task_id or hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:24]
        temp_root: Path | None = None
        try:
            candidate = self._unwrap_zip(path)
            if candidate != path:
                temp_root = candidate.parent
            rows, _fmt = self._read_rows(candidate)
            normalized: list[dict[str, Any]] = []
            reasons: list[str] = []
            for index, row in enumerate(rows, start=1):
                item = {mapping.get(key, key): value for key, value in row.items()}
                reason = self._validate_row(item)
                if reason is not None:
                    reasons.append(f"第 {index} 行：{reason}")
                    self._write_quarantine(task_id, index, item, reason)
                    continue
                normalized.append(item)
            if not normalized:
                raise ValueError("没有可发布的有效数据行")
            as_of = max(self._parse_date(row["as_of"]) for row in normalized)
            encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            status = "partial" if reasons else "ready"
            batch = NormalizedBatch(
                source_id=f"file:{path.suffix.lower().lstrip('.')}",
                as_of=as_of,
                observed_at=datetime.now(timezone.utc),
                ingested_at=datetime.now(timezone.utc),
                records=tuple(normalized),
                content_hash=hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
                quality_status=status,
            )
            return ImportResult(batch, len(reasons), tuple(reasons), task_id)
        finally:
            if temp_root is not None:
                shutil.rmtree(temp_root, ignore_errors=True)

    def _check_file(self, path: Path) -> None:
        if not path.is_file():
            raise ValueError("文件不存在或不是文件")
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError(f"不支持的文件格式: {path.suffix or '无扩展名'}")
        if path.stat().st_size > self.max_bytes:
            raise ValueError("文件超过 250 MB 限制")

    def _unwrap_zip(self, path: Path) -> Path:
        if path.suffix.lower() != ".zip":
            return path
        target = Path(tempfile.mkdtemp(prefix="qibao-import-"))
        total = 0
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                destination = (target / member.filename).resolve()
                if target.resolve() not in destination.parents and destination != target.resolve():
                    raise ValueError("压缩包包含越界路径")
                total += member.file_size
                if total > self.max_bytes * 4:
                    raise ValueError("解压后文件总大小超过限制")
            archive.extractall(target)
        candidates = sorted(
            item for item in target.rglob("*") if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES - {".zip"}
        )
        if not candidates:
            shutil.rmtree(target, ignore_errors=True)
            raise ValueError("压缩包内没有可识别的数据文件")
        return candidates[0]

    def _read_rows(self, path: Path) -> tuple[list[dict[str, Any]], str]:
        suffix = path.suffix.lower()
        if suffix in {".csv", ".tsv"}:
            return self._read_delimited(path, "\t" if suffix == ".tsv" else None), suffix.lstrip(".")
        if suffix in {".json", ".jsonl"}:
            text = path.read_text(encoding="utf-8-sig")
            if suffix == ".jsonl":
                return [json.loads(line) for line in text.splitlines() if line.strip()], "jsonl"
            payload = json.loads(text)
            if isinstance(payload, dict):
                payload = payload.get("data", payload.get("rows", [payload]))
            if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
                raise ValueError("JSON 必须是对象数组或包含 data/rows 数组")
            return payload, "json"
        if suffix == ".parquet":
            with duckdb.connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM read_parquet(?)", [str(path)]
                ).fetchdf().to_dict(orient="records")
            return rows, "parquet"
        if suffix in {".sqlite", ".sqlite3", ".db"}:
            with sqlite3.connect(path) as connection:
                table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name LIMIT 1"
                ).fetchone()
                if table is None:
                    raise ValueError("SQLite 中没有可读取的数据表")
                cursor = connection.execute(f'SELECT * FROM "{table[0]}"')
                columns = [item[0] for item in cursor.description or ()]
                return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()], "sqlite"
        if suffix == ".duckdb":
            with duckdb.connect(str(path), read_only=True) as connection:
                table = connection.execute("SHOW TABLES").fetchone()
                if table is None:
                    raise ValueError("DuckDB 中没有可读取的数据表")
                rows = connection.execute(f'SELECT * FROM "{table[0]}"').fetchdf().to_dict(orient="records")
            return rows, "duckdb"
        if suffix in {".xls", ".xlsx"}:
            try:
                import pandas as pd
                return pd.read_excel(path).where(lambda frame: frame.notna(), None).to_dict(orient="records"), suffix.lstrip(".")
            except ImportError as error:
                raise ValueError("读取 Excel 需要安装 openpyxl") from error
        raise ValueError(f"不支持的文件格式: {suffix}")

    @staticmethod
    def _read_delimited(path: Path, delimiter: str | None) -> list[dict[str, Any]]:
        raw = path.read_bytes()
        text = None
        for encoding in ("utf-8-sig", "utf-8", "gbk"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise ValueError("文件编码不是 UTF-8 或 GBK")
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter or ",")
        if not reader.fieldnames:
            raise ValueError("文件缺少表头")
        return [dict(row) for row in reader]

    @staticmethod
    def _parse_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value or "").strip().replace("/", "-")
        return date.fromisoformat(text[:10])

    @classmethod
    def _validate_row(cls, row: dict[str, Any]) -> str | None:
        symbol = str(row.get("symbol") or "").strip()
        if not _CODE_RE.fullmatch(symbol):
            return "股票代码无效"
        if "as_of" not in row:
            return "缺少日期字段 as_of"
        try:
            cls._parse_date(row["as_of"])
        except (TypeError, ValueError):
            return "日期字段无效"
        return None

    def _write_quarantine(self, task_id: str, index: int, row: dict[str, Any], reason: str) -> None:
        target = self.root / task_id / "quarantine.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"row": index, "reason": reason, "data": row}, ensure_ascii=False) + "\n")

    @staticmethod
    def _format(path: Path) -> str:
        return path.suffix.lower().lstrip(".") or "unknown"

    @staticmethod
    def _message(error: Exception) -> str:
        return str(error) or "数据文件读取失败"
