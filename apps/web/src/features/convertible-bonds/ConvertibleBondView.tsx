import { useEffect, useRef, useState } from "react";
import { AlertTriangle, FileText, Gauge, LoaderCircle, Search, ShieldAlert } from "lucide-react";
import type { BondCandidates, BondDashboard, BondDiagnosis, BondDiagnosisBatch } from "./types";
import { friendlyError } from "../../shared/friendlyError";
import { BondTaskFlow } from "./BondTaskFlow";
import { bondTaskCards } from "./taskCards";

type Props = {
  loadDashboard: () => Promise<BondDashboard>;
  loadDiagnosis: (code: string) => Promise<BondDiagnosis>;
  loadCachedDiagnosis?: (code: string) => Promise<BondDiagnosis | null>;
  loadCandidates: (filters?: Record<string, string>) => Promise<BondCandidates>;
  diagnoseDiscovered?: (limit?: number) => Promise<BondDiagnosisBatch>;
  openBondCompliance?: () => void;
};

const sourceName: Record<string, string> = { tencent: "腾讯", eastmoney: "东方财富" };
const filterName: Record<string, string> = {
  max_conversion_premium: "最高转股溢价率",
  min_turnover_amount: "最低成交额（元）",
  min_remaining_size: "最低剩余规模（亿元）",
  min_days_to_maturity: "最低到期天数",
};
const value = (item: string | null, suffix = "") => item == null ? "未知" : `${item}${suffix}`;
const redemptionLabel: Record<string, string> = { unknown: "强赎状态未知", triggered: "强赎已触发", announced: "强赎已公告", completed: "强赎已完成" };
const riskLabel: Record<string, string> = { eligible: "可观察", observe_only: "仅观察", exclude: "排除" };
const riskReason: Record<string, string> = {
  pure_bond_value: "纯债价值缺失", turnover_amount: "成交额缺失",
  bond_liquidity_missing: "成交额缺失", bond_conversion_premium_missing: "转股溢价率缺失",
  bond_maturity_too_near: "距离到期过近", bond_remaining_size_too_small: "剩余规模偏小",
  bond_strong_redemption_unknown: "强赎状态未知",
  bond_strong_redemption_triggered: "已触发强赎，按规则排除",
  bond_strong_redemption_announced: "已公告强赎，按规则排除",
  bond_strong_redemption_completed: "强赎流程已完成，按规则排除",
};
const discoveryStateLabel: Record<string, string> = {
  discovered: "未诊断",
  diagnosed: "可观察",
  unavailable: "数据不可用",
  risk_excluded: "风险排除",
};
const batchReasonLabel: Record<string, string> = {
  source_unauthorized: "数据源未授权",
  clauses_unavailable: "条款数据暂不可用",
  upstream_unavailable: "上游服务暂不可用",
  invalid_provider_data: "数据格式无法核验",
};

function presentRedemptionEvidence(field: string, rawValue: string): { label: string; value: string } {
  const providerField = field.split(".").pop() ?? field;
  const dateValue = /^\d{4}-\d{2}-\d{2}(?:[ T]00:00:00)?$/.test(rawValue)
    ? rawValue.slice(0, 10)
    : rawValue;
  if (providerField.startsWith("NOTICE_DATE_")) return { label: "赎回公告日期", value: dateValue };
  if (providerField.startsWith("EXECUTE_START_DATE")) return { label: "赎回执行起始日", value: dateValue };
  if (providerField.startsWith("EXECUTE_END_DATE") || providerField.startsWith("ACTUAL_EXECUTE_DATE")) {
    return { label: "赎回执行完成日", value: dateValue };
  }
  if (providerField.startsWith("EXECUTE_REASON_")) {
    return {
      label: "执行原因",
      value: /^\d+$/.test(rawValue) ? `原始代码 ${rawValue}（数据源未提供文字释义）` : rawValue,
    };
  }
  if (providerField === "IS_REDEEM") return { label: "数据源赎回标记", value: rawValue };
  if (providerField.includes("TRIGGER")) return { label: "强赎触发标记", value: rawValue };
  if (providerField.includes("REDEEM_STATUS")) return { label: "强赎状态标记", value: rawValue };
  if (providerField.includes("ANNOUNCEMENT_TYPE")) return { label: "公告类型", value: rawValue };
  return { label: "其他原始证据", value: rawValue };
}

export function ConvertibleBondView({ loadDashboard, loadDiagnosis, loadCachedDiagnosis, loadCandidates, diagnoseDiscovered, openBondCompliance }: Props) {
  const [tab, setTab] = useState<"overview" | "diagnosis" | "candidates">("overview");
  const [code, setCode] = useState("113065");
  const [dashboard, setDashboard] = useState<BondDashboard | null>(null);
  const [diagnosis, setDiagnosis] = useState<BondDiagnosis | null>(null);
  const [candidates, setCandidates] = useState<BondCandidates | null>(null);
  const [batchReport, setBatchReport] = useState<BondDiagnosisBatch | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ max_conversion_premium: "", min_turnover_amount: "", min_remaining_size: "", min_days_to_maturity: "" });
  const diagnosisCache = useRef(new Map<string, BondDiagnosis>());
  const diagnosisRequest = useRef(0);

  useEffect(() => {
    loadDashboard().then(setDashboard).catch((e) => setError(friendlyError(e, "转债概览")));
    loadCandidates().then(setCandidates).catch(() => undefined);
  }, [loadCandidates, loadDashboard]);
  async function inspect(target = code) {
    const request = ++diagnosisRequest.current;
    let cached = diagnosisCache.current.get(target) ?? null;
    setLoading(true);
    setError("");
    setDiagnosis((current) => cached ?? (current?.bond.code === target ? current : null));
    if (!cached && loadCachedDiagnosis) {
      try {
        cached = await loadCachedDiagnosis(target);
        if (request !== diagnosisRequest.current) return;
        if (cached) {
          diagnosisCache.current.set(target, cached);
          setDiagnosis(cached);
        }
      } catch {
        // A cache read failure must not block the verified live refresh.
      }
    }
    try {
      const fresh = await loadDiagnosis(target);
      if (request !== diagnosisRequest.current) return;
      const current = { ...fresh, is_cached: false, cache_recorded_at: undefined };
      diagnosisCache.current.set(target, current);
      setDiagnosis(current);
    } catch (e) {
      if (request !== diagnosisRequest.current) return;
      setError(
        cached
          ? `${friendlyError(e, "转债诊断")} 已保留最近一次缓存快照。`
          : friendlyError(e, "转债诊断"),
      );
    } finally {
      if (request === diagnosisRequest.current) setLoading(false);
    }
  }
  async function showCandidates() { setTab("candidates"); setLoading(true); setError(""); try { setCandidates(await loadCandidates(filters)); } catch (e) { setError(friendlyError(e, "转债候选池")); } finally { setLoading(false); } }

  async function runBatchDiagnosis() {
    if (!diagnoseDiscovered) return;
    setLoading(true);
    setError("");
    try {
      setBatchReport(await diagnoseDiscovered(6));
      setCandidates(await loadCandidates(filters));
    } catch (e) {
      setError(friendlyError(e, "转债批量诊断"));
    } finally {
      setLoading(false);
    }
  }

  const unknownDetails = diagnosis
    ? diagnosis.risk.unknowns.map((item) => riskReason[item] ?? item).filter((item, index, values) => values.indexOf(item) === index)
    : [];
  const explanationDetails = diagnosis
    ? diagnosis.risk.explanations.map((item) => riskReason[item] ?? item).filter((item, index, values) => values.indexOf(item) === index && !unknownDetails.includes(item))
    : [];
  const riskSummaryText = [
    unknownDetails.length ? `数据待补齐：${unknownDetails.join("、")}` : "",
    explanationDetails.length ? `风险依据：${explanationDetails.join("、")}` : "",
  ].filter(Boolean).join("；") || "当前规则输入完整";
  const authorizationError = error.includes("尚未授权") || error.includes("来源权限");
  const taskCards = bondTaskCards(candidates);
  return <main className="terminal-page bond-domain bond-glass-workbench" role="region" aria-label="可转债独立工作台">
    <header className="bond-header bond-workbench-header"><div><p className="eyebrow">INDEPENDENT ASSET DOMAIN / CONVERTIBLE BONDS</p><h1>可转债专区</h1><p>独立任务工作台 · 行情、条款、估值与关联正股分层核验；状态不与 A 股混合。</p></div><div className="bond-domain-mark"><Gauge size={18} /><span>CB</span></div></header>
    <div className="bond-tabs" role="tablist">
      <button role="tab" aria-selected={tab === "overview"} onClick={() => setTab("overview")}>总览</button>
      <button role="tab" aria-selected={tab === "diagnosis"} onClick={() => setTab("diagnosis")}>诊断</button>
      <button role="tab" aria-selected={tab === "candidates"} onClick={() => void showCandidates()}>候选池</button>
    </div>
    {error && <div className="bond-alert" role="alert"><ShieldAlert size={18} />{error}{(authorizationError || error === "数据源尚未配置，请在数据设置中检查连接。") && openBondCompliance && <button onClick={openBondCompliance}>打开数据设置</button>}</div>}
    {loading && <div className="bond-loading" aria-busy="true"><LoaderCircle size={18} />正在核验数据源...</div>}
    {tab === "overview" && !loading && <><section className="bond-overview bond-workbench-summary"><div><span>已发现转债</span><strong>{dashboard?.discovered_count ?? dashboard?.bond_count ?? "—"}</strong></div><div><span>可观察</span><strong>{dashboard?.observable_count ?? 0}</strong></div><div><span>未诊断</span><strong>{dashboard?.undiagnosed_count ?? dashboard?.undignosed_count ?? dashboard?.unavailable_count ?? 0}</strong></div><div><span>数据不可用</span><strong>{dashboard?.data_unavailable_count ?? 0}</strong></div><div><span>风险排除</span><strong>{dashboard?.risk_excluded_count ?? 0}</strong></div><div><span>列表状态</span><strong>{dashboard?.status === "empty" ? "等待数据源" : "全市场发现池可用"}</strong></div><p>发现池与 A 股候选完全分离；只有行情、条款和风险输入完整且通过风险规则的转债才会进入可观察列表。</p></section><BondTaskFlow cards={taskCards} selectedCode={diagnosis?.bond.code ?? null} onSelect={(target) => { setCode(target); setTab("diagnosis"); void inspect(target); }} /></>}
    {tab === "diagnosis" && <section className="bond-diagnosis">
      <div className="bond-search"><Search size={17} /><label className="visually-hidden" htmlFor="bond-code">转债代码</label><input id="bond-code" value={code} maxLength={6} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}/><button onClick={() => void inspect()} disabled={loading}>诊断转债</button></div>
      {diagnosis && <>
        <div className="bond-state-line">{diagnosis.is_cached && <span className="warning"><LoaderCircle size={15}/>缓存快照 · {diagnosis.cache_recorded_at ? new Date(diagnosis.cache_recorded_at).toLocaleString("zh-CN") : "时间未知"}{loading ? " · 后台更新中" : ""}</span>}{diagnosis.status === "stale_quote" && <span className="warning"><AlertTriangle size={15}/>行情已过期</span>}{diagnosis.status === "source_conflict" && <span className="danger"><AlertTriangle size={15}/>数据源冲突</span>}<span>{sourceName[diagnosis.quote.source] ?? diagnosis.quote.source} · {new Date(diagnosis.quote.observed_at).toLocaleString("zh-CN")}</span></div>
        <div className="bond-identity"><div><small>{diagnosis.bond.code}</small><h2>{diagnosis.bond.name}</h2></div><div><small>关联正股（独立上下文）</small><b>{diagnosis.linked_stock.code} · {diagnosis.linked_stock.name}</b><span>{diagnosis.linked_stock.price}</span></div></div>
        <div className="bond-metrics"><div><span>转股价值</span><b>{value(diagnosis.metrics.conversion_value)}</b></div><div><span>转股溢价率</span><b>{value(diagnosis.metrics.conversion_premium)}</b></div><div><span>剩余规模</span><b>{diagnosis.clause_snapshot.remaining_size}</b></div><div><span>到期日</span><b>{diagnosis.clause_snapshot.maturity}</b></div><div><span>纯债溢价</span><b>{diagnosis.metrics.pure_bond_premium == null ? "未知（缺少纯债价值）" : diagnosis.metrics.pure_bond_premium}</b></div><div><span>当日成交额</span><b>{diagnosis.quote.turnover_amount == null ? "未知（缺少成交额）" : `${diagnosis.quote.turnover_amount} 元`}</b></div></div>
        <section className={`bond-risk-summary ${diagnosis.risk.outcome}`}><div><span>规则风险结论</span><b>{riskLabel[diagnosis.risk.outcome] ?? diagnosis.risk.outcome}</b></div><small>{riskSummaryText}</small></section>
        <section className="clause-evidence"><header><FileText size={17}/><div><b>{redemptionLabel[diagnosis.strong_redemption.state] ?? "强赎状态未知"}</b><small>{sourceName[diagnosis.strong_redemption.source] ?? diagnosis.strong_redemption.source} · {new Date(diagnosis.strong_redemption.observed_at).toLocaleString("zh-CN")}</small></div></header>{diagnosis.strong_redemption.clause_text && <p>{diagnosis.strong_redemption.clause_text}</p>}<dl>{Object.entries(diagnosis.strong_redemption.evidence_fields ?? {}).map(([field, fieldValue]) => { const evidence = presentRedemptionEvidence(field, fieldValue); return <div key={field} data-source-field={field}><dt>{evidence.label}</dt><dd>{evidence.value}</dd></div>; })}</dl></section>
      </>}
    </section>}
    {tab === "candidates" && !loading && <section className="bond-candidates"><div className="candidate-filters">{Object.entries(filters).map(([key, current]) => <label key={key}><span>{filterName[key]}</span><input aria-label={filterName[key]} inputMode="decimal" value={current} onChange={(event) => setFilters((items) => ({ ...items, [key]: event.target.value }))} /></label>)}<button onClick={() => void showCandidates()}>应用筛选</button>{diagnoseDiscovered && <button onClick={() => void runBatchDiagnosis()} disabled={loading}>诊断首批</button>}</div>{batchReport && <div className="bond-batch-report" role="status"><b>本轮完成诊断 {batchReport.diagnosed_count} 只 · 可观察 {batchReport.observable_count ?? 0} 只 · 风险排除 {batchReport.risk_excluded_count ?? batchReport.items.filter((item) => item.state === "diagnosed" && item.risk_outcome === "exclude").length} 只 · 数据不可用 {batchReport.data_unavailable_count ?? batchReport.unavailable_count} 只</b>{batchReport.items.map((item) => item.state === "unavailable" ? <small key={item.bond_code}>{item.bond_code}: {batchReasonLabel[item.reason_code] ?? "数据暂不可用"}</small> : <small key={item.bond_code}>{item.bond_code}: {item.risk_outcome === "exclude" ? "风险排除" : item.risk_outcome === "eligible" ? "可观察" : "已完成核验"}</small>)}</div>}{candidates?.coverage && <div className="bond-coverage"><span>发现 {candidates.coverage.discovered_count}</span><span>未诊断 {candidates.coverage.undignosed_count ?? 0}</span><span>数据不可用 {candidates.coverage.data_unavailable_count ?? candidates.coverage.unavailable_count}</span><span>风险排除 {candidates.coverage.risk_excluded_count ?? 0}</span><span>可观察 {candidates.coverage.observable_count ?? candidates.coverage.candidate_count}</span></div>}{candidates?.items.length ? candidates.items.map((item) => <div key={item.bond_code}><b>{item.bond_code}</b><span>转股溢价 {value(item.conversion_premium)}</span><small>可观察</small></div>) : <p>暂无可直接观察的转债；下方列表仍会显示每只转债当前处于未诊断、数据不可用或风险排除的具体原因。</p>}{candidates?.discovered?.map((item) => <button type="button" aria-label={`${item.bond_code} ${item.name}`} className={`bond-discovered-row ${item.state}`} key={`discovered-${item.bond_code}`} onClick={() => { setCode(item.bond_code); setTab("diagnosis"); void inspect(item.bond_code); }}><b>{item.bond_code}</b><span>{item.name}</span><small>{discoveryStateLabel[item.state]}{item.reason ? ` · ${item.reason}` : ""}</small></button>)}</section>}
  </main>;
}
