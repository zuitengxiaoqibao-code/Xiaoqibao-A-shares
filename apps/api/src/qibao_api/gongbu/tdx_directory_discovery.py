"""Read-only discovery and ranking of local TongDaXin daily-bar directories.

The application may have several TDX installations.  This module deliberately
does not start or control a terminal; it only inspects ``vipdoc/*/lday/*.day``
files and returns the evidence used to choose a source.
"""

from __future__ import annotations

import os
import struct
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from qibao_api.gongbu.tdx_local_daily import _a_share_symbol


KNOWN_TDX_PATHS: tuple[Path, ...] = (Path(r"D:\new_tdx_mock"),)
_DAY_RECORD = struct.Struct("<IIIIIfII")
_EXCHANGES = ("sh", "sz", "bj")


class TdxDirectoryCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    root: Path
    vipdoc_path: Path
    display_name: str
    version_hint: str | None = None
    latest_trade_date: date | None = None
    day_file_count: int = Field(ge=0)
    readable_day_file_count: int = Field(ge=0)
    a_share_coverage_percent: float = Field(ge=0, le=100)
    last_data_update: datetime | None = None
    score: float = Field(ge=0, le=100)
    state: Literal["ready", "partial", "unavailable"]
    reasons: tuple[str, ...] = ()


class TdxDirectoryDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    scanned_at: datetime
    candidates: tuple[TdxDirectoryCandidate, ...] = ()
    active_root: Path | None = None
    active_vipdoc_path: Path | None = None
    state: Literal["ready", "partial", "unavailable"] = "unavailable"


def discover_tdx_directories(
    *,
    known_paths: Sequence[Path] = KNOWN_TDX_PATHS,
    search_roots: Sequence[Path] = (),
    universe_symbols: Sequence[str] = (),
    clock=None,
) -> TdxDirectoryDiscovery:
    """Discover local TDX installations with a bounded, read-only scan."""

    roots: list[Path] = []
    seen: set[str] = set()
    for path in (*known_paths, *search_roots):
        resolved = Path(path).expanduser().resolve(strict=False)
        candidates = _candidate_roots(resolved) if path in known_paths else _scan_roots(resolved)
        for candidate in candidates:
            key = str(candidate).casefold()
            if key not in seen:
                seen.add(key)
                roots.append(candidate)
    raw = tuple(_inspect_root(root, universe_symbols) for root in roots)
    ranked = rank_tdx_directories(raw)
    active = ranked[0] if ranked else None
    observed_at = (clock or (lambda: datetime.now(timezone.utc)))()
    return TdxDirectoryDiscovery(
        scanned_at=observed_at,
        candidates=ranked,
        active_root=active.root if active else None,
        active_vipdoc_path=active.vipdoc_path if active else None,
        state="ready" if ranked and active and active.state == "ready" else "partial" if ranked else "unavailable",
    )


def rank_tdx_directories(candidates: Sequence[TdxDirectoryCandidate]) -> tuple[TdxDirectoryCandidate, ...]:
    """Score candidates by freshness, readability, A-share coverage and activity."""

    if not candidates:
        return ()
    dates = [item.latest_trade_date for item in candidates if item.latest_trade_date]
    newest = max(dates) if dates else None
    max_readable = max((item.readable_day_file_count for item in candidates), default=0)
    max_activity = max(
        (item.last_data_update.timestamp() for item in candidates if item.last_data_update),
        default=0,
    )
    ranked: list[TdxDirectoryCandidate] = []
    for item in candidates:
        freshness = 0.0
        if item.latest_trade_date and newest:
            age_days = max(0, (newest - item.latest_trade_date).days)
            freshness = max(0.0, 100.0 - min(100.0, age_days * 20.0))
        readable = (item.readable_day_file_count / max_readable * 100.0) if max_readable else 0.0
        coverage = item.a_share_coverage_percent
        activity = (
            item.last_data_update.timestamp() / max_activity * 100.0
            if item.last_data_update and max_activity > 0
            else 0.0
        )
        score = round(freshness * 0.40 + readable * 0.30 + coverage * 0.20 + activity * 0.10, 2)
        reasons = (
            f"覆盖率 {coverage:.2f}%",
            f"可读取日线 {item.readable_day_file_count}/{item.day_file_count}",
            f"最新交易日 {item.latest_trade_date.isoformat() if item.latest_trade_date else '未知'}",
        )
        ranked.append(item.model_copy(update={"score": score, "reasons": reasons}))
    ranked.sort(
        key=lambda item: (
            -item.score,
            -(item.latest_trade_date.toordinal() if item.latest_trade_date else 0),
            -item.readable_day_file_count,
            str(item.root).casefold(),
        )
    )
    return tuple(ranked)


def _candidate_roots(path: Path) -> tuple[Path, ...]:
    if path.name.casefold() == "vipdoc" and _has_lday(path):
        return (path.parent,)
    if _has_lday(path / "vipdoc"):
        return (path,)
    if _has_lday(path):
        return (path.parent if path.name.casefold() == "vipdoc" else path,)
    return ()


def _scan_roots(base: Path, max_depth: int = 4) -> tuple[Path, ...]:
    if not base.is_dir():
        return ()
    found: list[Path] = []
    stack: list[tuple[Path, int]] = [(base, 0)]
    while stack:
        current, depth = stack.pop()
        found.extend(_candidate_roots(current))
        if depth >= max_depth:
            continue
        try:
            children = tuple(item for item in os.scandir(current) if item.is_dir(follow_symlinks=False))
        except OSError:
            continue
        stack.extend((Path(item.path), depth + 1) for item in children)
    return tuple(found)


def _has_lday(vipdoc: Path) -> bool:
    return any((vipdoc / exchange / "lday").is_dir() for exchange in _EXCHANGES)


def _inspect_root(root: Path, universe_symbols: Sequence[str]) -> TdxDirectoryCandidate:
    resolved = root.resolve(strict=False)
    vipdoc = resolved / "vipdoc" if (resolved / "vipdoc").is_dir() else resolved
    files = tuple(
        path
        for exchange in _EXCHANGES
        for path in (vipdoc / exchange / "lday").glob("*.day")
        if path.is_file()
    )
    readable = 0
    symbols: set[str] = set()
    latest: date | None = None
    latest_mtime: datetime | None = None
    for path in files:
        symbol = _a_share_symbol(path)
        try:
            size = path.stat().st_size
            valid = size >= _DAY_RECORD.size and _latest_date(path, size) is not None
            if valid:
                readable += 1
                if symbol:
                    symbols.add(symbol)
                candidate_date = _latest_date(path, size)
                if candidate_date and (latest is None or candidate_date > latest):
                    latest = candidate_date
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if latest_mtime is None or modified > latest_mtime:
                latest_mtime = modified
        except (OSError, ValueError, OverflowError):
            continue
    universe = {str(value).strip() for value in universe_symbols if str(value).strip()}
    denominator = len(universe) if universe else max(1, len(files))
    coverage = (len(symbols & universe) / denominator * 100.0) if universe else (len(symbols) / denominator * 100.0)
    state: Literal["ready", "partial", "unavailable"] = "ready" if readable else "unavailable"
    if readable and readable < len(files):
        state = "partial"
    return TdxDirectoryCandidate(
        root=resolved,
        vipdoc_path=vipdoc,
        display_name=resolved.name or str(resolved),
        version_hint=_version_hint(resolved),
        latest_trade_date=latest,
        day_file_count=len(files),
        readable_day_file_count=readable,
        a_share_coverage_percent=round(min(100.0, coverage), 2),
        last_data_update=latest_mtime,
        score=0,
        state=state,
    )


def _latest_date(path: Path, size: int) -> date | None:
    with path.open("rb") as handle:
        handle.seek(max(0, size - _DAY_RECORD.size))
        raw = handle.read(_DAY_RECORD.size)
    if len(raw) != _DAY_RECORD.size:
        return None
    value = _DAY_RECORD.unpack(raw)[0]
    try:
        parsed = date(value // 10000, value // 100 % 100, value % 100)
    except ValueError:
        return None
    return parsed if 1990 <= parsed.year <= 2100 else None


def _version_hint(root: Path) -> str | None:
    name = root.name.casefold()
    if "mock" in name:
        return "金融终端（量化模拟）"
    if "64" in name:
        return "64 位通达信"
    if "mpv" in name:
        return "MPV 版"
    if "专业" in root.name or "pro" in name:
        return "专业研究版"
    if "港美" in root.name:
        return "港美通"
    return None
