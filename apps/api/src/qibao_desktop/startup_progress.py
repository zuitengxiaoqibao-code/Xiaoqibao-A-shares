from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StartupProgress:
    stage: str
    percent: int
    step: str
    detail: str
    elapsed_ms: int | None = None


_STAGE_PROGRESS: dict[str, tuple[int, str, str]] = {
    "api-app-imported": (25, "API 模块已加载", "正在初始化本地数据服务"),
    "local-sources-ready": (28, "本地数据源已检查", "正在完成本地数据服务初始化"),
    "repositories-ready": (31, "本地数据库已就绪", "正在挂载研究与行情仓库"),
    "bond-universe-ready": (33, "可转债数据服务已就绪", "正在准备 A 股市场服务"),
    "services-and-instrument-directory-ready": (
        35,
        "股票目录与服务已就绪",
        "正在准备市场情绪与量化模块",
    ),
    "a-share-universe-ready": (36, "A 股股票目录已就绪", "正在连接本地行情快照"),
    "market-sentiment-ready": (38, "市场情绪服务已就绪", "正在准备首页与量化服务"),
    "history-symbol-reconciliation-scheduled": (
        39,
        "历史数据校准已排队",
        "后台校准不会阻塞首页展示",
    ),
    "a-share-universe-refresh-scheduled": (
        40,
        "A 股目录刷新已排队",
        "正在等待本地 API 完成最后检查",
    ),
    "lifespan-ready": (41, "本地 API 服务已完成初始化", "正在打开首页资源"),
}
_STAGE_PATTERN = re.compile(r"\bstage=(?P<stage>[a-z0-9-]+)\b")
_ELAPSED_PATTERN = re.compile(r"\belapsed_ms=(?P<elapsed>[0-9]+)\b")
_LOG_TAIL_BYTES = 64 * 1024


def read_startup_progress(log_path: Path) -> StartupProgress | None:
    """Return the latest startup milestone that the API actually logged."""
    try:
        with log_path.open("rb") as handle:
            handle.seek(0, 2)
            handle.seek(max(0, handle.tell() - _LOG_TAIL_BYTES))
            text = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    latest: StartupProgress | None = None
    for line in text.splitlines():
        match = _STAGE_PATTERN.search(line)
        if match is None:
            continue
        stage = match.group("stage")
        values = _STAGE_PROGRESS.get(stage)
        if values is None:
            continue
        percent, step, detail = values
        elapsed_match = _ELAPSED_PATTERN.search(line)
        elapsed_ms = int(elapsed_match.group("elapsed")) if elapsed_match else None
        latest = StartupProgress(stage, percent, step, detail, elapsed_ms)
    return latest
