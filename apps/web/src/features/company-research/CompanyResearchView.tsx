import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Building2, Clock3, ExternalLink, LoaderCircle, Search, ShieldAlert, X } from "lucide-react";

import { DailyCacheHistory } from "../../shared/DailyCacheHistory";
import { DailyRefreshStatus } from "../../shared/DailyRefreshStatus";
import { readDailySnapshot, writeDailySnapshot } from "../../shared/dailySnapshotCache";
import type { LoadProgress, LoadProgressCallback } from "../../shared/fetchJsonWithProgress";
import type { InstrumentSearchResponse } from "../stock-cockpit/types";
import type { CompanyResearchResponse, FinancialPeriod } from "./types";
import "./companyResearch.css";

type Props = {
  load: (symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback) => Promise<CompanyResearchResponse>;
  search: (query: string) => Promise<InstrumentSearchResponse>;
  selectedSymbol?: string | null;
  onOpenAShare?: (symbol: string) => void;
};

type ResearchEntry = {
  symbol: string;
  name: string;
  state: "loading" | "ready" | "error";
  value?: CompanyResearchResponse;
  error?: string;
  cachedAt?: string;
  updatedAt?: string;
  refreshing: boolean;
  progress?: LoadProgress | null;
  refreshError?: string;
};

const metricLabels: Record<string, string> = {
  revenue_cagr_3y: "营收3年CAGR", net_profit_cagr_3y: "净利润3年CAGR",
  latest_revenue_yoy: "最新营收同比", latest_net_profit_yoy: "最新净利润同比",
  roe: "ROE", gross_margin: "毛利率", cash_to_profit: "现金流/净利润",
  operating_cash_flow: "经营现金流", debt_ratio: "资产负债率", pe_ttm: "PE(TTM)", pb: "PB",
};

function numeric(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function pct(value: string | null | undefined, scale = 1): string {
  const parsed = numeric(value);
  return parsed === null ? "--" : `${(parsed * scale).toFixed(1)}%`;
}

function compactAmount(value: string | null | undefined): string {
  const parsed = numeric(value);
  if (parsed === null) return "--";
  if (Math.abs(parsed) >= 100_000_000) return `${(parsed / 100_000_000).toFixed(2)}亿`;
  if (Math.abs(parsed) >= 10_000) return `${(parsed / 10_000).toFixed(1)}万`;
  return parsed.toFixed(2);
}

function displayMetric(key: string, value: string | null): string {
  if (value === null) return "--";
  if (["revenue_cagr_3y", "net_profit_cagr_3y", "latest_revenue_yoy", "latest_net_profit_yoy", "gross_margin", "debt_ratio"].includes(key)) return pct(value, 100);
  if (key === "roe") return pct(value);
  if (key === "operating_cash_flow") return compactAmount(value);
  return numeric(value)?.toFixed(2) ?? value;
}

function ScoreGauge({ label, value, suffix = "", tone = "normal" }: { label: string; value: number | null; suffix?: string; tone?: "normal" | "risk" }) {
  const display = value === null ? "--" : value.toFixed(1);
  const width = value === null ? 0 : Math.max(0, Math.min(100, value));
  return <article className={`research-gauge ${tone}`}>
    <span className="research-gauge-label">{label}</span>
    <div className="research-gauge-value">{display}<small>{suffix}</small></div>
    <div className="research-meter" aria-label={`${label} ${display}`}><span style={{ width: `${width}%` }} /></div>
  </article>;
}

function FinancialTable({ periods }: { periods: FinancialPeriod[] }) {
  const rows = periods.slice(-5).reverse();
  if (!rows.length) return <p className="financial-note">多年财务序列暂不可用，不以估算值填补。</p>;
  return <div>
    <table className="financial-table">
      <thead><tr><th>报告期</th><th>营收</th><th>净利润</th><th>经营现金流</th><th>毛利率</th><th>负债率</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.period}>
        <td>{row.period}</td><td>{compactAmount(row.revenue)}</td><td>{compactAmount(row.net_profit)}</td>
        <td>{compactAmount(row.operating_cash_flow)}</td><td>{pct(row.gross_margin, 100)}</td><td>{pct(row.debt_ratio, 100)}</td>
      </tr>)}</tbody>
    </table>
  </div>;
}

function dimensionMetric(value: CompanyResearchResponse, dimensionKey: string, metricKey: string): string | null {
  return value.dimensions.find((item) => item.key === dimensionKey)?.metrics[metricKey] ?? null;
}

function PeerComparison({ peers }: { peers: CompanyResearchResponse[] }) {
  if (peers.length < 2) return null;
  return <section className="research-card research-comparison" aria-label="同行横向比较">
    <div className="research-card-header"><h2>同行横向比较</h2><span className="research-status partial">同口径原值 · 不做主观排名</span></div>
    <div className="research-comparison-scroll"><table className="financial-table">
      <thead><tr><th>公司</th><th>研究分</th><th>覆盖度</th><th>PE</th><th>PB</th><th>营收3年CAGR</th><th>净利润3年CAGR</th><th>ROE</th><th>风险扣分</th></tr></thead>
      <tbody>{peers.map((peer) => <tr key={peer.symbol}>
        <td>{peer.name}<br />{peer.symbol}</td><td>{numeric(peer.final_score)?.toFixed(1) ?? "--"}</td>
        <td>{pct(peer.evidence_coverage, 100)}</td><td>{numeric(peer.valuation.pe_ttm)?.toFixed(2) ?? "--"}</td>
        <td>{numeric(peer.valuation.pb)?.toFixed(2) ?? "--"}</td><td>{pct(peer.financial_history.revenue_cagr_3y, 100)}</td>
        <td>{pct(peer.financial_history.net_profit_cagr_3y, 100)}</td><td>{pct(dimensionMetric(peer, "profitability", "roe"))}</td>
        <td>{numeric(peer.risk_penalty)?.toFixed(1) ?? "--"}</td>
      </tr>)}</tbody>
    </table></div>
  </section>;
}

function ResearchDashboard({ value, peers, onOpenAShare }: { value: CompanyResearchResponse; peers: CompanyResearchResponse[]; onOpenAShare?: (symbol: string) => void }) {
  const score = numeric(value.final_score);
  const coverage = numeric(value.evidence_coverage);
  const risk = numeric(value.risk_penalty);
  const triggered = value.counter_case.filter((item) => item.status === "triggered").length;
  return <div className="research-dashboard">
    <section className="research-card research-card-header" aria-label="公司研究摘要">
      <div><p className="eyebrow">{value.symbol} / {value.as_of} / 研究账本</p><h2>{value.name}</h2></div>
      <div className={`research-context-strip quality-${value.status}`}>
        {onOpenAShare && <button className="company-research-jump company-research-jump--reverse" type="button" aria-label="打开个股观察" onClick={() => onOpenAShare(value.symbol)}><ExternalLink size={16} /><span>打开个股观察</span><small>同一只股票 · 一键切换</small></button>}
        <div><Clock3 size={15} /><span>研究时间</span><b>{new Date(value.generated_at).toLocaleString("zh-CN", { hour12: false })}</b></div>
        <div><span>证据质量</span><b>{value.status === "ready" ? "证据完整" : value.status === "partial" ? "部分证据" : "证据不可用"}</b><small>覆盖 {pct(value.evidence_coverage, 100)}</small></div>
      </div>
    </section>
    <section className="research-gauges" aria-label="公司研究核心仪表">
      <ScoreGauge label="研究分" value={score} suffix="/100" />
      <ScoreGauge label="证据覆盖度" value={coverage === null ? null : coverage * 100} suffix="%" />
      <ScoreGauge label="风险压力" value={risk === null ? null : risk * 4} suffix={risk === null ? "" : ` · 扣${risk.toFixed(1)}分`} tone="risk" />
    </section>
    <PeerComparison peers={peers} />
    <div className="research-grid">
      <section className="research-card" aria-label="九维公司研究矩阵">
        <div className="research-card-header"><h2>九维研究矩阵</h2><span className="research-status partial">只对可核验数值评分</span></div>
        <div className="dimension-list">{value.dimensions.map((item) => <article className="dimension-row" key={item.key}>
          <div className="dimension-name">{item.label}<small> · {item.weight}%</small></div>
          <div><div className="research-meter"><span style={{ width: `${numeric(item.score) ?? 0}%` }} /></div>
            <div className="dimension-summary">{item.summary}{item.reason ? ` · 未评分：${item.reason}` : ""}</div>
            {Object.entries(item.metrics).length > 0 && <div className="dimension-summary">{Object.entries(item.metrics).map(([key, metric]) => `${metricLabels[key] ?? key} ${displayMetric(key, metric)}`).join(" · ")}</div>}
          </div>
          <div className={`dimension-score ${item.status}`}>{item.score === null ? "未评分" : Number(item.score).toFixed(1)}</div>
        </article>)}</div>
      </section>
      <section className="research-card" aria-label="估值观察">
        <div className="research-card-header"><h2>估值观察</h2><span className={`research-status ${value.valuation.status}`}>{value.valuation.status}</span></div>
        <div className="valuation-grid">
          <div className="valuation-item"><span>PE(TTM)</span><strong>{numeric(value.valuation.pe_ttm)?.toFixed(2) ?? "--"}</strong></div>
          <div className="valuation-item"><span>PB</span><strong>{numeric(value.valuation.pb)?.toFixed(2) ?? "--"}</strong></div>
          <div className="valuation-item"><span>总市值</span><strong>{value.valuation.market_cap_yi ? `${Number(value.valuation.market_cap_yi).toFixed(1)}亿` : "--"}</strong></div>
        </div>
        <p className="financial-note">同行中位数：PE {numeric(value.valuation.peer_pe_median)?.toFixed(2) ?? "待建立同行样本"} · PB {numeric(value.valuation.peer_pb_median)?.toFixed(2) ?? "待建立同行样本"}</p>
        <p className="financial-note">{value.valuation.observation_range_reason}</p>
      </section>
      <section className="research-card" aria-label="多年财务趋势">
        <div className="research-card-header"><h2>多年财务趋势</h2><span className={`research-status ${value.financial_history.status}`}>{value.financial_history.source}</span></div>
        <FinancialTable periods={value.financial_history.annual_periods} />
        <p className="financial-note">营收3年CAGR {pct(value.financial_history.revenue_cagr_3y, 100)} · 净利润3年CAGR {pct(value.financial_history.net_profit_cagr_3y, 100)}</p>
      </section>
      <section className="research-card" aria-label="反方审查">
        <div className="research-card-header"><h2>十项反方审查</h2><span className={`research-status ${triggered ? "triggered" : "clear"}`}>{triggered ? `${triggered}项触发` : "未见触发"}</span></div>
        <div className="counter-list">{value.counter_case.map((item) => <article className={`counter-item ${item.status}`} key={item.key}>
          <header><span>{item.title}</span><span>{item.status === "clear" ? "通过" : item.status === "triggered" ? `扣${item.penalty}` : "待核验"}</span></header>
          <p>{item.detail}{item.threshold ? ` · 规则：${item.threshold}` : ""}</p>
        </article>)}</div>
      </section>
      <section className="research-card" aria-label="F10原文证据">
        <div className="research-card-header"><h2>F10 原文证据</h2><span className={`research-status ${value.profile.status}`}>{value.profile.source}</span></div>
        <div className="profile-copy">
          <section><h3>公司概况</h3><p>{value.profile.company_overview ?? "原文暂不可用"}</p></section>
          <section><h3>行业分析</h3><p>{value.profile.industry_analysis ?? "原文暂不可用"}</p></section>
          <section><h3>最新提示</h3><p>{value.profile.latest_tips ?? "原文暂不可用"}</p></section>
        </div>
      </section>
      <section className="research-card" aria-label="研究来源账本">
        <div className="research-card-header"><h2>来源账本</h2><span className="research-status partial">生成 {new Date(value.generated_at).toLocaleString("zh-CN")}</span></div>
        <div className="source-list">{value.sources.map((source) => <article className="source-item" key={`${source.source}-${source.label}`}>
          <div><strong>{source.label}</strong><div>{source.detail}</div></div>
          <span>{source.status}<br />{source.observed_at ? new Date(source.observed_at).toLocaleString("zh-CN") : "无时间戳"}</span>
        </article>)}</div>
        {value.reasons.length > 0 && <p className="financial-note">限制：{value.reasons.join("；")}</p>}
      </section>
    </div>
  </div>;
}

export function CompanyResearchView({ load, search, selectedSymbol, onOpenAShare }: Props) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<InstrumentSearchResponse["items"]>([]);
  const [entries, setEntries] = useState<ResearchEntry[]>([]);
  const [activeSymbol, setActiveSymbol] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const controllers = useRef(new Map<string, AbortController>());
  const initialized = useRef(false);

  async function addCompany(symbol: string, name = symbol) {
    const normalized = symbol.trim();
    if (!/^\d{6}$/.test(normalized)) return;
    const existing = entries.some((item) => item.symbol === normalized);
    if (!existing && entries.length >= 4) return;
    const cached = readDailySnapshot<CompanyResearchResponse>("company-research", normalized);
    setSuggestions([]); setQuery(""); setActiveSymbol(normalized);
    setEntries((current) => {
      const existing = current.find((item) => item.symbol === normalized);
      if (existing) return current;
      if (current.length >= 4) return current;
      return [...current, cached
        ? { symbol: normalized, name: cached.value.name, state: "ready", value: cached.value, cachedAt: cached.cachedAt, refreshing: true, progress: null }
        : { symbol: normalized, name, state: "loading", refreshing: true, progress: null }];
    });
    if (existing) return;
    const controller = new AbortController();
    controllers.current.set(normalized, controller);
    try {
      const value = await load(normalized, undefined, controller.signal, (progress) => {
        if (controllers.current.get(normalized) !== controller || controller.signal.aborted) return;
        setEntries((current) => current.map((item) => item.symbol === normalized ? { ...item, refreshing: true, progress, refreshError: undefined } : item));
      });
      if (controllers.current.get(normalized) !== controller) return;
      const stored = writeDailySnapshot("company-research", normalized, value);
      setEntries((current) => current.map((item) => item.symbol === normalized ? {
        symbol: normalized,
        name: value.name,
        state: "ready",
        value,
        cachedAt: stored.cachedAt,
        updatedAt: stored.cachedAt,
        refreshing: false,
        progress: { percent: 100, stage: "complete", detail: "最新公司研究数据已载入" },
      } : item));
    } catch (error) {
      if (controller.signal.aborted) return;
      const message = error instanceof Error ? error.message : "公司研究数据不可用";
      setEntries((current) => current.map((item) => item.symbol === normalized
        ? item.value
          ? { ...item, state: "ready", refreshing: false, refreshError: message }
          : { ...item, state: "error", refreshing: false, error: message, refreshError: message }
        : item));
    } finally { if (controllers.current.get(normalized) === controller) controllers.current.delete(normalized); }
  }

  useEffect(() => {
    if (initialized.current || !selectedSymbol || !/^\d{6}$/.test(selectedSymbol)) return;
    initialized.current = true;
    void addCompany(selectedSymbol);
  }, [selectedSymbol]);

  useEffect(() => () => { controllers.current.forEach((controller) => controller.abort()); }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    setSearching(true);
    try {
      const result = await search(trimmed);
      setSuggestions(result.items.slice(0, 8));
      if (result.items.length === 1) void addCompany(result.items[0].symbol, result.items[0].name);
    } finally { setSearching(false); }
  }

  function remove(symbol: string) {
    controllers.current.get(symbol)?.abort(); controllers.current.delete(symbol);
    setEntries((current) => current.filter((item) => item.symbol !== symbol));
    setActiveSymbol((current) => current === symbol ? entries.find((item) => item.symbol !== symbol)?.symbol ?? null : current);
  }

  const active = useMemo(() => entries.find((item) => item.symbol === activeSymbol) ?? entries[0] ?? null, [activeSymbol, entries]);
  return <main className="terminal-page company-research-page">
    <header className="research-hero">
      <div><p className="eyebrow">2–3 YEAR / EVIDENCE-BASED RESEARCH</p><h1>公司研究</h1><p className="financial-note">把财报、F10、估值与反方证据压缩成可核验研究账本；结论由用户独立判断。</p></div>
      <form className="research-search" onSubmit={submit}>
        <Search size={18} aria-hidden="true" /><label className="visually-hidden" htmlFor="company-research-query">股票代码或名称</label>
        <input id="company-research-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="代码或名称，最多比较4只" />
        <button type="submit" disabled={searching}>{searching ? <LoaderCircle size={16} /> : "查询"}</button>
        {suggestions.length > 0 && <div className="research-suggestions">{suggestions.map((item) => <button type="button" key={item.symbol} onClick={() => void addCompany(item.symbol, item.name)}><span>{item.name}</span><b>{item.symbol}</b></button>)}</div>}
      </form>
    </header>
    <DailyCacheHistory<CompanyResearchResponse>
      scope="company-research"
      ariaLabel="今日已加载研究"
      activeSymbol={active?.symbol}
      getName={(value) => value.name}
      onSelect={(item) => void addCompany(item.symbol, item.value.name)}
    />
    {entries.length > 0 && <div className="research-compare" aria-label="同行比较池">{entries.map((entry) => <span className={`research-chip ${active?.symbol === entry.symbol ? "active" : ""}`} key={entry.symbol} role="button" tabIndex={0} onClick={() => setActiveSymbol(entry.symbol)} onKeyDown={(event) => { if (event.key === "Enter") setActiveSymbol(entry.symbol); }}>
      <Building2 size={14} /><span>{entry.name} {entry.symbol}</span><button className="research-chip-remove" type="button" aria-label={`移除 ${entry.symbol}`} onClick={(event) => { event.stopPropagation(); remove(entry.symbol); }}><X size={13} /></button>
    </span>)}</div>}
    {!active && <section className="research-empty"><Building2 size={24} /><h2>建立公司研究池</h2><p>输入股票代码或名称，系统将读取真实多年财报、当前估值、通达信 F10 与反方风险证据。</p></section>}
    {active && <DailyRefreshStatus label="公司研究" cachedAt={active.cachedAt} loading={active.refreshing} progress={active.progress} error={active.refreshError ?? active.error} updatedAt={active.updatedAt} />}
    {active?.state === "loading" && <section className="research-empty" aria-busy="true"><LoaderCircle size={24} /><h2>正在建立 {active.symbol} 研究账本</h2><p>财务、估值与 F10 分源加载中；缺失项不会用推测值填补。</p></section>}
    {active?.state === "error" && <section className="research-error" role="alert"><ShieldAlert size={22} /><h2>{active.symbol} 研究数据不可用</h2><p>{active.error}</p></section>}
    {active?.state === "ready" && active.value && <ResearchDashboard value={active.value} peers={entries.flatMap((entry) => entry.value ? [entry.value] : [])} onOpenAShare={onOpenAShare} />}
  </main>;
}
