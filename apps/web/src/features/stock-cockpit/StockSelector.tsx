import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bookmark, BookmarkCheck, LoaderCircle, RefreshCw, Search, ShieldAlert } from "lucide-react";

import type {
  CandidateBoard,
  CandidateEntry,
  CandidateScoreBoard,
  CandidateScoreItem,
  CandidateScoreLoader,
} from "../a-shares/types";
import { isAShareSymbol, useSelectedInstrument } from "../instrument-selection/SelectedInstrumentProvider";
import type {
  CandidateSentimentBatch,
  CandidateSentimentLoader,
} from "../candidate-sentiment/types";
import type { AShareInstrument, InstrumentSearchResponse } from "./types";
import { friendlyError } from "../../shared/friendlyError";
import { DailyCacheHistory } from "../../shared/DailyCacheHistory";
import { createInstrumentDirectory } from "../../shared/instruments/instrumentDirectory";
import { readAShareWatchlist, writeAShareWatchlist } from "./watchlist";

type CandidateTab = "short_term" | "swing" | "watchlist";
const candidateTabs: ReadonlyArray<readonly [CandidateTab, string]> = [
  ["watchlist", "自选股"],
  ["short_term", "短线候选"],
  ["swing", "波段候选"],
];
const candidateTabOrder = candidateTabs.map(([key]) => key);
type Props = {
  loadCandidates: () => Promise<CandidateBoard>;
  loadWatchlistScores?: CandidateScoreLoader;
  prepare?: (symbol: string) => Promise<unknown>;
  search: (query: string) => Promise<InstrumentSearchResponse>;
  loadDirectory?: () => Promise<{ items: AShareInstrument[] }>;
  loadCandidateSentiments?: CandidateSentimentLoader;
  refreshCandidateSentiments?: CandidateSentimentLoader;
  onCandidateSentiments?: (batch: CandidateSentimentBatch | null) => void;
  pollIntervalMs?: number;
};

type CachedStockSnapshot = {
  symbol: string;
  instrument?: { name?: string | null };
};

function WatchButton({ symbol, watched, onToggle }: { symbol: string; watched: boolean; onToggle: () => void }) {
  return <button className="watch-button" type="button" aria-label={`${watched ? "将" : "将"} ${symbol} ${watched ? "移出自选" : "加入自选"}`} title={`${symbol} ${watched ? "移出自选" : "加入自选"}`} onClick={onToggle}>{watched ? <BookmarkCheck size={15} /> : <Bookmark size={15} />}</button>;
}

function CandidateRow({ entry, identity, selected, watched, onSelect, onWatch }: { entry: CandidateEntry; identity?: AShareInstrument; selected: boolean; watched: boolean; onSelect: () => void; onWatch: () => void }) {
  return <article className={selected ? "stock-option selected" : "stock-option"}>
    <button type="button" aria-pressed={selected} onClick={onSelect}>
      <span><b>{entry.symbol}</b><small>{identity?.name ?? "名称数据不可用"}</small></span>
      <span><strong>{Number(entry.score).toFixed(1)}</strong><small>候选分</small></span>
    </button>
    <WatchButton symbol={entry.symbol} watched={watched} onToggle={onWatch} />
  </article>;
}

const watchlistScoreLabels: Record<CandidateScoreItem["status"], string> = {
  ready: "自选分",
  insufficient_history: "待补60日日线",
  insufficient_liquidity: "流动性未达门槛",
  invalid_history: "日线校验未通过",
  stale_history: "日线未更新至确认日",
};

const candidateSourceNames: Record<string, string> = {
  baidu: "百度日线",
  mootdx: "通达信日线",
  "local-daily-bars": "本地日线",
};

function WatchlistRow({ symbol, item, score, error, selected, onSelect, onWatch, onRetry }: { symbol: string; item?: AShareInstrument; score?: CandidateScoreItem; error?: string; selected: boolean; onSelect: () => void; onWatch: () => void; onRetry: () => void }) {
  return <article className={selected ? "stock-option selected" : "stock-option"}>
    <button type="button" aria-pressed={selected} onClick={onSelect}><span><b>{symbol}</b><small>{item?.name ?? "身份数据暂不可用"}</small></span><span><strong>{score?.status === "ready" && score.score !== null ? Number(score.score).toFixed(1) : "--"}</strong><small>{score ? watchlistScoreLabels[score.status] : "评分待刷新"}</small></span></button>
    {error && <span className="visually-hidden" role="alert">{error}</span>}
    {error && <button className="identity-retry" type="button" aria-label={`重试 ${symbol} 身份`} onClick={onRetry}><RefreshCw size={14} /></button>}
    <WatchButton symbol={symbol} watched onToggle={onWatch} />
  </article>;
}

function shouldRefreshSentiment(
  board: CandidateBoard,
  batch: CandidateSentimentBatch,
): boolean {
  const symbols = new Set(batch.items.map((item) => item.symbol));
  return batch.quality === "unavailable"
    || board.short_term.slice(0, 20).some((item) => !symbols.has(item.symbol))
    || batch.items.some((item) => item.freshness === "stale");
}

function matchesSentimentBatch(
  board: CandidateBoard,
  batch: CandidateSentimentBatch,
): boolean {
  return batch.candidate_input_hash === board.input_snapshot_hash;
}

export function StockSelector({ loadCandidates, loadWatchlistScores, prepare, search, loadDirectory, loadCandidateSentiments, refreshCandidateSentiments, onCandidateSentiments, pollIntervalMs = 30_000 }: Props) {
  const selection = useSelectedInstrument();
  const [board, setBoard] = useState<CandidateBoard | null>(null);
  const [candidateState, setCandidateState] = useState<"loading" | "ready" | "error">("loading");
  const [tab, setTab] = useState<CandidateTab>("watchlist");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AShareInstrument[]>([]);
  const [directoryItems, setDirectoryItems] = useState<AShareInstrument[]>([]);
  const [searchState, setSearchState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [searchSourceStatus, setSearchSourceStatus] = useState<"ready" | "unavailable">("ready");
  const [searchError, setSearchError] = useState("");
  const [candidateError, setCandidateError] = useState("");
  const [watchlist, setWatchlist] = useState(readAShareWatchlist);
  const [identities, setIdentities] = useState<Record<string, AShareInstrument>>({});
  const [identityErrors, setIdentityErrors] = useState<Record<string, string>>({});
  const [watchlistScores, setWatchlistScores] = useState<CandidateScoreBoard | null>(null);
  const [watchlistScoreState, setWatchlistScoreState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [watchlistScoreError, setWatchlistScoreError] = useState("");
  const [sentimentBatch, setSentimentBatch] = useState<CandidateSentimentBatch | null>(null);
  const [sentimentError, setSentimentError] = useState("");
  const [sentimentRetryToken, setSentimentRetryToken] = useState(0);
  const searchRequest = useRef(0);
  const candidateRequest = useRef(0);
  const mounted = useRef(true);
  const initializedSelection = useRef(false);
  const identityRequests = useRef(new Set<string>());
  const identityGeneration = useRef<Record<string, number>>({});
  const watchlistScoreRequest = useRef(0);
  const watchlistScoresRef = useRef<CandidateScoreBoard | null>(null);
  const sentimentRequest = useRef(0);
  const sentimentBatchRef = useRef<CandidateSentimentBatch | null>(null);
  const loadedSentimentKey = useRef<string | null>(null);
  const refreshedSentimentKeys = useRef(new Set<string>());
  const sentimentCallbackRef = useRef(onCandidateSentiments);
  sentimentCallbackRef.current = onCandidateSentiments;
  const tabRefs = useRef<Record<CandidateTab, HTMLButtonElement | null>>({ short_term: null, swing: null, watchlist: null });
  const localDirectory = useMemo(() => createInstrumentDirectory(directoryItems), [directoryItems]);

  useEffect(() => {
    let active = true;
    if (loadDirectory) void loadDirectory().then((value) => { if (active) setDirectoryItems(value.items); }).catch(() => undefined);
    return () => { active = false; };
  }, [loadDirectory]);

  const refreshCandidates = useCallback(async (initial = false) => {
    const request = ++candidateRequest.current;
    if (initial) setCandidateState("loading");
    try { const value = await loadCandidates(); if (mounted.current && request === candidateRequest.current) { setBoard(value); setCandidateState("ready"); setCandidateError(""); } }
    catch (reason) { if (mounted.current && request === candidateRequest.current) { setCandidateError(friendlyError(reason, "候选池")); setCandidateState("error"); } }
  }, [loadCandidates]);

  useEffect(() => { mounted.current = true; void refreshCandidates(true); const timer = window.setInterval(() => void refreshCandidates(), pollIntervalMs); return () => { mounted.current = false; candidateRequest.current += 1; window.clearInterval(timer); }; }, [pollIntervalMs, refreshCandidates]);
  useEffect(() => {
    if (!board || initializedSelection.current) return;
    initializedSelection.current = true;
    // Candidate loading is asynchronous.  A user can select a row before the
    // board promise resolves; the URL is updated synchronously by the
    // selection provider, so consult it here instead of relying only on the
    // effect's stale `selection.symbol` closure.
    const urlSymbol = new URL(window.location.href).searchParams.get("symbol");
    if (!selection.symbol && !urlSymbol) {
      const first = board.short_term[0] ?? board.swing[0];
      if (first) selection.select(first.symbol, "candidate");
    }
  }, [board, selection]);

  const resolveSymbols = useCallback(async (symbols: string[]) => {
    const unique = [...new Set(symbols)].filter((symbol) => !identityRequests.current.has(symbol));
    if (!unique.length) return;
    unique.forEach((symbol) => identityRequests.current.add(symbol));
    const settled = await Promise.all(unique.map(async (symbol) => {
      const generation = (identityGeneration.current[symbol] ?? 0) + 1;
      identityGeneration.current[symbol] = generation;
      try { const response = await search(symbol); const item = response.items.find((candidate) => candidate.symbol === symbol); if (!item) throw new Error("身份目录未返回该 A 股"); return { symbol, generation, item }; }
      catch (reason) { return { symbol, generation, error: friendlyError(reason, "股票身份数据") }; }
    }));
    if (!mounted.current) return;
    const currentResults = settled.filter((result) => identityGeneration.current[result.symbol] === result.generation);
    setIdentities((current) => Object.fromEntries([...Object.entries(current), ...currentResults.flatMap((result) => result.item ? [[result.symbol, result.item] as const] : [])]));
    setIdentityErrors((current) => {
      const next = { ...current };
      currentResults.forEach((result) => { if (result.error) next[result.symbol] = result.error; else delete next[result.symbol]; });
      return next;
    });
  }, [search]);

  useEffect(() => { if (board) void resolveSymbols([...board.short_term, ...board.swing].map((item) => item.symbol)); }, [board, resolveSymbols]);
  useEffect(() => { void resolveSymbols(watchlist); }, [watchlist, resolveSymbols]);
  const refreshWatchlistScores = useCallback(async (hydrateMissing = false) => {
    if (!loadWatchlistScores || watchlist.length === 0) {
      watchlistScoresRef.current = null;
      setWatchlistScores(null); setWatchlistScoreState("idle"); setWatchlistScoreError("");
      return;
    }
    const request = ++watchlistScoreRequest.current;
    setWatchlistScoreState("loading"); setWatchlistScoreError("");
    try {
      if (hydrateMissing && prepare) {
        const current = new Map(watchlistScoresRef.current?.items.map((item) => [item.symbol, item]));
        const missing = watchlist.filter((symbol) => current.get(symbol)?.status !== "ready");
        for (const symbol of missing) await prepare(symbol);
      }
      const value = await loadWatchlistScores(watchlist, "short_term");
      if (mounted.current && request === watchlistScoreRequest.current) {
        watchlistScoresRef.current = value;
        setWatchlistScores(value); setWatchlistScoreState("ready"); setWatchlistScoreError("");
      }
    } catch (reason) {
      if (mounted.current && request === watchlistScoreRequest.current) {
        setWatchlistScoreState("error");
        setWatchlistScoreError(friendlyError(reason, "自选评分"));
      }
    }
  }, [loadWatchlistScores, prepare, watchlist]);

  useEffect(() => {
    if (!board) return;
    void refreshWatchlistScores();
  }, [board, board?.input_snapshot_hash, refreshWatchlistScores]);

  useEffect(() => {
    const snapshotId = board?.snapshot_id;
    const inputHash = board?.input_snapshot_hash;
    if (
      tab !== "short_term"
      || !board
      || !snapshotId
      || !inputHash
      || !loadCandidateSentiments
    ) {
      sentimentRequest.current += 1;
      setSentimentError("");
      sentimentCallbackRef.current?.(null);
      return;
    }

    const key = inputHash;
    const stored = sentimentBatchRef.current;
    if (
      loadedSentimentKey.current === key
      && stored
      && matchesSentimentBatch(board, stored)
    ) {
      setSentimentBatch(stored);
      setSentimentError("");
      sentimentCallbackRef.current?.(stored);
      return;
    }

    const request = ++sentimentRequest.current;
    let active = true;
    setSentimentBatch(null);
    sentimentBatchRef.current = null;
    setSentimentError("");
    sentimentCallbackRef.current?.(null);

    const publish = (value: CandidateSentimentBatch) => {
      if (!active || request !== sentimentRequest.current) return false;
      if (!matchesSentimentBatch(board, value)) {
        throw new Error("candidate sentiment snapshot mismatch");
      }
      loadedSentimentKey.current = key;
      sentimentBatchRef.current = value;
      setSentimentBatch(value);
      setSentimentError("");
      sentimentCallbackRef.current?.(value);
      return true;
    };

    void loadCandidateSentiments(snapshotId).then(async (current) => {
      if (!publish(current)) return;
      if (
        !refreshCandidateSentiments
        || !shouldRefreshSentiment(board, current)
        || refreshedSentimentKeys.current.has(key)
      ) return;
      refreshedSentimentKeys.current.add(key);
      try {
        const refreshed = await refreshCandidateSentiments(snapshotId);
        publish(refreshed);
      } catch (reason) {
        if (!active || request !== sentimentRequest.current) return;
        setSentimentError(friendlyError(reason, "短线候选情绪"));
      }
    }).catch((reason) => {
      if (!active || request !== sentimentRequest.current) return;
      setSentimentError(friendlyError(reason, "短线候选情绪"));
    });

    return () => {
      active = false;
      if (request === sentimentRequest.current) sentimentRequest.current += 1;
    };
  }, [
    board?.input_snapshot_hash,
    board?.snapshot_id,
    loadCandidateSentiments,
    refreshCandidateSentiments,
    sentimentRetryToken,
    tab,
  ]);

  const executeSearch = useCallback((value: string, request = ++searchRequest.current) => {
    setSearchState("loading"); setSearchError("");
    void search(value).then((response) => { if (request === searchRequest.current) { setResults(response.items); setSearchSourceStatus(response.source_status); setSearchState("ready"); } }).catch((reason) => { if (request === searchRequest.current) { setSearchError(friendlyError(reason, "股票搜索")); setSearchState("error"); } });
  }, [search]);

  useEffect(() => {
    const request = ++searchRequest.current;
    const normalized = query.trim();
    if (!normalized) { setResults([]); setSearchSourceStatus("ready"); setSearchState("idle"); return; }
    const localResults = localDirectory.search(normalized);
    if (localResults.length) {
      setResults(localResults); setSearchSourceStatus("ready"); setSearchState("ready");
      return;
    }
    setSearchState("loading"); setSearchError("");
    const timer = window.setTimeout(() => executeSearch(normalized, request), /^\d{6}$/.test(normalized) ? 0 : 250);
    return () => window.clearTimeout(timer);
  }, [executeSearch, localDirectory, query]);

  const candidateEntries = useMemo(() => board && tab !== "watchlist" ? board[tab] : [], [board, tab]);
  const watchlistScoreBySymbol = useMemo(() => new Map(watchlistScores?.items.map((item) => [item.symbol, item]) ?? []), [watchlistScores]);
  function toggleWatch(symbol: string) { if (!isAShareSymbol(symbol)) return; setWatchlist((current) => writeAShareWatchlist(current.includes(symbol) ? current.filter((item) => item !== symbol) : [...current, symbol])); }
  function retryIdentity(symbol: string) { identityRequests.current.delete(symbol); setIdentityErrors((current) => { const next = { ...current }; delete next[symbol]; return next; }); void resolveSymbols([symbol]); }
  function selectTab(next: CandidateTab) { setTab(next); window.setTimeout(() => tabRefs.current[next]?.focus(), 0); }
  function retrySentiment() {
    if (board?.snapshot_id && board.input_snapshot_hash) {
      const key = board.input_snapshot_hash;
      loadedSentimentKey.current = null;
      refreshedSentimentKeys.current.delete(key);
    }
    setSentimentRetryToken((value) => value + 1);
  }
  function onTabKey(event: React.KeyboardEvent<HTMLButtonElement>) { if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return; event.preventDefault(); const offset = event.key === "ArrowLeft" ? -1 : 1; selectTab(candidateTabOrder[(candidateTabOrder.indexOf(tab) + offset + candidateTabOrder.length) % candidateTabOrder.length]); }
  const provenance = tab === "watchlist" && watchlistScores ? watchlistScores : board;
  const provenanceSources = provenance?.sources?.map((source) => candidateSourceNames[source] ?? "已验证日线") ?? [];
  const provenanceUniverse = provenance?.universe_size ?? (board ? new Set([...board.short_term, ...board.swing].map((item) => item.symbol)).size : 0);
  const provenanceEligible = provenance?.eligible_size ?? provenanceUniverse;
  const provenanceDate = provenance?.latest_trade_date ?? null;

  const qualityNames = { ready: "行情可用", stale: "行情已陈旧", unavailable: "行情不可用" } as const;
  return <section className="stock-selector" aria-label="A 股选择器">
    <header><div><p className="eyebrow">股票选择</p><h2>选择观察股票</h2></div><span>{selection.symbol ?? "尚未选择 A 股"}</span><button type="button" className="selector-refresh" aria-label="刷新候选" onClick={() => { void refreshCandidates(); watchlist.forEach(retryIdentity); }}><RefreshCw size={14} /></button></header>
    <label className="stock-search"><Search size={16} /><span className="visually-hidden">搜索 A 股</span><input role="searchbox" aria-label="搜索 A 股" placeholder="输入六位代码或中文名称" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
    {searchState === "loading" && <p className="selector-message" role="status" aria-busy="true"><LoaderCircle size={15} />正在搜索...</p>}
    {query.trim() && searchState === "error" && <div className="selector-message error" role="alert"><ShieldAlert size={15} /><span>{searchError}</span><button type="button" onClick={() => executeSearch(query.trim())}>重试搜索</button></div>}
    {query.trim() && searchState === "ready" && <div className="stock-search-results" role="listbox" aria-label="A 股搜索结果">{results.length ? results.map((item) => <article key={item.symbol}><button role="option" aria-selected={selection.symbol === item.symbol} type="button" onClick={() => { selection.select(item.symbol, "search"); setQuery(""); }}><b>{item.symbol}</b><span>{item.name}</span><small>{item.exchange.toUpperCase()} · {qualityNames[item.quote_quality]}</small></button><WatchButton symbol={item.symbol} watched={watchlist.includes(item.symbol)} onToggle={() => toggleWatch(item.symbol)} /></article>) : searchSourceStatus === "unavailable" ? <div className="selector-message error" role="alert"><ShieldAlert size={15} /><span>行情验证源暂不可用，请稍后重试</span><button type="button" onClick={() => executeSearch(query.trim())}>重试搜索</button></div> : <p>没有找到已验证的 A 股</p>}</div>}
    <DailyCacheHistory<CachedStockSnapshot>
      scope="stock-cockpit"
      ariaLabel="今日已加载个股"
      activeSymbol={selection.symbol}
      getName={(value) => value.instrument?.name}
      onSelect={(item) => selection.select(item.symbol, "cache")}
    />
    <div className="selector-tabs" role="tablist" aria-label="A 股候选分类">{candidateTabs.map(([key, name]) => <button ref={(node) => { tabRefs.current[key] = node; }} id={`stock-selector-tab-${key === "short_term" ? "short" : key}`} key={key} role="tab" aria-controls="stock-selector-panel" aria-selected={tab === key} tabIndex={tab === key ? 0 : -1} type="button" onKeyDown={onTabKey} onClick={() => selectTab(key)}>{name}</button>)}</div>
    {provenance && <div className="candidate-provenance" role="status" aria-label="候选数据说明"><span>{provenanceSources.join(" / ") || "本地日线"}</span><span>可比较 {provenanceEligible} / {provenanceUniverse} 只</span><span>数据至 {provenanceDate ?? "待补齐"}</span><span>收盘后更新</span>{tab === "watchlist" && watchlist.length > 0 && <button type="button" aria-label="刷新自选评分" onClick={() => void refreshWatchlistScores(true)} disabled={watchlistScoreState === "loading"}><RefreshCw size={13} className={watchlistScoreState === "loading" ? "spin" : ""} /></button>}</div>}
    <div id="stock-selector-panel" role="tabpanel" aria-labelledby={`stock-selector-tab-${tab === "short_term" ? "short" : tab}`} className="stock-options">
      {candidateState === "loading" && <p className="selector-message" role="status" aria-busy="true"><LoaderCircle size={15} />正在读取候选池...</p>}
      {candidateState === "error" && <div className="selector-message error" role="alert"><ShieldAlert size={15} /><span>{candidateError}</span><button type="button" onClick={() => void refreshCandidates()}>重试候选</button></div>}
      {tab === "short_term" && sentimentError && <div className="selector-message candidate-sentiment-error error" role="alert"><ShieldAlert size={15} /><span>{sentimentError}{sentimentBatch ? " 当前保留最近已验证结果。" : ""}</span><button type="button" onClick={retrySentiment}><RefreshCw size={14} />重试情绪</button></div>}
      {tab === "watchlist" && watchlistScoreState === "error" && <div className="selector-message error" role="alert"><ShieldAlert size={15} /><span>{watchlistScoreError}</span><button type="button" onClick={() => void refreshWatchlistScores()}>重试评分</button></div>}
      {candidateState === "ready" && tab !== "watchlist" && candidateEntries.length === 0 && <div className="selector-empty"><b>{board?.universe_status === "empty" ? "本地候选池为空" : "当前分类暂无候选"}</b><p>{board?.universe_status === "empty" ? "同步足够历史数据后才会生成候选，不会自动猜测股票。" : "可通过代码或名称搜索选择 A 股。"}</p></div>}
      {tab === "watchlist" && watchlist.length === 0 && <div className="selector-empty"><b>暂无自选股</b><p>可从候选或搜索结果加入自选。</p></div>}
      {candidateEntries.map((entry) => <CandidateRow key={`${entry.horizon}-${entry.symbol}`} entry={entry} identity={identities[entry.symbol]} selected={selection.symbol === entry.symbol} watched={watchlist.includes(entry.symbol)} onSelect={() => selection.select(entry.symbol, "candidate")} onWatch={() => toggleWatch(entry.symbol)} />)}
      {tab === "watchlist" && watchlist.map((symbol) => <WatchlistRow key={symbol} symbol={symbol} item={identities[symbol]} score={watchlistScoreBySymbol.get(symbol)} error={identityErrors[symbol]} selected={selection.symbol === symbol} onSelect={() => selection.select(symbol, "watchlist")} onWatch={() => toggleWatch(symbol)} onRetry={() => retryIdentity(symbol)} />)}
    </div>
  </section>;
}
