import { useCallback, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, BarChart3, BrainCircuit, Database, FlaskConical,
  Network, ShieldCheck,
} from "lucide-react";

import type {
  QuantResearchLoader, QuantResearchSnapshot, QuantResearchStatus, QuantRiskGateCheck,
} from "./types";
import { useQuantLiveResource } from "./useQuantLiveRefresh";


type Props = { load: QuantResearchLoader };

const MODULES = [
  ["factor_registry", "因子注册"], ["factor_health", "因子健康"],
  ["risk", "风险闸门"], ["opportunities", "机会扫描"],
  ["shadow", "60日验证"], ["etf", "ETF映射"], ["hypotheses", "AI假设"],
] as const;

const STATUS_COPY: Record<QuantResearchStatus, string> = {
  ready: "就绪", partial: "部分可用", insufficient: "样本不足", stale: "数据陈旧",
  unavailable: "暂不可用", error: "读取失败",
};

function numberText(value: string | null | undefined, suffix = ""): string {
  if (value === null || value === undefined || value === "") return "--";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(2)}${suffix}` : "--";
}

function pitchState(status: string): string {
  if (status === "triggered") return "触发已确认";
  if (status === "excluded") return "风险排除";
  if (status === "insufficient") return "证据不足";
  return "等待触发";
}

function isResearchSnapshot(value: unknown): value is QuantResearchSnapshot {
  if (typeof value !== "object" || value === null) return false;
  const snapshot = value as Partial<QuantResearchSnapshot>;
  return snapshot.formula_version === "quant-research-intelligence-v1"
    && typeof snapshot.as_of === "string"
    && Array.isArray(snapshot.risk_summaries)
    && Array.isArray(snapshot.opportunities)
    && typeof snapshot.module_statuses === "object"
    && snapshot.module_statuses !== null;
}

const RISK_STATUS_COPY: Record<QuantRiskGateCheck["status"], string> = {
  pass: "通过", warn: "警告", block: "阻断", unavailable: "缺证据",
};

const RISK_PRIORITY: Record<QuantRiskGateCheck["status"], number> = {
  block: 0, warn: 1, unavailable: 2, pass: 3,
};

export function QuantResearchIntelligencePanel({ load }: Props) {
  const loader = useCallback(() => load(), [load]);
  const resource = useQuantLiveResource({
    loader,
    intervalMs: 60_000,
    errorMessage: "量化研究快照加载失败",
    initialDelayMs: 1_400,
    cache: { key: "quant-research-intelligence", validate: isResearchSnapshot },
  });
  const [filter, setFilter] = useState("all");
  const snapshot = resource.data;
  const types = useMemo(() => {
    if (!snapshot) return [];
    const labels = new Map<string, string>();
    snapshot.opportunities.forEach((item) => labels.set(item.opportunity_type, item.opportunity_name));
    return [...labels.entries()];
  }, [snapshot]);
  const pitches = useMemo(
    () => snapshot?.opportunities.filter((item) => filter === "all" || item.opportunity_type === filter) ?? [],
    [filter, snapshot],
  );
  const opportunityNames = useMemo(() => {
    const names = new Map<string, string>();
    snapshot?.opportunities.forEach((item) => names.set(item.symbol, item.name));
    return names;
  }, [snapshot]);

  if (!snapshot && resource.status === "error") {
    return <section className="quant-research-band quant-research-error" aria-label="量化研究智能">
      <AlertTriangle size={22} />
      <div><h2>量化研究快照加载失败</h2><p>请检查本地数据状态后重试；其他量化模块不受影响。</p></div>
    </section>;
  }
  if (!snapshot) {
    return <section className="quant-research-band quant-research-loading" aria-label="量化研究智能" aria-busy="true">
      <BrainCircuit size={24} />
      <div><h2>正在建立量化研究快照</h2><p>读取因子注册、风险闸门与影子验证</p><span><i /></span></div>
    </section>;
  }

  return <section className="quant-research-band" aria-label="量化研究智能">
    <header className="quant-research-header">
      <div><span><BrainCircuit size={16} />RESEARCH INTELLIGENCE</span><h2>研究智能</h2></div>
      <div className="quant-research-freshness" data-status={snapshot.status}>
        <strong>{STATUS_COPY[snapshot.status]}</strong>
        <span>{resource.refreshing ? "正在后台刷新，当前继续展示完整快照" : snapshot.refresh_stage}</span>
        <small>{snapshot.as_of} · {snapshot.snapshot_source === "cache" ? "缓存快照" : "最新计算"}</small>
      </div>
    </header>

    <div className="quant-research-modules">
      {MODULES.map(([key, label]) => {
        const state = snapshot.module_statuses[key];
        return <div key={key} data-status={state?.status ?? "unavailable"}>
          <span>{label}</span><strong>{STATUS_COPY[state?.status ?? "unavailable"]}</strong>
          <small>{state?.message ?? "模块状态未返回"}</small>
        </div>;
      })}
    </div>

    <div className="quant-research-evidence-grid">
      <section className="quant-research-section" aria-label="因子治理">
        <header><div><BarChart3 size={17} /><h3>因子治理</h3></div><span>{snapshot.factor_registry.factors.length} 个已注册</span></header>
        <div className="quant-factor-registers">
          {snapshot.factor_registry.factors.map((item) => <div key={item.factor_id}>
            <b>{item.name}</b><span>{item.family}</span><small>{item.lifecycle === "active" ? "有效" : item.lifecycle}</small>
          </div>)}
        </div>
        {snapshot.factor_health.length ? <div className="quant-factor-health-list">
          {snapshot.factor_health.map((item) => <div key={item.factor_id} data-status={item.status}>
            <b>{item.name}</b><span>RankIC {numberText(item.rank_ic_20)}</span><span>ICIR {numberText(item.icir)}</span><small>{item.valid_day_count} 个有效交易日</small>
          </div>)}
        </div> : <p className="quant-research-note">{snapshot.module_statuses.factor_health.message}</p>}
      </section>

      <section className="quant-research-section" aria-label="风险闸门">
        <header><div><ShieldCheck size={17} /><h3>风险闸门</h3></div><span>{snapshot.risk_summaries.length} 只候选</span></header>
        <div className="quant-risk-gate-list">
          {snapshot.risk_summaries.map((summary) => {
            const counts = { pass: 0, warn: 0, block: 0, unavailable: 0 };
            summary.checks.forEach((check) => { counts[check.status] += 1; });
            const priorityChecks = [...summary.checks]
              .filter((check) => check.status !== "pass")
              .sort((left, right) => RISK_PRIORITY[left.status] - RISK_PRIORITY[right.status]);
            return <article
              key={summary.symbol}
              data-testid={`quant-risk-card-${summary.symbol}`}
              data-status={summary.overall_status}
              aria-label={`${opportunityNames.get(summary.symbol) ?? summary.symbol} ${summary.symbol} 风险闸门`}
            >
              <header>
                <div><b>{opportunityNames.get(summary.symbol) ?? summary.symbol}</b><span>{summary.symbol}</span></div>
                <strong>{summary.overall_status === "pass" ? "可观察" : summary.overall_status === "warn" ? "需确认" : "已阻断"}</strong>
              </header>
              <div className="quant-risk-counts">
                {(Object.keys(counts) as QuantRiskGateCheck["status"][]).map((status) => (
                  <span key={status} data-status={status}>{RISK_STATUS_COPY[status]} {counts[status]}</span>
                ))}
              </div>
              <div className="quant-risk-reasons">
                {priorityChecks.length ? priorityChecks.map((check) => <p key={check.key} data-status={check.status}>
                  <b>{check.label}</b><span>{check.reason}</span>
                </p>) : <p data-status="pass"><b>当前结论</b><span>已返回的风险检查均通过。</span></p>}
              </div>
              <details>
                <summary>查看审计指标与来源</summary>
                <div className="quant-risk-audit-list">
                  {summary.checks.map((check) => <div key={check.key} data-status={check.status}>
                    <header><b>{check.label}</b><span>{RISK_STATUS_COPY[check.status]}</span></header>
                    <p>{check.reason}</p>
                    <small>指标 {check.metric_value ?? "--"} · 阈值 {check.threshold ?? "--"}</small>
                    <small>来源 {check.source_snapshot_ids.length ? check.source_snapshot_ids.join("、") : "暂无快照编号"}</small>
                  </div>)}
                </div>
              </details>
            </article>;
          })}
          {!snapshot.risk_summaries.length && <p className="quant-research-note">{snapshot.module_statuses.risk.message}</p>}
        </div>
      </section>
    </div>

    <section className="quant-opportunity-section" aria-label="机会候选卡">
      <header><div><Activity size={17} /><h3>机会候选</h3></div><span>综合分只用于排序，不代表概率</span></header>
      <div className="quant-opportunity-filters">
        <button type="button" className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>全部</button>
        {types.map(([key, label]) => <button type="button" className={filter === key ? "active" : ""} key={key} onClick={() => setFilter(key)}>{label}</button>)}
      </div>
      <div className="quant-opportunity-list">
        {pitches.map((item) => <article key={`${item.symbol}-${item.opportunity_type}`} data-status={item.status}>
          <header><div><b>{item.name}</b><span>{item.symbol}</span></div><strong>{numberText(item.strategy_score)}</strong></header>
          <div className="quant-pitch-tags"><span>{item.opportunity_name}</span><span>{item.market_regime ?? "风格待确认"}</span><span>{pitchState(item.status)}</span></div>
          <p>{item.core_evidence.join(" · ")}</p>
          <dl><div><dt>校准胜率</dt><dd>{item.calibrated_hit_rate_percent === null ? "样本不足，不显示胜率" : numberText(item.calibrated_hit_rate_percent, "%")}</dd></div><div><dt>成熟样本</dt><dd>{item.shadow_sample_count} 条</dd></div></dl>
          <div className="quant-pitch-rules"><span><b>触发</b>{item.trigger_rules[0]}</span><span><b>失效</b>{item.invalidation_rules[0]}</span></div>
          {item.risk_gate.blockers.length > 0 && <p className="quant-pitch-blocker">{item.risk_gate.blockers.join("；")}</p>}
        </article>)}
        {!pitches.length && <p className="quant-research-note">当前筛选没有可展示的真实候选。</p>}
      </div>
    </section>

    <div className="quant-research-lower-grid">
      <section><header><Database size={17} /><h3>60日影子验证</h3></header>{snapshot.shadow_cohorts.length ? snapshot.shadow_cohorts.map((item) => <p key={`${item.opportunity_type}-${item.horizon}`}>{item.opportunity_type} · {item.sample_count} 条 · {item.hit_rate_percent === null ? "样本不足" : numberText(item.hit_rate_percent, "%")}</p>) : <p>{snapshot.module_statuses.shadow.message}</p>}</section>
      <section><header><Network size={17} /><h3>ETF暴露映射</h3></header>{snapshot.etf_exposures.length ? snapshot.etf_exposures.map((item) => <p key={item.etf_symbol}>{item.etf_name} {item.etf_symbol} · 相关 {numberText(item.correlation)}</p>) : <p>{snapshot.module_statuses.etf.message}</p>}</section>
      <section><header><FlaskConical size={17} /><h3>AI可证伪假设</h3></header>{snapshot.hypotheses.length ? snapshot.hypotheses.map((item) => <p key={item.hypothesis_id}>{item.statement}</p>) : <p>{snapshot.module_statuses.hypotheses.message}</p>}</section>
    </div>
  </section>;
}
