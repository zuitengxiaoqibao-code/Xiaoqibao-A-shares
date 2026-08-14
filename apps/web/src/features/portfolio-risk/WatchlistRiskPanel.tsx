import { AlertTriangle, Eye, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import type { WatchlistRiskLoader, WatchlistRiskResponse } from "./types";

export function WatchlistRiskPanel({ symbols, load }: { symbols: string[]; load: WatchlistRiskLoader }) {
  const [value, setValue] = useState<WatchlistRiskResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!symbols.length) return undefined;
    let active = true;
    setError("");
    void load(symbols).then((next) => { if (active) setValue(next); }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "观察篮子风险暂不可用"); });
    return () => { active = false; };
  }, [load, symbols.join(",")]);
  if (!symbols.length) return null;
  return <section className="portfolio-risk-panel" aria-label="观察篮子风险">
    <header><div><p className="eyebrow">OBSERVATION BASKET</p><h2>观察篮子风险</h2><p>仅对当前选择的 A 股做风险观察，不代表真实持仓或委托。</p></div><Eye size={20} /></header>
    {!value && !error && <div className="portfolio-empty"><RefreshCw className="spin" /><b>正在读取观察篮子风险</b></div>}
    {error && <div className="portfolio-error" role="alert"><AlertTriangle size={15} />{error}</div>}
    {value && <div className="portfolio-risk-results" data-status={value.status}><div className="portfolio-risk-kpis"><div><span>数据状态</span><strong>{value.status === "ready" ? "就绪" : value.status === "partial" ? "部分证据" : "不可用"}</strong><small>覆盖 {Number(value.coverage_percent).toFixed(2)}%</small></div><div><span>观察标的</span><strong>{value.valid_count}/{value.total_count}</strong><small>{value.as_of}</small></div><div><span>高相关股票对</span><strong>{value.high_correlation_pairs.length}</strong><small>重叠日线至少20日</small></div></div><div className="portfolio-correlation-list">{value.items.map((item) => <article key={item.symbol}><div><b>{item.name} {item.symbol}</b><small>{item.industry ?? "行业待核验"} · 波动 {item.volatility_20d_percent ?? "--"}%</small></div><strong>{item.status === "ready" ? "已核验" : "待核验"}</strong></article>)}</div>{value.warnings.length > 0 && <div className="portfolio-warnings">{value.warnings.map((warning) => <span key={warning}><AlertTriangle size={13} />{warning}</span>)}</div>}</div>}
  </section>;
}
