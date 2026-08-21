import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock3, FileSearch, RefreshCw, X } from "lucide-react";
import { EvidenceLedger } from "../../shared/evidence/EvidenceLedger";

import type { CorrectionInput, EventImpactReport, NewsEvent, NewsIntelligenceBundle } from "./types";
import { friendlyError } from "../../shared/friendlyError";
import { NewsEventGraph } from "./NewsEventGraph";
import { NewsEventGrid } from "./NewsEventGrid";
import { EventImpactPanel } from "./EventImpactPanel";
import { useRealtimeState, useRealtimeSubscription } from "../../shared/realtime/RealtimeProvider";
import { RealtimeAIInsight, type RealtimeAIInsightPayload } from "../../shared/RealtimeAIInsight";

type Props = {
  selectedSymbol?: string | null;
  loadBundle: () => Promise<NewsIntelligenceBundle>;
  syncNews: (symbol?: string | null) => Promise<Record<string, number>>;
  syncHotspots?: () => Promise<Record<string, number>>;
  createCorrection: (input: CorrectionInput) => Promise<unknown>;
  loadEventImpact?: (eventId: string) => Promise<EventImpactReport>;
  openNewsCompliance?: () => void;
};
type Tab = "timeline" | "briefings" | "quality";
const phaseName = { premarket: "盘前", intraday: "盘中", postclose: "盘后" };

export function NewsIntelligenceView({ selectedSymbol, loadBundle, syncNews, syncHotspots, createCorrection, loadEventImpact, openNewsCompliance }: Props) {
  const [bundle, setBundle] = useState<NewsIntelligenceBundle | null>(null);
  const [tab, setTab] = useState<Tab>("timeline");
  const [selected, setSelected] = useState<NewsEvent | null>(null);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [hotspotLoading, setHotspotLoading] = useState(false);
  const [hotspotError, setHotspotError] = useState("");
  const [eventImpact, setEventImpact] = useState<EventImpactReport | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactError, setImpactError] = useState("");
  const newsStreamState = useRealtimeState();
  const [realtimeAIInsight, setRealtimeAIInsight] = useState<RealtimeAIInsightPayload | null>(null);
  const requestVersion = useRef(0);
  const impactRequestVersion = useRef(0);
  function filterSelectedBundle(loaded: NewsIntelligenceBundle, symbol: string | null | undefined) {
    if (!symbol) return loaded;
    return { ...loaded, events: loaded.events.filter((event) => event.affected_instruments.length === 0 || event.affected_instruments.some(([asset, code]) => asset === "a_share" && code === symbol)) };
  }
  async function runBundleRequest(work: () => Promise<NewsIntelligenceBundle>, failureMessage: string, mode: "loading" | "saving") {
    const request = ++requestVersion.current;
    const requestSymbol = selectedSymbol;
    if (mode === "loading") setLoading(true); else setSaving(true);
    setError("");
    try { const loaded = await work(); if (request === requestVersion.current) { setBundle(filterSelectedBundle(loaded, requestSymbol)); return true; } }
    catch (cause) { if (request === requestVersion.current) setError(friendlyError(cause, failureMessage)); }
    finally { if (request === requestVersion.current) { setLoading(false); setSaving(false); } }
    return false;
  }
  useEffect(() => {
    requestVersion.current += 1;
    impactRequestVersion.current += 1;
    setSelected(null); setReason(""); setBundle(null); setSaving(false); setHotspotLoading(false); setHotspotError(""); setEventImpact(null); setImpactError("");
    setRealtimeAIInsight(null);
    void runBundleRequest(loadBundle, "新闻数据", "loading");
    return () => { requestVersion.current += 1; };
  }, [loadBundle, selectedSymbol]);
  useRealtimeSubscription<{ snapshot_id?: string }>("news_events", (event) => {
        if (!event.payload?.snapshot_id) return;
        const request = ++requestVersion.current;
        const requestSymbol = selectedSymbol;
        void loadBundle().then((loaded) => {
          if (request === requestVersion.current) setBundle(filterSelectedBundle(loaded, requestSymbol));
        }).catch((cause) => {
          if (request === requestVersion.current) setError(friendlyError(cause, "新闻数据"));
        });
  });
  useRealtimeSubscription<RealtimeAIInsightPayload>("ai_analysis", (event) => {
        if (event.payload?.kind === "news_events") setRealtimeAIInsight(event.payload);
  });
  const interpretationByEvent = useMemo(() => new Map(bundle?.interpretations.map((item) => [item.event_id, item]) ?? []), [bundle]);
  async function collect() { await runBundleRequest(async () => { await syncNews(selectedSymbol ?? undefined); return loadBundle(); }, "新闻数据", "loading"); }
  async function collectHotspots() {
    if (!syncHotspots) return;
    const request = requestVersion.current;
    const requestSymbol = selectedSymbol;
    setHotspotLoading(true); setHotspotError("");
    try {
      await syncHotspots();
      const loaded = await loadBundle();
      if (request === requestVersion.current) setBundle(filterSelectedBundle(loaded, requestSymbol));
    } catch (cause) {
      if (request === requestVersion.current) setHotspotError(friendlyError(cause, "热点数据"));
    } finally {
      if (request === requestVersion.current) setHotspotLoading(false);
    }
  }
  async function saveCorrection() {
    if (!selected || !reason.trim()) return;
    const correction = { event_id: selected.event_id, reason: reason.trim(), review_state: "verified" as const, affected_instruments: selected.affected_instruments, industries: selected.industries, themes: selected.themes };
    if (await runBundleRequest(async () => { await createCorrection(correction); return loadBundle(); }, "新闻复核", "saving")) setReason("");
  }
  const selectedInterpretation = selected ? interpretationByEvent.get(selected.event_id) : undefined;
  function selectEvent(event: NewsEvent) {
    impactRequestVersion.current += 1;
    setSelected(event);
    setEventImpact(null);
    setImpactError("");
    setImpactLoading(false);
  }
  function closeEventDrawer() {
    impactRequestVersion.current += 1;
    setSelected(null);
    setEventImpact(null);
    setImpactError("");
    setImpactLoading(false);
  }
  async function loadImpact() {
    if (!selected || !loadEventImpact) return;
    const request = ++impactRequestVersion.current;
    const eventId = selected.event_id;
    setImpactLoading(true); setImpactError("");
    try {
      const report = await loadEventImpact(eventId);
      if (request === impactRequestVersion.current) setEventImpact(report);
    }
    catch (cause) {
      if (request === impactRequestVersion.current) setImpactError(friendlyError(cause, "事件影响复盘"));
    }
    finally {
      if (request === impactRequestVersion.current) setImpactLoading(false);
    }
  }
  const contrary = selected?.citations.filter((item) => selectedInterpretation?.contrary_citation_ids.includes(item.citation_id)) ?? [];
  const verifiedNewsCount = bundle?.events.filter((event) => event.review_state === "verified" && event.event_type !== "market_hotspot").length ?? 0;
  const verifiedHotspotCount = bundle?.events.filter((event) => event.review_state === "verified" && event.event_type === "market_hotspot").length ?? 0;
  const relatedStockCount = new Set(bundle?.events.flatMap((event) => event.affected_instruments.filter(([asset]) => asset === "a_share").map(([, code]) => code)) ?? []).size;
  const latestEventOccurred = bundle?.events.map((event) => event.occurred_at).sort().at(-1);
  const latestSourcePublished = bundle?.events.flatMap((event) => event.citations.map((citation) => citation.published_at)).sort().at(-1);
  const latestNormalized = bundle?.events.map((event) => event.normalized_at).sort().at(-1);
  const latestAnalysisGenerated = [...(bundle?.interpretations.map((item) => item.generated_at) ?? []), ...(bundle?.briefings.map((item) => item.generated_at) ?? [])].sort().at(-1);
  const realtimeStatusLabel = newsStreamState === "connected" ? "实时推送已连接" : newsStreamState === "error" ? "实时推送不可用 · 保留手动同步" : "正在连接实时推送";
  return <main className="terminal-page news-domain">
    <header className="news-header"><div><p className="eyebrow">新闻热点 / VERIFIED FEED</p><h1>每日情报流</h1><p>{selectedSymbol ? `当前标的 ${selectedSymbol}` : "全市场情报 · 尚未选择 A 股"}</p><span className={`news-realtime-status ${newsStreamState}`}><i aria-hidden="true" />{realtimeStatusLabel}</span></div><div className="news-sync-actions">{syncHotspots && <button className="news-sync secondary" onClick={() => void collectHotspots()} disabled={hotspotLoading}><RefreshCw size={15}/>{hotspotLoading ? "核验中" : "同步热点"}</button>}<button className="news-sync" onClick={() => void collect()} disabled={loading}><RefreshCw size={15}/>{loading ? "核验中" : "同步新闻"}</button></div></header>
    <div className="news-tabs" role="tablist"><button role="tab" aria-selected={tab === "timeline"} onClick={() => setTab("timeline")}>事件时间线</button><button role="tab" aria-selected={tab === "briefings"} onClick={() => setTab("briefings")}>每日简报</button><button role="tab" aria-selected={tab === "quality"} onClick={() => setTab("quality")}>数据状态</button></div>
    {error && <div className="news-error" role="alert"><AlertTriangle size={17}/><span>{error}</span>{error === "数据源尚未配置，请在数据设置中检查连接。" && openNewsCompliance && <button onClick={openNewsCompliance}>打开数据设置</button>}<button onClick={() => void collect()}>重试</button></div>}
    {hotspotError && <div className="news-error hotspot-error" role="alert"><AlertTriangle size={17}/><span>{hotspotError}</span>{hotspotError === "数据源尚未配置，请在数据设置中检查连接。" && openNewsCompliance && <button onClick={openNewsCompliance}>打开数据设置</button>}<button onClick={() => void collectHotspots()}>重试热点</button></div>}
    {realtimeAIInsight && <RealtimeAIInsight insight={realtimeAIInsight} domainLabel="新闻热点" />}
    {loading && !bundle && <div className="news-loading" role="status" aria-busy="true"><Clock3 size={18}/>正在读取冻结情报...</div>}
    {tab === "timeline" && bundle && (bundle.events.length === 0 ? <div className="news-empty"><FileSearch size={28}/><b>暂无已归档事件</b></div> : <><NewsEventGraph events={bundle.events} interpretations={bundle.interpretations} unifiedEvents={bundle.unifiedEvents} onSelect={selectEvent}/><NewsEventGrid events={bundle.events} interpretationByEvent={interpretationByEvent} onSelect={selectEvent}/></>)}
    {tab === "briefings" && bundle && <section className="briefing-ledger">{bundle.briefings.length === 0 ? <div className="news-empty"><FileSearch size={28}/><b>暂无冻结简报</b></div> : bundle.briefings.map((item) => <article key={item.report_id}><div><span>{phaseName[item.phase]}</span><time>{item.trading_date}</time></div><strong>{item.sections.watchlist.length} 个观察标的</strong><small>{item.event_ids.length} 个事件 · {item.interpretation_ids.length} 条解释</small></article>)}</section>}
    {tab === "quality" && bundle && <section className="quality-console"><div><span>已核验新闻数</span><strong>{verifiedNewsCount}</strong></div><div><span>已核验热点数</span><strong>{verifiedHotspotCount}</strong></div><div><span>关联当前股票数</span><strong>{relatedStockCount}</strong></div><div><span>最新事件发生</span><strong>{latestEventOccurred ? new Date(latestEventOccurred).toLocaleString("zh-CN", { hour12: false }) : "暂无"}</strong></div><div><span>最新来源发布时间</span><strong>{latestSourcePublished ? new Date(latestSourcePublished).toLocaleString("zh-CN", { hour12: false }) : "暂无"}</strong></div><div><span>最新标准化时间</span><strong>{latestNormalized ? new Date(latestNormalized).toLocaleString("zh-CN", { hour12: false }) : "暂无"}</strong></div><div><span>最新分析生成</span><strong>{latestAnalysisGenerated ? new Date(latestAnalysisGenerated).toLocaleString("zh-CN", { hour12: false }) : "暂无"}</strong></div></section>}
    {selected && <div className="evidence-backdrop" onClick={closeEventDrawer}><aside className="evidence-drawer" role="dialog" aria-label="事件证据" onClick={(event) => event.stopPropagation()}><header><div><p className="eyebrow">EVIDENCE CHAIN</p><h2>事件证据</h2></div><button aria-label="关闭证据" onClick={closeEventDrawer}><X size={18}/></button></header><section><h3>来源引用</h3>{selected.citations.map((citation) => <a href={citation.canonical_url} target="_blank" rel="noreferrer" key={citation.citation_id}><span>{citation.publisher} · {new Date(citation.published_at).toLocaleString("zh-CN")}</span><p>{citation.quoted_text}</p></a>)}</section>{contrary.length > 0 && <section className="contrary-evidence"><h3>相反证据</h3>{contrary.map((citation) => <p key={citation.citation_id}>{citation.quoted_text}</p>)}</section>}{(selected.evidence_ledger?.length ?? 0) > 0 && <EvidenceLedger entries={selected.evidence_ledger!} defaultOpen />} {loadEventImpact && <section className="event-impact-drawer"><button type="button" onClick={() => void loadImpact()} disabled={impactLoading}>{impactLoading ? "读取影响复盘..." : "查看影响复盘"}</button>{impactError && <p role="alert">{impactError}</p>}{eventImpact && <EventImpactPanel report={eventImpact} />}</section>}<section className="human-review"><h3>人工复核</h3><label>复核理由<textarea aria-label="复核理由" value={reason} onChange={(event) => setReason(event.target.value)}/></label><button disabled={saving || !reason.trim()} onClick={() => void saveCorrection()}><CheckCircle2 size={15}/>{saving ? "存档中" : "确认并存档"}</button></section></aside></div>}
  </main>;
}
