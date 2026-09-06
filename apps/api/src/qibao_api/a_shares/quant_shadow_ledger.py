"""Immutable shadow decisions and truthful post-decision outcome evaluation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Callable, Sequence

from qibao_api.a_shares.data_quality import assess_bar_series
from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.quant_shadow import (
    CalibrationBucket,
    QuantShadowAnalytics,
    RegimePerformance,
    ShadowDecisionRecord,
    ShadowOutcome,
    StrategyDriftAssessment,
)
from qibao_api.contracts.quant_strategy import QuantStrategyDashboard


HORIZONS = (1, 3, 5, 10, 20, 60)
FORMULA_VERSION = "a-share-short-strategy-v2.0"
CALIBRATION_BUCKETS = (
    ("0-69", 0, 69),
    ("70-79", 70, 79),
    ("80-89", 80, 89),
    ("90-100", 90, 100),
)
MIN_ANALYTICS_SAMPLE = 20
MIN_BUCKET_SAMPLE = 5
DRIFT_WINDOW = 10
MARKET_REGIMES = ("情绪主升", "指数权重进攻", "轮动震荡", "冰点修复", "高位退潮", "缩量混沌")


class QuantShadowLedgerStore:
    def __init__(
        self,
        database_path: Path,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        bar_repository=None,
    ) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.bar_repository = bar_repository
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS quant_shadow_decisions (
                    decision_id TEXT PRIMARY KEY,
                    as_of TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    formula_version TEXT NOT NULL,
                    candidate_status TEXT NOT NULL,
                    market_regime TEXT,
                    strategy_score TEXT NOT NULL,
                    reference_price TEXT,
                    candidate_json TEXT NOT NULL,
                    frozen_at TEXT NOT NULL,
                    UNIQUE(as_of, symbol, formula_version)
                );
                CREATE TABLE IF NOT EXISTS quant_shadow_outcomes (
                    decision_id TEXT NOT NULL,
                    horizon INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    evaluated_trade_date TEXT,
                    return_percent TEXT,
                    mfe_percent TEXT,
                    mae_percent TEXT,
                    invalidation_state TEXT NOT NULL,
                    evaluated_at TEXT,
                    limitation TEXT,
                    PRIMARY KEY(decision_id, horizon),
                    FOREIGN KEY(decision_id) REFERENCES quant_shadow_decisions(decision_id)
                );
                CREATE TABLE IF NOT EXISTS quant_candidate_lifecycle_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    snapshot_id TEXT,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY(decision_id) REFERENCES quant_shadow_decisions(decision_id)
                );
                CREATE TRIGGER IF NOT EXISTS reject_update_quant_candidate_lifecycle
                BEFORE UPDATE ON quant_candidate_lifecycle_events
                BEGIN SELECT RAISE(ABORT, 'append-only candidate lifecycle'); END;
                CREATE TRIGGER IF NOT EXISTS reject_delete_quant_candidate_lifecycle
                BEFORE DELETE ON quant_candidate_lifecycle_events
                BEGIN SELECT RAISE(ABORT, 'append-only candidate lifecycle'); END;
                CREATE INDEX IF NOT EXISTS ix_quant_shadow_decisions_as_of
                ON quant_shadow_decisions(as_of, symbol);
                """
            )
            columns = {
                row[1] for row in connection.execute(
                    "PRAGMA table_info(quant_shadow_decisions)"
                ).fetchall()
            }
            if "market_regime" not in columns:
                connection.execute(
                    "ALTER TABLE quant_shadow_decisions ADD COLUMN market_regime TEXT"
                )
            if "decision_source" not in columns:
                connection.execute(
                    "ALTER TABLE quant_shadow_decisions ADD COLUMN decision_source "
                    "TEXT NOT NULL DEFAULT 'quant_strategy'"
                )
            if "opportunity_type" not in columns:
                connection.execute(
                    "ALTER TABLE quant_shadow_decisions ADD COLUMN opportunity_type TEXT"
                )
            connection.execute(
                """INSERT OR IGNORE INTO quant_shadow_outcomes
                (decision_id, horizon, status, invalidation_state)
                SELECT decision_id, 60, 'pending', 'unavailable'
                FROM quant_shadow_decisions"""
            )

    def freeze(
        self,
        dashboard: QuantStrategyDashboard,
        *,
        decision_source: str = "quant_strategy",
        opportunity_type: str | None = None,
    ) -> int:
        """Append candidates once; never update an existing decision row."""
        if dashboard.status == "unavailable":
            return 0
        if decision_source not in {
            "quant_strategy", "opportunity_scan", "ai_hypothesis", "manual_watch",
        }:
            raise ValueError("unsupported shadow decision source")
        frozen_at = dashboard.generated_at.astimezone(timezone.utc).isoformat()
        inserted = 0
        with self._connect() as connection:
            for candidate in dashboard.candidates:
                decision_id = _decision_id(
                    dashboard.as_of, candidate.symbol, dashboard.formula_version,
                )
                payload = json.dumps(
                    candidate.model_dump(mode="json"),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO quant_shadow_decisions
                    (decision_id, as_of, symbol, formula_version, candidate_status,
                     strategy_score, reference_price, candidate_json, frozen_at, market_regime,
                     decision_source, opportunity_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision_id,
                        dashboard.as_of.isoformat(),
                        candidate.symbol,
                        dashboard.formula_version,
                        candidate.status,
                        str(candidate.strategy_score),
                        str(candidate.reference_price) if candidate.reference_price is not None else None,
                        payload,
                        frozen_at,
                        dashboard.regime.regime,
                        decision_source,
                        opportunity_type,
                    ),
                )
                if cursor.rowcount:
                    inserted += 1
                    snapshot_id = dashboard.input_snapshot_ids[0] if dashboard.input_snapshot_ids else None
                    connection.execute(
                        """INSERT INTO quant_candidate_lifecycle_events(
                           decision_id, state, reason, snapshot_id, occurred_at
                        ) VALUES (?, 'observed', ?, ?, ?)""",
                        (decision_id, "候选进入观察池", snapshot_id, frozen_at),
                    )
                    connection.executemany(
                        """INSERT OR IGNORE INTO quant_shadow_outcomes
                        (decision_id, horizon, status, invalidation_state)
                        VALUES (?, ?, 'pending', 'unavailable')""",
                        [(decision_id, horizon) for horizon in HORIZONS],
                    )
        return inserted

    def lifecycle(self, decision_id: str) -> tuple[str, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT state FROM quant_candidate_lifecycle_events
                   WHERE decision_id = ? ORDER BY sequence""",
                (decision_id,),
            ).fetchall()
        return tuple(row["state"] for row in rows)

    def transition(
        self, decision_id: str, state: str, *, reason: str, snapshot_id: str | None,
    ) -> None:
        if state not in {"triggered", "invalidated", "reviewed"}:
            raise ValueError("unsupported candidate lifecycle state")
        if not reason.strip():
            raise ValueError("candidate lifecycle transition requires a reason")
        current = self.lifecycle(decision_id)
        if not current:
            raise KeyError(decision_id)
        allowed = {
            "observed": {"triggered", "invalidated", "reviewed"},
            "triggered": {"invalidated", "reviewed"},
            "invalidated": {"reviewed"},
            "reviewed": set(),
        }
        if state not in allowed[current[-1]]:
            raise ValueError("invalid candidate lifecycle transition")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO quant_candidate_lifecycle_events(
                   decision_id, state, reason, snapshot_id, occurred_at
                ) VALUES (?, ?, ?, ?, ?)""",
                (decision_id, state, reason.strip(), snapshot_id, self.clock().isoformat()),
            )

    def get(self, decision_id: str) -> ShadowDecisionRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM quant_shadow_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
            if row is None:
                raise KeyError(decision_id)
            outcomes = connection.execute(
                "SELECT * FROM quant_shadow_outcomes WHERE decision_id = ? ORDER BY horizon",
                (decision_id,),
            ).fetchall()
            lifecycle = connection.execute(
                "SELECT state, snapshot_id FROM quant_candidate_lifecycle_events WHERE decision_id = ? ORDER BY sequence",
                (decision_id,),
            ).fetchall()
        return ShadowDecisionRecord(
            decision_id=row["decision_id"],
            as_of=date.fromisoformat(row["as_of"]),
            symbol=row["symbol"],
            formula_version=row["formula_version"],
            candidate_status=row["candidate_status"],
            market_regime=row["market_regime"],
            decision_source=row["decision_source"],
            opportunity_type=row["opportunity_type"],
            strategy_score=Decimal(row["strategy_score"]),
            reference_price=Decimal(row["reference_price"]) if row["reference_price"] else None,
            frozen_at=datetime.fromisoformat(row["frozen_at"]),
            outcomes=tuple(_outcome(item) for item in outcomes),
            lifecycle=tuple(item["state"] for item in lifecycle),
            input_snapshot_ids=tuple(dict.fromkeys(item["snapshot_id"] for item in lifecycle if item["snapshot_id"])),
        )

    def recent(self, *, limit: int = 50) -> tuple[ShadowDecisionRecord, ...]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        with self._connect() as connection:
            ids = connection.execute(
                """SELECT decision_id FROM quant_shadow_decisions
                   ORDER BY as_of DESC, symbol LIMIT ?""",
                (limit,),
            ).fetchall()
        return tuple(self.get(row["decision_id"]) for row in ids)

    def evaluate(
        self,
        decision_id: str,
        bars: Sequence[DailyBar],
    ) -> tuple[ShadowOutcome, ...]:
        decision = self.get(decision_id)
        future_bars = tuple(bar for bar in bars if bar.trade_date > decision.as_of)
        quality = assess_bar_series(future_bars)
        ordered = tuple(sorted(
            future_bars,
            key=lambda bar: bar.trade_date,
        ))
        quality_limitation = _quality_limitation(quality.issues)
        now = self.clock()
        outcomes: list[ShadowOutcome] = []
        with self._connect() as connection:
            for horizon in HORIZONS:
                window = ordered[:horizon]
                if quality.blocked:
                    outcome = ShadowOutcome(
                        decision_id=decision_id,
                        horizon=horizon,
                        status="unavailable",
                        evaluated_at=now,
                        limitation=quality_limitation,
                    )
                elif decision.reference_price is None:
                    outcome = ShadowOutcome(
                        decision_id=decision_id,
                        horizon=horizon,
                        status="unavailable",
                        evaluated_at=now,
                        limitation=_merge_limitation("冻结候选没有真实参考价", quality_limitation),
                    )
                elif len(window) < horizon:
                    outcome = ShadowOutcome(
                        decision_id=decision_id,
                        horizon=horizon,
                        status="pending",
                        limitation=_merge_limitation(
                            f"未来真实日线不足 {horizon} 个交易日",
                            quality_limitation,
                        ),
                    )
                else:
                    ref = decision.reference_price
                    outcome = ShadowOutcome(
                        decision_id=decision_id,
                        horizon=horizon,
                        status="ready",
                        evaluated_trade_date=window[-1].trade_date,
                        return_percent=_percent(window[-1].close / ref - 1),
                        mfe_percent=_percent(max(item.high for item in window) / ref - 1),
                        mae_percent=_percent(min(item.low for item in window) / ref - 1),
                        invalidation_state="unavailable",
                        evaluated_at=now,
                        limitation=_merge_limitation(
                            "冻结规则未提供可量化失效价格",
                            quality_limitation,
                        ),
                    )
                connection.execute(
                    """UPDATE quant_shadow_outcomes SET status=?, evaluated_trade_date=?,
                    return_percent=?, mfe_percent=?, mae_percent=?, invalidation_state=?,
                    evaluated_at=?, limitation=? WHERE decision_id=? AND horizon=?""",
                    (
                        outcome.status,
                        outcome.evaluated_trade_date.isoformat() if outcome.evaluated_trade_date else None,
                        str(outcome.return_percent) if outcome.return_percent is not None else None,
                        str(outcome.mfe_percent) if outcome.mfe_percent is not None else None,
                        str(outcome.mae_percent) if outcome.mae_percent is not None else None,
                        outcome.invalidation_state,
                        outcome.evaluated_at.isoformat() if outcome.evaluated_at else None,
                        outcome.limitation,
                        decision_id,
                        horizon,
                    ),
                )
                outcomes.append(outcome)
        return tuple(outcomes)

    def analytics(
        self,
        *,
        horizon: int = 5,
        decision_source: str | None = None,
        opportunity_type: str | None = None,
    ) -> QuantShadowAnalytics:
        if horizon not in HORIZONS:
            raise ValueError(f"horizon must be one of {HORIZONS}")
        self._refresh_pending_outcomes(horizon)
        if decision_source is not None and decision_source not in {
            "quant_strategy", "opportunity_scan", "ai_hypothesis", "manual_watch",
        }:
            raise ValueError("unsupported shadow decision source")
        conditions = [
            "o.horizon = ?", "o.status = 'ready'", "o.return_percent IS NOT NULL",
        ]
        parameters: list[object] = [horizon]
        if decision_source is not None:
            conditions.append("d.decision_source = ?")
            parameters.append(decision_source)
        if opportunity_type is not None:
            conditions.append("d.opportunity_type = ?")
            parameters.append(opportunity_type)
        where_clause = " AND ".join(conditions)
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT d.as_of, d.symbol, d.strategy_score, d.market_regime,
                          o.return_percent, o.mfe_percent, o.mae_percent
                   FROM quant_shadow_decisions AS d
                   JOIN quant_shadow_outcomes AS o ON o.decision_id = d.decision_id
                   WHERE {where_clause}
                   ORDER BY d.as_of ASC, d.symbol ASC""",
                tuple(parameters),
            ).fetchall()
            pending_conditions = ["o.horizon = ?", "o.status = 'pending'"]
            pending_parameters: list[object] = [horizon]
            if decision_source is not None:
                pending_conditions.append("d.decision_source = ?")
                pending_parameters.append(decision_source)
            if opportunity_type is not None:
                pending_conditions.append("d.opportunity_type = ?")
                pending_parameters.append(opportunity_type)
            pending_sample_count = int(connection.execute(
                f"""SELECT COUNT(*) FROM quant_shadow_outcomes AS o
                   JOIN quant_shadow_decisions AS d ON d.decision_id = o.decision_id
                   WHERE {' AND '.join(pending_conditions)}""",
                tuple(pending_parameters),
            ).fetchone()[0])

        samples = tuple(_analytics_sample(row) for row in rows)
        mature_sample_count = len(samples)
        limitations: list[str] = []
        buckets = tuple(
            _calibration_bucket(label, score_min, score_max, samples)
            for label, score_min, score_max in CALIBRATION_BUCKETS
        )
        if mature_sample_count < MIN_ANALYTICS_SAMPLE:
            status = "insufficient"
            limitations.append(
                f"成熟样本少于 {MIN_ANALYTICS_SAMPLE} 条，当前仅 {mature_sample_count} 条，不作可靠性结论"
            )
        elif any(bucket.status == "insufficient" for bucket in buckets):
            status = "partial"
            limitations.append(
                f"部分评分区间少于 {MIN_BUCKET_SAMPLE} 条成熟样本，分桶校准结论不完整"
            )
        else:
            status = "ready"
        unknown_regime_count = sum(
            sample["market_regime"] not in MARKET_REGIMES for sample in samples
        )
        if unknown_regime_count:
            limitations.append(
                f"{unknown_regime_count} 条历史记录未冻结六类市场风格，不纳入分风格统计"
            )

        return QuantShadowAnalytics(
            status=status,
            horizon=horizon,
            decision_source=decision_source,
            opportunity_type=opportunity_type,
            mature_sample_count=mature_sample_count,
            pending_sample_count=pending_sample_count,
            hit_rate_percent=_hit_rate(samples),
            average_return_percent=_average(samples, "return_percent", places="0.01"),
            average_mfe_percent=_average(samples, "mfe_percent", places="0.01"),
            average_mae_percent=_average(samples, "mae_percent", places="0.01"),
            brier_score=_brier_score(samples),
            buckets=buckets,
            regime_performance=tuple(
                _regime_performance(regime, samples) for regime in MARKET_REGIMES
            ),
            drift=_drift_assessment(samples),
            generated_at=self.clock(),
            limitations=tuple(limitations),
        )

    def _refresh_pending_outcomes(self, horizon: int) -> None:
        if self.bar_repository is None:
            return
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT d.decision_id, d.symbol
                   FROM quant_shadow_decisions AS d
                   JOIN quant_shadow_outcomes AS o ON o.decision_id = d.decision_id
                   WHERE o.horizon = ? AND o.status = 'pending'
                   ORDER BY d.as_of, d.symbol""",
                (horizon,),
            ).fetchall()
        for row in rows:
            bars = self.bar_repository.latest(row["symbol"], 2000)
            self.evaluate(row["decision_id"], bars)


def _decision_id(as_of: date, symbol: str, formula_version: str) -> str:
    raw = f"{as_of.isoformat()}|{symbol}|{formula_version}".encode()
    return f"shadow-{hashlib.sha256(raw).hexdigest()[:24]}"


def _percent(value: Decimal) -> Decimal:
    return (value * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quality_limitation(issues) -> str | None:
    details = tuple(dict.fromkeys(issue.detail for issue in issues))
    return "；".join(details) if details else None


def _merge_limitation(primary: str, secondary: str | None) -> str:
    return f"{primary}；{secondary}" if secondary else primary


def _outcome(row: sqlite3.Row) -> ShadowOutcome:
    return ShadowOutcome(
        decision_id=row["decision_id"],
        horizon=int(row["horizon"]),
        status=row["status"],
        evaluated_trade_date=(date.fromisoformat(row["evaluated_trade_date"])
                              if row["evaluated_trade_date"] else None),
        return_percent=Decimal(row["return_percent"]) if row["return_percent"] else None,
        mfe_percent=Decimal(row["mfe_percent"]) if row["mfe_percent"] else None,
        mae_percent=Decimal(row["mae_percent"]) if row["mae_percent"] else None,
        invalidation_state=row["invalidation_state"],
        evaluated_at=(datetime.fromisoformat(row["evaluated_at"])
                      if row["evaluated_at"] else None),
        limitation=row["limitation"],
    )


def _analytics_sample(row: sqlite3.Row) -> dict[str, Decimal | str]:
    return {
        "as_of": row["as_of"],
        "symbol": row["symbol"],
        "market_regime": row["market_regime"] or "unknown",
        "strategy_score": Decimal(row["strategy_score"]),
        "return_percent": Decimal(row["return_percent"]),
        "mfe_percent": Decimal(row["mfe_percent"]) if row["mfe_percent"] is not None else Decimal("0"),
        "mae_percent": Decimal(row["mae_percent"]) if row["mae_percent"] is not None else Decimal("0"),
    }


def _regime_performance(
    regime: str,
    samples: Sequence[dict[str, Decimal | str]],
) -> RegimePerformance:
    selected = tuple(sample for sample in samples if sample["market_regime"] == regime)
    returns = [sample["return_percent"] for sample in selected]
    wins = [value for value in returns if value > 0]
    losses = [-value for value in returns if value < 0]
    profit_loss_ratio = None
    if wins and losses:
        profit_loss_ratio = (
            (sum(wins, Decimal("0")) / Decimal(len(wins)))
            / (sum(losses, Decimal("0")) / Decimal(len(losses)))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    streak = 0
    max_streak = 0
    equity = Decimal("1")
    peak = Decimal("1")
    max_drawdown = Decimal("0")
    for value in returns:
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
        equity *= Decimal("1") + value / Decimal("100")
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak * Decimal("100"))
    sharpe = None
    if len(returns) >= 2:
        mean = sum(returns, Decimal("0")) / Decimal(len(returns))
        variance = sum(((value - mean) ** 2 for value in returns), Decimal("0")) / Decimal(len(returns) - 1)
        standard_deviation = variance.sqrt()
        if standard_deviation > 0:
            sharpe = (mean / standard_deviation).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    average_return = _average(selected, "return_percent", places="0.01")
    return RegimePerformance(
        regime=regime,
        sample_count=len(selected),
        hit_rate_percent=_hit_rate(selected),
        average_return_percent=average_return,
        expected_value_percent=average_return,
        profit_loss_ratio=profit_loss_ratio,
        max_consecutive_losses=max_streak,
        max_drawdown_percent=(
            max_drawdown.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if selected else None
        ),
        sharpe_ratio=sharpe,
    )


def _calibration_bucket(
    label: str,
    score_min: int,
    score_max: int,
    samples: Sequence[dict[str, Decimal | str]],
) -> CalibrationBucket:
    selected = tuple(
        sample for sample in samples
        if Decimal(score_min) <= sample["strategy_score"] <= Decimal(score_max)
    )
    sample_count = len(selected)
    average_score = _average(selected, "strategy_score", places="0.01")
    hit_rate = _hit_rate(selected) if sample_count >= MIN_BUCKET_SAMPLE else None
    calibration_gap = None
    if average_score is not None and hit_rate is not None:
        calibration_gap = (average_score - hit_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
    return CalibrationBucket(
        label=label,
        score_min=score_min,
        score_max=score_max,
        sample_count=sample_count,
        average_score=average_score,
        hit_rate_percent=hit_rate,
        average_return_percent=(
            _average(selected, "return_percent", places="0.01")
            if sample_count >= MIN_BUCKET_SAMPLE else None
        ),
        average_mfe_percent=(
            _average(selected, "mfe_percent", places="0.01")
            if sample_count >= MIN_BUCKET_SAMPLE else None
        ),
        average_mae_percent=(
            _average(selected, "mae_percent", places="0.01")
            if sample_count >= MIN_BUCKET_SAMPLE else None
        ),
        calibration_gap_percent=calibration_gap,
        status="ready" if sample_count >= MIN_BUCKET_SAMPLE else "insufficient",
    )


def _drift_assessment(
    samples: Sequence[dict[str, Decimal | str]],
) -> StrategyDriftAssessment:
    if len(samples) < DRIFT_WINDOW * 2:
        return StrategyDriftAssessment(
            status="insufficient",
            recent_sample_count=min(len(samples), DRIFT_WINDOW),
            baseline_sample_count=max(0, len(samples) - DRIFT_WINDOW),
            reasons=(f"近期与基线各至少需要 {DRIFT_WINDOW} 条成熟样本",),
        )

    recent = tuple(samples[-DRIFT_WINDOW:])
    baseline = tuple(samples[:-DRIFT_WINDOW])
    recent_hit_rate = _hit_rate(recent)
    baseline_hit_rate = _hit_rate(baseline)
    recent_return = _average(recent, "return_percent", places="0.01")
    baseline_return = _average(baseline, "return_percent", places="0.01")
    assert recent_hit_rate is not None and baseline_hit_rate is not None
    assert recent_return is not None and baseline_return is not None
    hit_rate_drop = baseline_hit_rate - recent_hit_rate
    reasons: list[str] = []
    if hit_rate_drop >= Decimal("20"):
        reasons.append("近期命中率较基线下降至少 20 个百分点")
    if baseline_return > 0 and recent_return < 0:
        reasons.append("近期平均收益由正转负")
    if reasons:
        drift_status = "drift"
    elif hit_rate_drop >= Decimal("10"):
        drift_status = "warning"
        reasons.append("近期命中率较基线下降 10 至 20 个百分点")
    else:
        drift_status = "stable"
        reasons.append("近期命中率和平均收益未触发漂移阈值")
    return StrategyDriftAssessment(
        status=drift_status,
        recent_sample_count=len(recent),
        baseline_sample_count=len(baseline),
        recent_hit_rate_percent=recent_hit_rate,
        baseline_hit_rate_percent=baseline_hit_rate,
        recent_average_return_percent=recent_return,
        baseline_average_return_percent=baseline_return,
        reasons=tuple(reasons),
    )


def _hit_rate(samples: Sequence[dict[str, Decimal | str]]) -> Decimal | None:
    if not samples:
        return None
    wins = sum(1 for sample in samples if sample["return_percent"] > 0)
    return (Decimal(wins) * Decimal("100") / Decimal(len(samples))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP,
    )


def _average(
    samples: Sequence[dict[str, Decimal | str]],
    key: str,
    *,
    places: str,
) -> Decimal | None:
    if not samples:
        return None
    total = sum((sample[key] for sample in samples), Decimal("0"))
    return (total / Decimal(len(samples))).quantize(
        Decimal(places), rounding=ROUND_HALF_UP,
    )


def _brier_score(samples: Sequence[dict[str, Decimal | str]]) -> Decimal | None:
    if not samples:
        return None
    total = Decimal("0")
    for sample in samples:
        probability = sample["strategy_score"] / Decimal("100")
        actual = Decimal("1") if sample["return_percent"] > 0 else Decimal("0")
        total += (probability - actual) ** 2
    return (total / Decimal(len(samples))).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP,
    )
