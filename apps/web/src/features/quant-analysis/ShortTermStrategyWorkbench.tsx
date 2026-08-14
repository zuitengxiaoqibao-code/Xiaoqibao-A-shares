import type { EChartsOption } from "echarts";
import {
  AlertTriangle, CheckCircle2, CircleGauge, Database, ShieldAlert, Target,
} from "lucide-react";

import { QuantChart } from "./QuantChart";
import { CandidateFunnel } from "./CandidateFunnel";
import { EvidenceLedger } from "../../shared/evidence/EvidenceLedger";
import { FieldEvidenceDetails } from "../../shared/evidence/FieldEvidenceDetails";
import { chartTheme } from "../../shared/visualization/chartTheme";
import type { QuantRegimeMetrics, QuantStrategyCandidate, QuantStrategyDashboard } from "./types";

type Props = {
  dashboard: QuantStrategyDashboard | null;
  loading: boolean;
  error: string;
};

const regimeColor: Record<string, string> = {
  情绪主升: chartTheme.eventColors.capital,
  指数权重进攻: chartTheme.warningColor,
  轮动震荡: chartTheme.liveColor,
  冰点修复: chartTheme.eventColors.company,
  高位退潮: chartTheme.riskMediumColor,
  缩量混沌: chartTheme.unavailableColor,
};

const regimeOrder = [
  "情绪主升", "指数权重进攻", "轮动震荡", "冰点修复", "高位退潮", "缩量混沌",
];

const metricDefinitions: Array<{
  key: keyof QuantRegimeMetrics;
  label: string;
  suffix: string;
  detail: string;
}> = [
  { key: "up_ratio", label: "上涨率", suffix: "%", detail: "上涨家数 / 全市场家数" },
  { key: "zt_ratio", label: "涨停率", suffix: "%", detail: "涨停家数 / 全市场家数" },
  { key: "dt_ratio", label: "跌停率", suffix: "%", detail: "跌停家数 / 全市场家数" },
  { key: "median_ret", label: "中位涨幅", suffix: "%", detail: "全市场涨跌幅中位数" },
  { key: "amt_heat", label: "成交热度", suffix: "x", detail: "成交额 / 20日平均成交额" },
  { key: "strong_close_ratio", label: "强收比例", suffix: "%", detail: "ClosePos 不低于75" },
  { key: "weak_close_ratio", label: "弱收比例", suffix: "%", detail: "ClosePos 不高于25" },
  { key: "limit_fail_ratio", label: "炸板弱收率", suffix: "%", detail: "触板后收盘低于涨停价97%" },
  { key: "panic_ratio", label: "恐慌率", suffix: "%", detail: "最低涨幅不高于-8%" },
  { key: "amp_ratio", label: "高波动率", suffix: "%", detail: "振幅不低于10%" },
  { key: "net_positive_ratio", label: "资金净流入率", suffix: "%", detail: "净流入为正的股票比例" },
];

const missingLabels: Record<string, string> = {
  net_positive_ratio: "全市场资金净流入覆盖不足",
  previous_risk_score: "缺少昨日风险分",
  realtime_quote: "缺少盘中实时行情",
  vwap_support: "待验证均价支撑",
  three_minute_return: "待验证3分钟涨幅",
  one_minute_return: "待验证1分钟涨幅",
  net_large_flow: "待验证大单净流入",
  net_fund_flow: "待验证资金净流入",
  volume_ratio: "待验证量比",
  order_ratio: "待验证委比",
  close_position_rising: "待验证收盘位置持续抬升",
  risk_reward_plan: "缺少明确止损和目标价",
  first_morning_divergence: "待验证早盘第一次分歧",
  limit_down_recovery: "待验证脱离跌停价",
  large_outflow_narrowing: "待验证大单净流出收窄",
  daily_low: "缺少日内最低价证据",
  open_gap: "缺少开盘涨幅证据",
  candidate_score: "候选分未达到阈值",
};

function number(value: string | null | undefined): number | null {
  if (value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function percent(value: string): string {
  const parsed = number(value);
  return parsed === null ? "--" : `${(parsed * 100).toFixed(1)}%`;
}

export function regimeGauge(dashboard: QuantStrategyDashboard): EChartsOption {
  const regime = dashboard.regime.regime ?? "待判定";
  const regimeIndex = Math.max(0, regimeOrder.indexOf(regime));
  const value = (regimeIndex + 0.5) / regimeOrder.length * 100;
  const emotion = number(dashboard.regime.emotion_score);
  const color = regimeColor[regime] ?? chartTheme.unavailableColor;
  const segments = regimeOrder.map((name, index) => [
    (index + 1) / regimeOrder.length,
    name === regime ? regimeColor[name] : `${regimeColor[name]}55`,
  ]) as Array<[number, string]>;
  return {
    animation: false,
    series: [{
      type: "gauge",
      min: 0,
      max: 100,
      startAngle: 210,
      endAngle: -30,
      splitNumber: 6,
      axisLine: { lineStyle: { width: 12, color: segments } },
      progress: { show: false },
      pointer: { length: "58%", width: 4, itemStyle: { color } },
      axisTick: { show: false },
      splitLine: { distance: -16, length: 7, lineStyle: { color: chartTheme.mutedTextColor, width: 1 } },
      axisLabel: {
        distance: 18,
        color: chartTheme.mutedTextColor,
        fontSize: 13,
        fontWeight: 700,
        backgroundColor: chartTheme.tooltipBackgroundColor,
        borderRadius: 2,
        padding: [2, 4],
        formatter: (axisValue: number) => axisValue === 0 || axisValue === 50 || axisValue === 100
          ? `${axisValue}`
          : "",
      },
      anchor: { show: true, size: 8, itemStyle: { color } },
      detail: {
        valueAnimation: false,
        offsetCenter: [0, "43%"],
        color,
        fontSize: 18,
        lineHeight: 28,
        formatter: `{regime|${regime}}\n{label|情绪 }{score|${emotion === null ? "--" : emotion.toFixed(1)}}`,
        rich: {
          regime: { color, fontSize: 18, fontWeight: 700, lineHeight: 28 },
          label: { color: chartTheme.mutedTextColor, fontSize: 13, fontWeight: 600, lineHeight: 28 },
          score: { color: chartTheme.textColor, fontSize: 22, fontWeight: 800, lineHeight: 28 },
        },
      },
      title: { show: false },
      data: [{ value }],
    }],
  };
}

function scoreTone(label: string, value: number | null): string {
  if (value === null) return "muted";
  if (label === "风险分") return value >= 65 ? "danger" : value >= 45 ? "warning" : "positive";
  return value >= 70 ? "positive" : value >= 45 ? "warning" : "danger";
}

function statusLabel(status: QuantStrategyCandidate["status"]): string {
  return {
    alert: "触发成立",
    watch: "触发成立",
    reject: "不具备条件",
    pending_trigger: "等待确认",
  }[status];
}

type FunnelStageKey = NonNullable<QuantStrategyDashboard["candidate_funnel"]>["stages"][number]["key"];

function stageCount(dashboard: QuantStrategyDashboard, key: FunnelStageKey): number | null {
  return dashboard.candidate_funnel?.stages.find((item) => item.key === key)?.count ?? null;
}

function QuantEvidenceSummary({ dashboard }: { dashboard: QuantStrategyDashboard }) {
  const universe = stageCount(dashboard, "universe");
  const factorReady = stageCount(dashboard, "factor_ready");
  const finalCandidates = stageCount(dashboard, "final_candidates");
  const excluded = universe !== null && finalCandidates !== null ? Math.max(0, universe - finalCandidates) : null;
  const coverage = number(dashboard.regime.coverage_percent);
  return <section className="strategy-evidence-summary" role="region" aria-label="量化证据摘要">
    <header><div><Database size={14} /><b>量化证据摘要</b></div><small>{dashboard.as_of} · 只统计真实返回样本</small></header>
    <div>
      <article><span>全市场样本</span><strong>{universe === null ? "--" : universe.toLocaleString("zh-CN")}</strong><small>扫描范围</small></article>
      <article><span>因子有效样本</span><strong>{factorReady === null ? "--" : factorReady.toLocaleString("zh-CN")}</strong><small>历史与字段可计算</small></article>
      <article><span>最终候选</span><strong>{finalCandidates === null ? "--" : finalCandidates.toLocaleString("zh-CN")}</strong><small>达到当前筛选口径</small></article>
      <article><span>筛选淘汰</span><strong>{excluded === null ? "--" : excluded.toLocaleString("zh-CN")}</strong><small>不代表亏损预测</small></article>
      <article><span>证据覆盖</span><strong>{coverage === null ? "--" : `${coverage.toFixed(0)}%`}</strong><small>{dashboard.status === "ready" ? "可用于当前结论" : "部分字段仍待补齐"}</small></article>
    </div>
  </section>;
}

function CandidateTag({ candidate }: { candidate: QuantStrategyCandidate }) {
  return <article className={`strategy-candidate-tag ${candidate.status}`} aria-label={`${candidate.symbol} ${candidate.name}`}>
    <header>
      <div><strong>{candidate.symbol}</strong><b>{candidate.name}</b></div>
      <span>{statusLabel(candidate.status)}</span>
    </header>
    <div className="strategy-candidate-primary">
      <span><small>策略总分</small><strong>{Number(candidate.strategy_score).toFixed(1)}</strong></span>
      <span><small>匹配模型</small><b>{candidate.model}</b></span>
      <span><small>证据覆盖</small><b>{Number(candidate.evidence_coverage_percent).toFixed(0)}%</b></span>
    </div>
    <div className="strategy-score-strip" aria-label="候选评分构成">
      <span>风格 <b>{percent(candidate.regime_match)}</b></span>
      <span>个股 <b>{percent(candidate.stock_score)}</b></span>
      <span>触发 <b>{percent(candidate.trigger_score)}</b></span>
      <span>盈亏比分 <b>{percent(candidate.rr_score)}</b></span>
      <span>风险扣分 <b>-{Number(candidate.risk_penalty).toFixed(1)}</b></span>
    </div>
    <div className="strategy-position-row">
      <span>当前建议仓位 <b>{percent(candidate.position)}</b></span>
      <span>触发后仓位上限 <b>{percent(candidate.planned_position)}</b></span>
    </div>
    {(candidate.alert_gate?.checks.length ?? 0) > 0 && <section className="strategy-alert-gate" aria-label="严格提醒门槛" data-eligible={candidate.alert_gate!.eligible}>
      <header><b>严格提醒门槛</b><span>{candidate.alert_gate!.eligible ? "全部通过" : `${candidate.alert_gate!.blockers.length} 项未通过`}</span></header>
      <div>{candidate.alert_gate!.checks.map((check) => <span className={check.passed ? "passed" : "blocked"} key={check.key}><i>{check.passed ? "✓" : "×"}</i><b>{check.label}</b><small>{check.detail}</small></span>)}</div>
    </section>}
    {(candidate.signal_votes?.length ?? 0) > 0 && <div className="strategy-vote-engine" aria-label="信号投票仓位引擎">
      <header><span>信号一致度 <b>{Number(candidate.vote_consensus ?? 0).toFixed(2)}</b></span><span>投票仓位 <b>{percent(candidate.vote_position ?? "0")}</b></span></header>
      <div>{candidate.signal_votes!.map((item) => <span className={item.vote > 0 ? "long" : item.vote < 0 ? "short" : "neutral"} key={item.signal}><b>{item.vote > 0 ? "+1" : item.vote < 0 ? "-1" : "0"}</b>{item.signal}<small>{percent(item.evidence_value)}</small></span>)}</div>
      <p>R(t) = Rmax × Σsⱼ / J · A 股长仓模式将负值截断为 0</p>
    </div>}
    <div className="strategy-evidence-columns">
      <div><h4><Target size={13} />触发条件</h4>{candidate.buy_triggers.map((item) => <p key={item}>{item}</p>)}</div>
      <div><h4><ShieldAlert size={13} />失效条件</h4>{candidate.invalidation_rules.map((item) => <p key={item}>{item}</p>)}</div>
    </div>
    {(candidate.missing_evidence.length > 0 || candidate.risk_flags.length > 0) && <footer>
      {candidate.missing_evidence.map((item) => <span className="pending" key={item}>{missingLabels[item] ?? item}</span>)}
      {candidate.risk_flags.map((item) => <span className="risk" key={item}>{item}</span>)}
    </footer>}
  </article>;
}

export function ShortTermStrategyWorkbench({ dashboard, loading, error }: Props) {
  if (loading) return <section className="short-strategy-workbench strategy-loading" aria-busy="true">
    <span className="scanner" /><b>正在计算全市场风格与策略匹配</b>
  </section>;
  if (error || !dashboard) return <section className="short-strategy-workbench strategy-error">
    <AlertTriangle size={20} /><b>{error || "短线策略数据暂不可用"}</b><p>原有 TICK、回测和 Kronos 证据不受影响。</p>
  </section>;

  const scoreItems = [
    ["情绪分", dashboard.regime.emotion_score],
    ["风险分", dashboard.regime.risk_score],
    ["热度分", dashboard.regime.heat_score],
    ["轮动分", dashboard.regime.rotation_score],
  ] as const;
  return <section className="short-strategy-workbench" aria-label="A股短线风格与策略工作台">
    <header className="strategy-workbench-header">
      <div><p><CircleGauge size={15} />REGIME / STRATEGY ENGINE V2.0</p><h2>短线风格与策略</h2><small>先定风格，再选模型；只有真实触发成立，候选才会升级为可提醒。</small></div>
      <div className={`strategy-quality ${dashboard.status}`}><i />{dashboard.status === "ready" ? "数据完整" : dashboard.status === "partial" ? "部分数据可用" : "数据不足"}<small>{dashboard.as_of} · 覆盖 {dashboard.regime.coverage_percent}%</small></div>
    </header>

    <div className="strategy-overview-grid">
      <section className="strategy-regime-gauge">
        <QuantChart option={regimeGauge(dashboard)} ariaLabel={`市场风格 ${dashboard.regime.regime ?? "待判定"}`} />
        <div><span>市场仓位系数 <b>{Number(dashboard.regime.market_coef).toFixed(1)}</b></span><span>规则命中 <b>{dashboard.regime.rule_matched ? "完整" : "近似"}</b></span></div>
      </section>
      <section className="strategy-score-dashboard" role="region" aria-label="市场风格评分">
        {scoreItems.map(([label, raw]) => {
          const value = number(raw);
          return <div className={scoreTone(label, value)} data-state={value === null ? "unavailable" : "ready"} key={label}><span>{label}</span><strong>{value === null ? "--" : value.toFixed(1)}</strong><i><b style={{ width: `${value ?? 0}%` }} /></i></div>;
        })}
      </section>
      <section className="strategy-model-fit">
        <div><h3><CheckCircle2 size={14} />适合手法</h3>{dashboard.regime.suitable_strategies.map((item) => <span className="positive" key={item}>{item}</span>)}</div>
        <div><h3><ShieldAlert size={14} />回避手法</h3>{dashboard.regime.avoid_strategies.map((item) => <span className="danger" key={item}>{item}</span>)}</div>
        <p>{dashboard.discipline}</p>
      </section>
    </div>

    <section className="strategy-model-pool" role="region" aria-label="六模型策略池">
      <header><div><Target size={15} /><h3>六模型策略池</h3></div><small>高亮模型与当前市场风格匹配，未高亮模型保持待机</small></header>
      <div>{dashboard.strategy_models.map((model) => <article className={`${model.selected ? "selected" : "standby"} ${model.defensive ? "defensive" : ""}`} key={model.name}>
        <b>{model.name}</b><span>{model.selected ? "当前适配" : "待机"}</span><small>{model.applicable_regimes.join(" / ")}</small>
      </article>)}</div>
    </section>

    <section className="strategy-market-metrics" role="region" aria-label="全市场实时指标">
      <header><div><Database size={15} /><h3>全市场指标扫描</h3></div><small>ClosePos = (最新价 - 最低价) / max(最高价 - 最低价, 0.01)</small></header>
      <div>{metricDefinitions.map((definition) => {
        const value = number(dashboard.metrics[definition.key]);
        const flowCoverage = number(dashboard.metrics.net_positive_ratio_coverage_percent);
        const unavailableDetail = definition.key === "net_positive_ratio" && flowCoverage !== null
          ? `资金流仅覆盖 ${flowCoverage.toFixed(2)}%，未达到全市场计算门槛`
          : "数据待补全";
        return <article className={value === null ? "missing" : "ready"} key={definition.key}><span>{definition.label}</span><strong>{value === null ? "--" : `${value.toFixed(definition.suffix === "x" ? 2 : 1)}${definition.suffix}`}</strong><small>{value === null ? unavailableDetail : definition.detail}</small></article>;
      })}</div>
    </section>

    {dashboard.candidate_funnel && <CandidateFunnel funnel={dashboard.candidate_funnel} />}
    <QuantEvidenceSummary dashboard={dashboard} />
    {(dashboard.field_evidence?.length ?? 0) > 0 && <FieldEvidenceDetails entries={dashboard.field_evidence!} />}
    {(dashboard.evidence_ledger?.length ?? 0) > 0 && <EvidenceLedger entries={dashboard.evidence_ledger!} />}

    <section className="strategy-recommendations">
      <header><div><Target size={15} /><h3>模型匹配候选</h3></div><small>StrategyScore = 风格×40 + 个股×30 + 触发×20 + 盈亏比×10 - 风险扣分</small></header>
      {dashboard.candidates.length > 0 ? <div className="strategy-tag-grid">{dashboard.candidates.map((candidate) => <CandidateTag candidate={candidate} key={candidate.symbol} />)}</div> : <div className="strategy-no-candidates"><ShieldAlert size={20} /><b>当前不强行推荐股票</b><p>{dashboard.discipline}</p></div>}
    </section>
  </section>;
}
