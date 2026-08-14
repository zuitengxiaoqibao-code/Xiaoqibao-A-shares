import { AlertTriangle, Clock3, Database, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { RiskStatus } from "../governance/GovernanceViews";
import { PortfolioRiskPanel } from "../portfolio-risk/PortfolioRiskPanel";
import type { PortfolioPositionRemover, PortfolioPositionSaver, PortfolioRiskAnalyzer, PortfolioRiskLoader } from "../portfolio-risk/types";
import { friendlyError } from "../../shared/friendlyError";
import { DataWatermarkStrip } from "../../shared/evidence/DataWatermarkStrip";

export function BeginnerRiskView({ load, analyzePortfolio, loadPortfolio, savePortfolioPosition, removePortfolioPosition }: {
  load?: () => Promise<RiskStatus>;
  analyzePortfolio?: PortfolioRiskAnalyzer;
  loadPortfolio?: PortfolioRiskLoader;
  savePortfolioPosition?: PortfolioPositionSaver;
  removePortfolioPosition?: PortfolioPositionRemover;
}) {
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [data, setData] = useState<RiskStatus | null>(null);
  const request = useRef(0);
  const reload = useCallback(async () => {
    const current = ++request.current;
    if (!load) { setState("error"); setMessage("风险数据服务尚未连接"); return; }
    setState("loading"); setMessage("");
    try { const loaded = await load(); if (current === request.current) { setData(loaded); setState("ready"); } }
    catch (error) { if (current === request.current) { setState("error"); setMessage(friendlyError(error, "风险数据")); } }
  }, [load]);
  useEffect(() => { void reload(); return () => { request.current += 1; }; }, [reload]);
  return <main className="beginner-page beginner-risk"><header><p className="eyebrow">风险提醒</p><h1>当前风险状态</h1><p>这里汇总研究过程中需要优先留意的数据与市场风险。</p></header>
    {state === "loading" && <section className="beginner-empty" aria-busy="true"><RefreshCw className="spin" /><h2>正在检查风险状态</h2></section>}
    {state === "error" && <section className="beginner-empty risk-error" role="alert"><AlertTriangle /><h2>{message}</h2><button type="button" onClick={() => void reload()}>重试</button></section>}
    {state === "ready" && data && <><DataWatermarkStrip
      status={data.overall_level === "unavailable" ? "unavailable" : "ready"}
      observedAt={data.generated_at}
      generatedAt={data.generated_at}
      sourceCount={new Set((data.alerts ?? []).map((item) => item.source)).size}
      sampleCount={(data.dimensions ?? []).length + (data.alerts ?? []).length}
      refreshState="ready"
      limitations={(data.dimensions ?? []).filter((item) => item.level === "unavailable").map((item) => `${item.label}待核验`)}
    /><RiskDashboard data={data}/></>}
    {(analyzePortfolio || loadPortfolio) && <PortfolioRiskPanel
      analyze={analyzePortfolio}
      load={loadPortfolio}
      savePosition={savePortfolioPosition}
      removePosition={removePortfolioPosition}
    />}
  </main>;
}

const levelName = { low: "较低", medium: "中等", high: "较高", unavailable: "待核验" };
const riskLayers = [
  ["市场", ["market_sentiment"]],
  ["个股", ["stock_specific"]],
  ["事件", ["news_events"]],
  ["数据", ["data_freshness", "evidence_coverage"]],
  ["策略", ["strategy_execution"]],
] as const;

function RiskDashboard({ data }: { data: RiskStatus }) {
  const level = data.overall_level ?? "unavailable";
  const dimensions = data.dimensions ?? [];
  const alerts = data.alerts ?? [];
  const high = dimensions.filter((item) => item.level === "high").length + alerts.filter((item) => item.level === "high").length;
  const medium = dimensions.filter((item) => item.level === "medium").length + alerts.filter((item) => item.level === "medium").length;
  const available = dimensions.filter((item) => item.level !== "unavailable").length;
  return <section className="risk-dashboard" data-level={level}>
    <div className="risk-dashboard__overview">
      <div className="risk-level-gauge" aria-label={`整体风险${levelName[level]}`}><div><ShieldAlert size={24}/><b>{levelName[level]}</b><span>整体风险</span></div></div>
      <div><p className="eyebrow">EVIDENCE-BASED RISK</p><h2>当前风险：{levelName[level]}</h2><p>仅汇总已经取得证据的市场、数据和新闻风险；无法验证的项目单独标记。</p></div>
      <dl><div><dt>高风险</dt><dd>{high}</dd></div><div><dt>中风险</dt><dd>{medium}</dd></div><div><dt>可用维度</dt><dd>{available}/{dimensions.length || 4}</dd></div></dl>
    </div>
    <section className="risk-dashboard__section"><header><Database size={17}/><div><h2>风险检查矩阵</h2><p>每个结论都附带证据和处理动作</p></div></header>
      <div className="risk-layer-strip" aria-label="五层风险矩阵">{riskLayers.map(([label, ids]) => {
        const items = dimensions.filter((item) => (ids as readonly string[]).includes(item.id));
        const resolved = items.filter((item) => item.level !== "unavailable");
        const layerLevel = resolved.length ? resolved.reduce((highest, item) => item.level === "high" || (item.level === "medium" && highest === "low") ? item.level : highest, "low" as "low" | "medium" | "high") : "unavailable";
        return <span key={label} data-level={layerLevel}><b>{label}</b><small>{levelName[layerLevel]}</small></span>;
      })}</div>
      <div className="risk-dimension-grid">{dimensions.length ? dimensions.map((item) => <article key={item.id} data-level={item.level}><header><span>{item.label}</span><b>{levelName[item.level]}</b></header><strong>{item.value}</strong><p>{item.evidence}</p><footer><ShieldCheck size={14}/>{item.action}</footer></article>) : <div className="risk-dashboard__empty"><Database/><b>风险维度数据待补齐</b><p>接口已连接，但当前没有可核验的市场快照。</p></div>}</div>
    </section>
    <section className="risk-dashboard__section"><header><ShieldAlert size={17}/><div><h2>已核验风险提醒</h2><p>按影响级别展示近期负面事件</p></div></header>
      <div className="risk-alert-list">{alerts.length ? alerts.map((alert) => <article key={alert.id} data-level={alert.level}><div className="risk-alert-list__level">{levelName[alert.level]}</div><div><header><span>{alert.category}</span><time><Clock3 size={13}/>{new Date(alert.observed_at).toLocaleString("zh-CN", { hour12: false })}</time></header><h3>{alert.title}</h3><p><b>证据</b>{alert.evidence}</p><p><b>处理</b>{alert.action}</p><div className="risk-alert-list__tags">{alert.affected_instruments.map((item) => <span key={item}>{item}</span>)}{alert.affected_sectors.map((item) => <span key={item}>{item}</span>)}<small>来源：{alert.source}</small></div></div></article>) : <div className="risk-dashboard__empty"><ShieldCheck/><b>暂无已证实的负面事件</b><p>这不等于没有风险，系统仍会持续核验新闻和行情。</p></div>}</div>
    </section>
  </section>;
}
