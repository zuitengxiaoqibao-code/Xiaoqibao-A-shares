import { useEffect, useState } from "react";
import { AlertTriangle, Link2, Plus, ShieldCheck, Trash2 } from "lucide-react";

import type {
  PortfolioPositionInput,
  PortfolioPositionRemover,
  PortfolioPositionSaver,
  PortfolioRiskAnalyzer,
  PortfolioRiskLoader,
  PortfolioRiskResponse,
} from "./types";


type Draft = PortfolioPositionInput & { id: number };

function money(value: string | null): string {
  if (value === null || value === "") return "--";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "--";
}

function pct(value: string | null): string {
  if (value === null || value === "") return "--";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(2)}%` : "--";
}

export function PortfolioRiskPanel({ analyze, load, savePosition, removePosition }: {
  analyze?: PortfolioRiskAnalyzer;
  load?: PortfolioRiskLoader;
  savePosition?: PortfolioPositionSaver;
  removePosition?: PortfolioPositionRemover;
}) {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [sequence, setSequence] = useState(1);
  const [result, setResult] = useState<PortfolioRiskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [persistedLoaded, setPersistedLoaded] = useState(false);
  const [error, setError] = useState("");
  const add = () => { setDrafts((items) => [...items, { id: sequence, symbol: "", shares: "", cost_price: "" }]); setSequence((value) => value + 1); };
  const update = (id: number, key: keyof PortfolioPositionInput, value: string) => setDrafts((items) => items.map((item) => item.id === id ? { ...item, [key]: value } : item));
  useEffect(() => {
    if (!load) return undefined;
    let active = true;
    setLoading(true);
    setError("");
    void load().then((value) => {
      if (!active) return;
      setResult(value);
      setDrafts(value.positions.map((item, index) => ({
        id: index + 1,
        symbol: item.symbol,
        shares: item.shares,
        cost_price: item.cost_price,
      })));
      setSequence(value.positions.length + 1);
      setPersistedLoaded(true);
    }).catch(() => {
      if (active) setError("本地持仓读取失败，请稍后重试");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [load]);
  const remove = async (item: Draft) => {
    setError("");
    if (removePosition && /^\d{6}$/.test(item.symbol)) {
      setLoading(true);
      try { setResult(await removePosition(item.symbol)); }
      catch { setError("本地持仓删除失败，请稍后重试"); return; }
      finally { setLoading(false); }
    }
    setDrafts((items) => items.filter((candidate) => candidate.id !== item.id));
  };
  const valid = drafts.length > 0 && drafts.every((item) => /^\d{6}$/.test(item.symbol) && Number(item.shares) > 0 && Number(item.cost_price) > 0);
  const run = async () => {
    if ((!analyze && !savePosition) || !valid) return;
    setLoading(true); setError("");
    try {
      const positions = drafts.map(({ symbol, shares, cost_price }) => ({ symbol, shares, cost_price }));
      if (savePosition) {
        let latest: PortfolioRiskResponse | null = null;
        for (const position of positions) latest = await savePosition(position);
        if (latest) setResult(latest);
        setPersistedLoaded(true);
      } else if (analyze) {
        setResult(await analyze({ positions }));
      }
    } catch {
      setError("组合风险计算失败，请检查本地日线和持仓输入");
    } finally {
      setLoading(false);
    }
  };

  return <section className="portfolio-risk-panel" aria-label="组合风险仪表盘">
    <header><div><p className="eyebrow">PORTFOLIO RISK</p><h2>组合风险仪表盘</h2><p>持仓由用户手动录入；价格、行业和相关性只使用已核验的本地证据。</p></div><button type="button" onClick={add}><Plus size={15} />添加持仓</button></header>
    <div className="portfolio-position-editor">
      {persistedLoaded && <div className="portfolio-persistence-state"><ShieldCheck size={14} />本地持仓已载入</div>}
      {drafts.length === 0 && <div className="portfolio-empty"><ShieldCheck /><b>请先录入真实持仓</b><p>系统不会预置模拟股票、模拟成本或模拟仓位。</p></div>}
      {drafts.map((item, index) => <div className="portfolio-position-row" key={item.id}>
        <label>股票代码<input aria-label={`股票代码 ${index + 1}`} value={item.symbol} onChange={(event) => update(item.id, "symbol", event.target.value.trim())} maxLength={6} /></label>
        <label>持股数量<input aria-label={`持股数量 ${index + 1}`} inputMode="decimal" value={item.shares} onChange={(event) => update(item.id, "shares", event.target.value)} /></label>
        <label>成本价<input aria-label={`成本价 ${index + 1}`} inputMode="decimal" value={item.cost_price} onChange={(event) => update(item.id, "cost_price", event.target.value)} /></label>
        <button type="button" aria-label={`删除持仓 ${index + 1}`} onClick={() => { void remove(item); }}><Trash2 size={15} /></button>
      </div>)}
      {drafts.length > 0 && <div className="portfolio-editor-actions"><button type="button" disabled={!valid || loading || (!analyze && !savePosition)} onClick={() => { void run(); }}>{loading ? "正在计算…" : savePosition ? "保存并计算组合风险" : "计算组合风险"}</button><small>只保存到本机，不会发送委托，也不会修改任何交易软件。</small></div>}
      {error && <p className="portfolio-error" role="alert"><AlertTriangle size={15} />{error}</p>}
    </div>
    {result && <div className="portfolio-risk-results" data-status={result.status}>
      <div className="portfolio-risk-kpis">
        <div><span>组合市值</span><strong>{money(result.total_market_value)}</strong><small>成本 {money(result.total_cost)}</small></div>
        <div><span>浮动盈亏</span><strong className={Number(result.total_pnl) >= 0 ? "up" : "down"}>{money(result.total_pnl)}</strong><small>{pct(result.total_pnl_percent)}</small></div>
        <div><span>HHI 集中度</span><strong>{result.hhi ?? "--"}</strong><small>越高越集中</small></div>
        <div><span>平均相关性</span><strong>{result.average_correlation ?? "--"}</strong><small>阈值 0.65</small></div>
        <div><span>市场仓位上限</span><strong>{pct(result.market_position_cap_percent)}</strong><small>{result.market_regime ?? "市场风格不可用"}</small></div>
      </div>
      <section><header><h3>行业集中度</h3><small>单行业警戒线 35%</small></header><div className="portfolio-industry-bars">{result.industries.length ? result.industries.map((item) => <div key={item.industry}><span>{item.industry} {pct(item.weight_percent)}</span><i><b style={{ width: `${Math.min(100, Number(item.weight_percent))}%` }} /></i><small>{item.symbols.join(" · ")}</small></div>) : <p>行业证据不足，暂不计算。</p>}</div></section>
      <section><header><h3>高相关股票对</h3><small>相关系数至少 0.80，重叠不少于 20 日</small></header><div className="portfolio-correlation-list">{result.high_correlation_pairs.length ? result.high_correlation_pairs.map((item) => <article key={`${item.left_symbol}-${item.right_symbol}`}><Link2 size={15} /><div><b>{item.left_symbol} / {item.right_symbol}</b><small>{item.overlap_days} 日重叠</small></div><strong>{Number(item.correlation).toFixed(2)}</strong></article>) : <p>暂无达到阈值的真实股票对。</p>}</div></section>
      <section><header><h3>机械压力测试</h3><small>只做统一冲击测算，不是价格预测</small></header><div className="portfolio-stress-grid">{result.stress_scenarios.map((item) => <article key={item.key} data-status={item.status}><span>{item.label}</span><strong>{item.status === "ready" ? money(item.estimated_loss) : "不可用"}</strong><small>{item.detail}</small></article>)}</div></section>
      {result.warnings.length > 0 && <div className="portfolio-warnings">{result.warnings.map((item) => <span key={item}><AlertTriangle size={13} />{item}</span>)}</div>}
    </div>}
  </section>;
}
