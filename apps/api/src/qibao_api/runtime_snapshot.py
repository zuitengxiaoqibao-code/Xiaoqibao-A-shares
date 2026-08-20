from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from qibao_api.contracts.runtime_snapshot import RuntimeSnapshot


PayloadT = TypeVar("PayloadT")


@dataclass(frozen=True)
class SnapshotDecision(Generic[PayloadT]):
    snapshot: RuntimeSnapshot[PayloadT]
    reason: str | None = None


def choose_runtime_snapshot(
    current: RuntimeSnapshot[PayloadT] | None,
    incoming: RuntimeSnapshot[PayloadT],
    *,
    is_empty: Callable[[PayloadT], bool] | None = None,
) -> SnapshotDecision[PayloadT]:
    """Accept only an equally trustworthy or better snapshot.

    Refresh errors are returned as a reason while the caller keeps rendering the
    last usable payload. This prevents a late, empty, or degraded response from
    clearing the page.
    """

    if current is None or current.data is None:
        return SnapshotDecision(incoming)
    if incoming.status in {"error", "unavailable"} or incoming.data is None:
        reason = incoming.error.message if incoming.error is not None else "最新数据暂不可用"
        return SnapshotDecision(current, reason)
    if current.trade_date and incoming.trade_date and incoming.trade_date < current.trade_date:
        return SnapshotDecision(current, "新响应属于更早交易日，继续展示当前数据")
    if (
        current.observed_at is not None
        and incoming.observed_at is not None
        and incoming.observed_at < current.observed_at
    ):
        return SnapshotDecision(current, "新响应时间早于当前数据，继续展示当前数据")
    if is_empty is not None and is_empty(incoming.data) and not is_empty(current.data):
        return SnapshotDecision(current, "新数据为空，继续展示上一次完整数据")
    if (
        current.coverage is not None
        and incoming.coverage is not None
        and incoming.coverage < current.coverage
    ):
        return SnapshotDecision(current, "新数据覆盖率较低，继续展示上一次完整数据")
    return SnapshotDecision(incoming)
