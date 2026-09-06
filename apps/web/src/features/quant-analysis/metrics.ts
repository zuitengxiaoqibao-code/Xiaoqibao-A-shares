import type { BacktestResult } from "../backtest/types";
import type { FirstLimitUpCandidate } from "../first-limit-up/types";
import type { QuantStrategyCandidate, SignalMetric } from "./types";

function numeric(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

function clamp(value: number): number {
  return Math.max(0, Math.min(100, value));
}

function percent(value: number | null, digits = 1): string {
  return value === null ? "--" : `${value.toFixed(digits)}%`;
}

export function signalMetrics(
  candidate: FirstLimitUpCandidate | null,
  backtest: BacktestResult | null,
  strategyCandidate: QuantStrategyCandidate | null = null,
): SignalMetric[] {
  const score = numeric(candidate?.score ?? strategyCandidate?.strategy_score);
  const hasTrades = (backtest?.metrics.closed_trade_count ?? 0) > 0;
  const volatility = backtest ? numeric(backtest.metrics.annualized_volatility) : null;
  const winRate = hasTrades && backtest ? numeric(backtest.metrics.win_rate) : null;
  const odds = hasTrades && backtest ? numeric(backtest.metrics.profit_loss_ratio) : null;
  const drawdown = backtest ? numeric(backtest.max_drawdown) : null;
  const ev = winRate !== null && odds !== null
    ? winRate * odds - (1 - winRate)
    : null;

  return [
    {
      key: "vol", label: "VOL",
      value: percent(volatility === null ? null : volatility * 100),
      detail: backtest ? "回测年化波动率" : "等待历史回测",
      barValue: volatility === null ? 0 : clamp(volatility * 100),
      tone: volatility === null ? "muted" : volatility > 0.35 ? "danger" : volatility > 0.2 ? "warning" : "positive",
    },
    {
      key: "score", label: "SCORE",
      value: score === null ? "--" : score.toFixed(1),
      detail: candidate
        ? "首次涨停规则分"
        : strategyCandidate
          ? "量化策略综合分"
          : "等待候选规则分",
      barValue: score === null ? 0 : clamp(score),
      tone: score === null ? "muted" : score >= 70 ? "positive" : score >= 50 ? "warning" : "danger",
    },
    {
      key: "win_rate", label: "胜率",
      value: percent(winRate === null ? null : winRate * 100),
      detail: hasTrades ? `${backtest?.metrics.closed_trade_count} 笔已平仓样本` : "没有足够的已平仓样本",
      barValue: winRate === null ? 0 : clamp(winRate * 100),
      tone: winRate === null ? "muted" : winRate >= 0.55 ? "positive" : winRate >= 0.45 ? "warning" : "danger",
    },
    {
      key: "odds", label: "赔率",
      value: odds === null ? "--" : `${odds.toFixed(2)}x`,
      detail: "历史平均盈利 / 平均亏损",
      barValue: odds === null ? 0 : clamp(odds / 3 * 100),
      tone: odds === null ? "muted" : odds >= 1.5 ? "positive" : odds >= 1 ? "warning" : "danger",
    },
    {
      key: "risk", label: "风险",
      value: percent(drawdown === null ? null : drawdown * 100),
      detail: "历史最大回撤",
      barValue: drawdown === null ? 0 : clamp(drawdown * 100),
      tone: drawdown === null ? "muted" : drawdown > 0.2 ? "danger" : drawdown > 0.1 ? "warning" : "positive",
    },
    {
      key: "position", label: "仓位", value: "--",
      detail: "观察系统未连接券商账户",
      barValue: 0, tone: "muted",
    },
    {
      key: "ev", label: "EV",
      value: ev === null ? "--" : `${ev >= 0 ? "+" : ""}${ev.toFixed(2)}R`,
      detail: "胜率 × 赔率 − 失败概率",
      barValue: ev === null ? 0 : clamp((ev + 1) * 50),
      tone: ev === null ? "muted" : ev > 0 ? "positive" : ev > -0.2 ? "warning" : "danger",
    },
  ];
}

function distanceScore(value: string | null): number | null {
  const result = numeric(value);
  return result === null ? null : clamp(100 - result * 100);
}

function valuationScore(value: string | null): number | null {
  const result = numeric(value);
  if (result === null) return null;
  if (result <= 0 || result > 50) return 0;
  return clamp(100 - result);
}

function structureScore(candidate: FirstLimitUpCandidate): number {
  return {
    limit_up_day: 15,
    waiting_pullback: 45,
    pullback_window: 90,
    risk_expanded: 5,
    data_insufficient: 0,
  }[candidate.stage];
}

export function factorRadar(candidate: FirstLimitUpCandidate) {
  const score = candidate.selection_status === "data_insufficient" ? null : numeric(candidate.score);
  const structure = candidate.selection_status === "data_insufficient" ? null : structureScore(candidate);
  const consolidation = candidate.selection_status === "data_insufficient" ? null : clamp(candidate.consolidation_days / 10 * 100);
  return {
    indicators: ["估值", "周线底部", "月线底部", "回撤结构", "盘整", "规则总分"],
    values: [
      valuationScore(candidate.pe_ttm),
      distanceScore(candidate.weekly_distance_to_low),
      distanceScore(candidate.monthly_distance_to_low),
      structure,
      consolidation,
      score,
    ],
    verifiedCount: [
      candidate.pe_ttm,
      candidate.weekly_distance_to_low,
      candidate.monthly_distance_to_low,
      structure,
      consolidation,
      score,
    ].filter((value) => value !== null && Number.isFinite(value)).length,
  };
}

export function backtestFactorRadar(
  backtest: BacktestResult,
  strategyCandidate: QuantStrategyCandidate | null = null,
) {
  const winRate = numeric(backtest.metrics.win_rate);
  const odds = numeric(backtest.metrics.profit_loss_ratio);
  const volatility = numeric(backtest.metrics.annualized_volatility);
  const drawdown = numeric(backtest.max_drawdown);
  const sharpe = numeric(backtest.metrics.sharpe_ratio);
  const score = numeric(strategyCandidate?.strategy_score);
  const values = [
    winRate === null ? null : clamp(winRate * 100),
    odds === null ? null : clamp(odds / 3 * 100),
    volatility === null ? null : clamp(100 - volatility * 100),
    drawdown === null ? null : clamp(100 - drawdown * 100),
    sharpe === null ? null : clamp((sharpe + 1) / 3 * 100),
    score,
  ];
  return {
    indicators: ["历史胜率", "历史赔率", "波动控制", "回撤控制", "风险调整", "策略综合分"],
    values,
    verifiedCount: values.filter((value) => value !== null && Number.isFinite(value)).length,
  };
}

export function equityPoints(backtest: BacktestResult | null): Array<{
  date: string;
  equity: number;
  drawdown: number;
}> {
  if (!backtest || !Array.isArray(backtest.equity_curve)) return [];
  let peak = 0;
  return backtest.equity_curve.flatMap((value) => {
    if (!value || typeof value !== "object") return [];
    const row = value as Record<string, unknown>;
    const date = typeof row.trade_date === "string" ? row.trade_date : null;
    const equity = numeric(row.equity as string | number | null | undefined);
    if (!date || equity === null) return [];
    peak = Math.max(peak, equity);
    return [{ date, equity, drawdown: peak ? (equity / peak - 1) * 100 : 0 }];
  });
}
