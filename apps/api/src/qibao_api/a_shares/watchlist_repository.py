from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from qibao_api.contracts.instruments import validate_a_share_code


@dataclass(frozen=True)
class WatchlistSnapshot:
    symbols: tuple[str, ...]
    updated_at: datetime | None


class WatchlistRepository:
    """Atomic, portable configuration storage for the user's A-share watchlist."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> WatchlistSnapshot:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("watchlist must be an object")
            symbols = self._clean(payload.get("symbols", []))
            raw_updated = payload.get("updated_at")
            updated_at = (
                datetime.fromisoformat(raw_updated)
                if isinstance(raw_updated, str) else None
            )
            return WatchlistSnapshot(symbols=symbols, updated_at=updated_at)
        except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return WatchlistSnapshot(symbols=(), updated_at=None)

    def save(self, symbols: list[str] | tuple[str, ...]) -> WatchlistSnapshot:
        cleaned = self._clean(symbols, strict=True)
        updated_at = datetime.now(timezone.utc)
        payload = {
            "symbols": list(cleaned),
            "updated_at": updated_at.isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
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
        return WatchlistSnapshot(symbols=cleaned, updated_at=updated_at)

    @staticmethod
    def _clean(values: object, *, strict: bool = False) -> tuple[str, ...]:
        if not isinstance(values, (list, tuple)):
            if strict:
                raise ValueError("自选股列表格式不正确")
            return ()
        result: list[str] = []
        for value in values:
            if not isinstance(value, str):
                if strict:
                    raise ValueError("自选股必须使用六位 A 股代码")
                continue
            symbol = value.strip()
            try:
                validate_a_share_code(symbol)
            except ValueError as error:
                if strict:
                    raise ValueError("自选股必须使用六位 A 股代码") from error
                continue
            if symbol not in result:
                result.append(symbol)
        return tuple(result)
