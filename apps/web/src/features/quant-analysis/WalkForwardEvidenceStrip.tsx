import { Activity, AlertTriangle, ShieldCheck } from "lucide-react";

import type { WalkForwardReport } from "./types";


type Props = {
  report: WalkForwardReport | null;
  loading: boolean;
  error: string;
};

const limitationLabels: Record<string, string> = {
  insufficient_bars_for_walk_forward: "日线不足，无法形成完整滚动窗口",
  closed_trade_sample_below_minimum: "样本外闭合交易未达到结论门槛",
  out_of_sample_sharpe_unavailable: "测试段波动样本不足，Sharpe 不可用",
  mixed_bar_sources: "测试日线包含多个真实来源，结论已降级",
  survivorship_bias_unresolved: "幸存者偏差尚未消除",
  corporate_actions_not_adjusted: "复权与公司行为边界仍需核验",
  benchmark_not_available: "当前没有可比基准收益",
};

function numberText(value: string | null | undefined, digits = 2): string {
  if (value === null || value === undefined || value === "") return "--";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "--";
}

function percentText(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "--";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${(parsed * 100).toFixed(1)}%` : "--";
}

export function WalkForwardEvidenceStrip({ report, loading, error }: Props) {
  const statusLabel = report?.status === "ready"
    ? "样本外可评估"
    : report?.status === "partial"
      ? "样本不足"
      : report?.status === "unavailable"
        ? "验证不可用"
        : loading
          ? "正在滚动验证"
          : "等待验证";
  const reason = error || report?.limitations
    .map((item) => limitationLabels[item])
    .find(Boolean) || "训练、验证和测试按时间隔离，测试段禁止调参。";

  return <section className="walk-forward-strip" role="region" aria-label="样本外滚动验证" aria-busy={loading}>
    <header>
      <div><span>OUT-OF-SAMPLE / WALK FORWARD</span><h2>样本外滚动验证</h2></div>
      <div className={`walk-forward-state ${loading ? "loading" : report?.status ?? "idle"}`}>
        {report?.status === "ready" ? <ShieldCheck size={15} /> : report?.status ? <AlertTriangle size={15} /> : <Activity size={15} />}
        <i />{statusLabel}
      </div>
    </header>
    <div className="walk-forward-metrics">
      <span><small>测试窗口</small><b>{report ? `${report.window_count} 个` : "--"}</b></span>
      <span><small>闭合交易门槛</small><b>{report ? `${report.closed_trade_count} / ${report.minimum_closed_trades} 笔` : "--"}</b></span>
      <span><small>样本外胜率</small><b>{percentText(report?.win_rate)}</b></span>
      <span><small>样本外 Sharpe</small><b>{numberText(report?.sharpe_ratio)}</b></span>
      <span><small>最大回撤</small><b className="loss">{percentText(report?.max_drawdown)}</b></span>
      <span><small>验证分</small><b>{numberText(report?.strategy_score)}</b></span>
    </div>
    <footer><span>{reason}</span><small>{report ? `${report.source} · 参数 ${report.parameter_snapshot_hash.slice(0, 8)}` : "使用本地日线计算"}</small></footer>
  </section>;
}
