import type { CSSProperties } from "react";
import type { CompanyResearchResponse, FinancialPeriod, ResearchDimension } from "./types";
import { ValuationComparisonChart } from "./ValuationComparisonChart";

type Props = { value: CompanyResearchResponse };

function numeric(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function percent(value: number | null, digits = 1): string {
  return value === null ? "--" : `${(value * 100).toFixed(digits)}%`;
}

function amount(value: string | null | undefined): string {
  const parsed = numeric(value);
  if (parsed === null) return "--";
  if (Math.abs(parsed) >= 100_000_000) return `${(parsed / 100_000_000).toFixed(2)}亿`;
  if (Math.abs(parsed) >= 10_000) return `${(parsed / 10_000).toFixed(1)}万`;
  return parsed.toFixed(2);
}

function latestPeriod(value: CompanyResearchResponse): FinancialPeriod | null {
  return value.financial_history.latest_period
    ?? value.financial_history.annual_periods.at(-1)
    ?? value.financial_history.periods.at(-1)
    ?? null;
}

function score(value: ResearchDimension): number | null {
  const parsed = numeric(value.score);
  return parsed === null ? null : Math.max(0, Math.min(100, parsed));
}

function safeRatio(value: number | null, total: number | null): number | null {
  if (value === null || total === null || total <= 0) return null;
  return Math.max(0, Math.min(100, value / total * 100));
}

function Donut({ label, value, total, tone }: { label: string; value: number | null; total: number | null; tone: "liability" | "equity" }) {
  const ratio = safeRatio(value, total);
  return <div className={`research-donut research-capital-donut ${tone} ${ratio === null ? "unavailable" : ""}`} data-state={ratio === null ? "unavailable" : "ready"} style={{ "--donut-value": `${(ratio ?? 0) * 3.6}deg` } as CSSProperties}>
    <div><strong>{ratio === null ? "--" : `${ratio.toFixed(1)}%`}</strong><span>{label}</span></div>
  </div>;
}

function CompositionMap({ assets, liabilities, equity }: { assets: number; liabilities: number | null; equity: number | null }) {
  const capital = liabilities !== null && equity !== null ? liabilities + equity : null;
  const balanced = capital !== null && assets > 0 && Math.abs(capital - assets) / assets <= 0.05;
  const liabilityRatio = safeRatio(liabilities, capital);
  const equityRatio = safeRatio(equity, capital);
  if (capital === null || liabilityRatio === null || equityRatio === null || !balanced) {
    return <div className="research-composition-map research-composition-map--unavailable" aria-label="资产负债构成图">
      <div><span>资产负债构成</span><strong>构成待核验</strong></div>
      <small>{capital === null ? "负债与权益字段不完整" : `资产与负债权益不平衡（资产 ${amount(String(assets))} · 资本 ${amount(String(capital))}）`}</small>
    </div>;
  }
  return <div className="research-composition-map" aria-label="资产负债构成图">
    <div className="research-composition-assets"><span>资产总额</span><strong>{amount(String(assets))}</strong></div>
    <div className="research-composition-capital">
      <div className="liability" style={{ width: `${liabilityRatio}%` }}><span>负债合计</span><strong>{amount(String(liabilities))}</strong><small>{liabilityRatio.toFixed(1)}%</small></div>
      <div className="equity" style={{ width: `${equityRatio}%` }}><span>所有者权益</span><strong>{amount(String(equity))}</strong><small>{equityRatio.toFixed(1)}%</small></div>
    </div>
  </div>;
}

function TrendBars({ periods }: { periods: FinancialPeriod[] }) {
  const rows = periods.slice(-8);
  const capitalValues = rows.map((row) => numeric(row.total_assets)).filter((item): item is number => item !== null && item > 0);
  const revenueValues = rows.map((row) => numeric(row.revenue)).filter((item): item is number => item !== null);
  const maxCapital = Math.max(...capitalValues, 0);
  if (!rows.length || maxCapital <= 0) return <div className="research-visual-empty">多年资产负债序列暂不可用</div>;
  const minRevenue = Math.min(...revenueValues, 0);
  const maxRevenue = Math.max(...revenueValues, 0);
  const revenueRange = Math.max(maxRevenue - minRevenue, 1);
  const revenuePoints = rows.map((row, index) => {
    const revenue = numeric(row.revenue);
    if (revenue === null) return null;
    const x = rows.length === 1 ? 50 : index / (rows.length - 1) * 100;
    const y = 88 - (revenue - minRevenue) / revenueRange * 72;
    return `${x.toFixed(2)},${Math.max(10, Math.min(90, y)).toFixed(2)}`;
  });
  const lineSegments: string[][] = [];
  let gap = true;
  revenuePoints.forEach((point) => {
    if (point === null) { gap = true; return; }
    const current = lineSegments.at(-1);
    if (current && !gap) current.push(point);
    else lineSegments.push([point]);
    gap = false;
  });
  return <div className="research-trend-combo" aria-label="多年财务趋势图">
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{lineSegments.filter((segment) => segment.length > 1).map((segment, index) => <polyline points={segment.join(" ")} key={index} />)}</svg>
    {rows.map((row) => {
      const assets = numeric(row.total_assets);
      const liabilities = numeric(row.total_liabilities);
      const equity = numeric(row.total_equity);
      const capital = liabilities !== null && equity !== null ? liabilities + equity : null;
      const columnHeight = assets !== null && assets > 0 ? Math.max(6, assets / maxCapital * 100) : 0;
      const liabilityRatio = safeRatio(liabilities, capital);
      const equityRatio = safeRatio(equity, capital);
      const partial = assets === null || liabilities === null || equity === null || liabilityRatio === null || equityRatio === null;
      return <div className="research-trend-column" key={row.period}>
        <div className={`research-trend-stack ${partial ? "is-partial" : ""}`} title={`资产 ${amount(row.total_assets)} · 负债 ${amount(row.total_liabilities)} · 权益 ${amount(row.total_equity)} · 营收 ${amount(row.revenue)}`} style={{ "--capital-height": `${columnHeight}%` } as CSSProperties}>
          {liabilityRatio !== null && <span className="research-trend-segment liability" style={{ height: `${liabilityRatio}%` }} />}
          {equityRatio !== null && <span className="research-trend-segment equity" style={{ height: `${equityRatio}%` }} />}
        </div>
        <b title={partial ? "该报告期部分字段缺失" : undefined}>{row.period.slice(0, 4)}{partial ? "*" : ""}</b>
      </div>;
    })}
  </div>;
}

function ResearchVisualSummary({ value }: Props) {
  const latest = latestPeriod(value);
  const assets = numeric(latest?.total_assets);
  const liabilities = numeric(latest?.total_liabilities);
  const equity = numeric(latest?.total_equity);
  const capital = liabilities !== null && equity !== null ? liabilities + equity : null;
  const capitalReady = capital !== null && capital > 0;
  const dimensions = value.dimensions.slice(0, 9);
  const growth = numeric(value.financial_history.revenue_cagr_3y);
  const profitGrowth = numeric(value.financial_history.net_profit_cagr_3y);
  const pe = numeric(value.valuation.pe_ttm);
  const pb = numeric(value.valuation.pb);
  return <section className="research-visual-overview" aria-label="财务可视化总览">
    <header className="research-visual-header"><div><p className="eyebrow">TDX STYLE / EVIDENCE VISUALS</p><h2>财务可视化总览</h2></div><span>红色 = 上涨 / 改善 · 绿色 = 下跌 / 恶化 · 灰色 = 未接入</span></header>
    <div className="research-visual-grid">
      <article className="research-visual-card" aria-label="资产负债结构">
        <header><h3>资本结构</h3><small>{latest?.period ?? "报告期不可用"}</small></header>
        {latest && assets !== null ? <div className="research-visual-split">
          <div className="research-capital-donuts"><Donut label="负债率" value={liabilities} total={capital} tone="liability" /><Donut label="权益率" value={equity} total={capital} tone="equity" /></div>
          <div className="research-visual-table"><div><span>资产总额</span><b>{amount(latest.total_assets)}</b></div><div><span>负债合计</span><b>{amount(latest.total_liabilities)}</b></div><div><span>所有者权益</span><b>{amount(latest.total_equity)}</b></div><div><span>资产负债率</span><b>{percent(numeric(latest.debt_ratio))}</b></div>{!capitalReady && <div className="research-visual-table-warning"><span>结构状态</span><b>资本结构数据不足</b></div>}</div>
        </div> : <div className="research-visual-empty">资产负债表数据暂不可用</div>}
      </article>

      <article className="research-visual-card" aria-label="资产负债构成">
        <header><h3>资产负债构成</h3><small>真实报告期 · 面积映射</small></header>
        {latest && assets !== null ? <CompositionMap assets={assets} liabilities={liabilities} equity={equity} /> : <div className="research-visual-empty">资产负债表数据暂不可用</div>}
      </article>

      <article className="research-visual-card research-visual-card--wide" aria-label="多年财务趋势">
        <header><h3>多年财务趋势</h3><small>负债/权益堆叠柱 · 营收趋势线</small></header>
        <TrendBars periods={value.financial_history.annual_periods.length ? value.financial_history.annual_periods : value.financial_history.periods} />
        <div className="research-visual-legend"><span className="liability">负债</span><span className="equity">所有者权益</span><span className="revenue">营收趋势</span></div>
      </article>

      <article className="research-visual-card" aria-label="综合能力剖面">
        <header><h3>综合能力剖面</h3><small>九维研究矩阵</small></header>
        <div className="research-profile-bars">{dimensions.map((item) => {
          const current = score(item);
          return <div className={`research-profile-row ${item.status}`} data-state={current === null ? "unavailable" : "ready"} key={item.key}><span title={item.label}>{item.label}</span><i data-state={current === null ? "unavailable" : "ready"}><b style={{ width: `${current ?? 0}%` }} /></i><strong>{current === null ? "--" : current.toFixed(0)}</strong></div>;
        })}</div>
      </article>

      <article className="research-visual-card" aria-label="估值与增长">
        <header><h3>估值与增长</h3><small>当前快照 · 不替代价格区间</small></header>
        <div className="research-valuation-board"><div><span>PE(TTM)</span><strong>{pe === null ? "--" : pe.toFixed(2)}</strong></div><div><span>PB</span><strong>{pb === null ? "--" : pb.toFixed(2)}</strong></div><div><span>营收3年CAGR</span><strong className={growth !== null && growth >= 0 ? "positive" : "negative"}>{percent(growth)}</strong></div><div><span>净利润3年CAGR</span><strong className={profitGrowth !== null && profitGrowth >= 0 ? "positive" : "negative"}>{percent(profitGrowth)}</strong></div></div>
        <p className="financial-note">最新财务期：{latest?.period ?? "不可用"} · 所有数值保留原始来源口径。</p>
      </article>
      <div className="research-visual-card research-visual-card--wide" aria-label="估值双轴对照"><ValuationComparisonChart pe={pe} pb={pb} peerPe={numeric(value.valuation.peer_pe_median)} peerPb={numeric(value.valuation.peer_pb_median)} source={value.valuation.source} observedAt={value.valuation.observed_at} /></div>
    </div>
  </section>;
}

export { ResearchVisualSummary };
