import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SelectedInstrumentProvider } from "../instrument-selection/SelectedInstrumentProvider";
import type { CandidateBoard } from "../a-shares/types";
import type { MarketSentimentResponse } from "../market-sentiment/types";
import type {
  CandidateSentimentBatch,
  CandidateSentimentSnapshot,
} from "../candidate-sentiment/types";
import { StockSelector } from "./StockSelector";
import type { InstrumentSearchResponse } from "./types";
import { writeDailySnapshot } from "../../shared/dailySnapshotCache";

const factor = {
  symbol: "600000", as_of: "2026-07-15", latest_trade_date: "2026-07-14",
  close: "10.25", return_5d: "0.0149",
  return_20d: "0.04", distance_ma20: "0.02", volume_ratio_5_20: "1.25",
  volatility_20d: "0.18", drawdown_60d: "-0.06", liquidity_amount_20d: "800000000",
  factor_version: "a-share-factors-v1", source: "local-daily-bars",
};
const first: CandidateBoard = {
  asset: "a_share", snapshot_id: "candidate-1", input_snapshot_hash: "a".repeat(64),
  universe_status: "ready", as_of: "2026-07-15", factor_version: "a-share-factors-v1",
  universe_size: 128, eligible_size: 96, latest_trade_date: "2026-07-14",
  sources: ["baidu"], refresh_policy: "after_close",
  short_term: [{ symbol: "600000", horizon: "short_term", score: "68.5", score_breakdown: { momentum: "24.5", volume: "18" }, factor_snapshot: factor }],
  swing: [{ symbol: "000001", horizon: "swing", score: "61", score_breakdown: { trend: "22" }, factor_snapshot: { ...factor, symbol: "000001" } }], exclusions: [],
};
const empty: CandidateBoard = { ...first, universe_status: "empty", snapshot_id: null, short_term: [], swing: [] };
const searchResult: InstrumentSearchResponse = {
  query: "平安", source_status: "ready", server_time: "2026-07-15T09:30:00+08:00",
  items: [{ symbol: "000001", name: "平安银行", exchange: "sz", observed_at: "2026-07-15T09:29:00+08:00", quote_quality: "ready" }],
};
const puFaResult: InstrumentSearchResponse = {
  ...searchResult, query: "600000",
  items: [{ ...searchResult.items[0], symbol: "600000", name: "浦发银行", exchange: "sh" }],
};
const watchlistScores = {
  as_of: "2026-07-15", horizon: "short_term" as const, factor_version: "a-share-factors-v1",
  universe_size: 128, eligible_size: 96, latest_trade_date: "2026-07-14", sources: ["baidu"],
  items: [{ symbol: "600000", status: "ready" as const, score: "42", latest_trade_date: "2026-07-14", reason: null }],
};
const marketSentiment: MarketSentimentResponse = {
  trading_date: "2026-07-17", phase: "postclose", display_mode: "current",
  current: {
    snapshot_id: "sentiment-watchlist", previous_snapshot_id: null, trading_date: "2026-07-17",
    phase: "postclose", quality: "ready", freshness: "current", score: "64", band: "active",
    coverage_percent: "88", components: [], drivers: [], risks: [], beginner_guidance: "顺势观察，但不要追高。",
    observed_at: "2026-07-17T15:00:00+08:00", generated_at: "2026-07-17T15:00:05+08:00",
    source_snapshot_ids: ["source-1"], formula_version: "a-share-sentiment-v1",
  },
  previous_close: null, trajectory: [],
};

function candidateSentiment(
  symbol = "600000",
  overrides: Partial<CandidateSentimentSnapshot> = {},
): CandidateSentimentSnapshot {
  return {
    snapshot_id: `sentiment-${symbol}`,
    candidate_snapshot_id: "candidate-1",
    candidate_input_hash: "a".repeat(64),
    symbol,
    quality: "ready",
    freshness: "current",
    score: "72",
    band: "positive",
    coverage_percent: "100",
    components: [
      { name: "news", status: "ready", score: "75", weight: "40", summary: "新闻偏积极", observed_at: "2026-07-15T10:00:00+08:00", evidence_ids: ["news-1"] },
      { name: "hotspot", status: "ready", score: "65", weight: "30", summary: "热点可用", observed_at: "2026-07-15T10:00:00+08:00", evidence_ids: ["hotspot-1"] },
      { name: "fund_flow", status: "ready", score: "75", weight: "30", summary: "资金偏流入", observed_at: "2026-07-15T10:00:00+08:00", evidence_ids: ["fund-1"] },
    ],
    primary_reason: "新闻与资金方向相互印证。",
    primary_risk: "情绪可能快速变化。",
    beginner_guidance: "继续观察风险条件。",
    observed_at: "2026-07-15T10:00:00+08:00",
    generated_at: "2026-07-15T10:00:05+08:00",
    source_snapshot_ids: ["news-1", "hotspot-1", "fund-1"],
    formula_version: "candidate-sentiment-v1",
    ...overrides,
  };
}

function candidateSentimentBatch(
  candidate = first,
  items: CandidateSentimentSnapshot[] = [candidateSentiment()],
): CandidateSentimentBatch {
  return {
    snapshot_id: `batch-${candidate.snapshot_id}`,
    candidate_snapshot_id: candidate.snapshot_id!,
    candidate_input_hash: candidate.input_snapshot_hash!,
    as_of: candidate.as_of,
    cutoff: "2026-07-15T10:00:05+08:00",
    quality: items.length && items.every((item) => item.quality === "ready") ? "ready" : items.some((item) => item.score !== null) ? "partial" : "unavailable",
    items: items.map((item) => ({
      ...item,
      candidate_snapshot_id: candidate.snapshot_id!,
      candidate_input_hash: candidate.input_snapshot_hash!,
    })),
    generated_at: "2026-07-15T10:00:05+08:00",
  };
}

function renderSelector(props: Partial<React.ComponentProps<typeof StockSelector>> = {}) {
  return render(<SelectedInstrumentProvider><StockSelector
    loadCandidates={() => Promise.resolve(first)} search={(query) => Promise.resolve(query === "600000" ? puFaResult : searchResult)} {...props}
  /></SelectedInstrumentProvider>);
}

function openShortTermCandidates() {
  const tab = screen.getByRole("tab", { name: "短线候选" });
  fireEvent.click(tab);
  return tab;
}

describe("StockSelector", () => {
  beforeEach(() => { window.history.replaceState({}, "", "/"); localStorage.clear(); vi.useRealTimers(); });

  it("shows the watchlist first and selects it by default", async () => {
    renderSelector();

    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((item) => item.textContent)).toEqual(["自选股", "短线候选", "波段候选"]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveAttribute("aria-labelledby", "stock-selector-tab-watchlist");
    expect(screen.getByText("暂无自选股")).toBeInTheDocument();
  });

  it("shows today's loaded stocks and opens a cached stock again", async () => {
    writeDailySnapshot("stock-cockpit", "600519", {
      symbol: "600519",
      instrument: { name: "贵州茅台" },
    }, new Date());

    renderSelector();

    const history = screen.getByRole("region", { name: "今日已加载个股" });
    const cached = screen.getByRole("button", { name: /贵州茅台.*600519/ });
    expect(history).toHaveTextContent("今日已加载");
    fireEvent.click(cached);
    await waitFor(() => expect(new URL(window.location.href).searchParams.get("symbol")).toBe("600519"));
  });

  it("offers candidates and searches by code or name after 250ms", async () => {
    const search = vi.fn(() => Promise.resolve(searchResult));
    renderSelector({ search });
    openShortTermCandidates();
    expect(await screen.findByRole("button", { pressed: true })).toHaveTextContent("600000");
    const callsBeforeInput = search.mock.calls.length;
    fireEvent.change(screen.getByRole("searchbox", { name: "搜索 A 股" }), { target: { value: "平安" } });
    expect(search).toHaveBeenCalledTimes(callsBeforeInput);
    expect(await screen.findByRole("option", { name: /000001.*平安银行/ })).toBeInTheDocument();
    expect(search).toHaveBeenCalledWith("平安");
  });

  it("shows the candidate data source, coverage and daily refresh cadence", async () => {
    renderSelector();

    const provenance = await screen.findByRole("status", { name: "候选数据说明" });
    expect(provenance).toHaveTextContent("百度日线");
    expect(provenance).toHaveTextContent("可比较 96 / 128 只");
    expect(provenance).toHaveTextContent("数据至 2026-07-14");
    expect(provenance).toHaveTextContent("收盘后更新");
  });

  it("selects the first valid candidate only when no selection exists", async () => {
    renderSelector();
    await waitFor(() => expect(new URL(window.location.href).searchParams.get("symbol")).toBe("600000"));
  });

  it("does not replace an explicit selection when candidates refresh", async () => {
    const view = renderSelector();
    fireEvent.click(screen.getByRole("tab", { name: "波段候选" }));
    fireEvent.click(await screen.findByRole("button", { pressed: false }));
    expect(new URL(window.location.href).searchParams.get("symbol")).toBe("000001");
    view.rerender(<SelectedInstrumentProvider><StockSelector loadCandidates={() => Promise.resolve(empty)} search={() => Promise.resolve(searchResult)} /></SelectedInstrumentProvider>);
    await screen.findByText("本地候选池为空");
    expect(new URL(window.location.href).searchParams.get("symbol")).toBe("000001");
  });

  it("does not guess a stock when the candidate pool is empty", async () => {
    renderSelector({ loadCandidates: () => Promise.resolve(empty) });
    openShortTermCandidates();
    expect(await screen.findByText("本地候选池为空")).toBeInTheDocument();
    expect(new URL(window.location.href).searchParams.has("symbol")).toBe(false);
    expect(screen.getByText("尚未选择 A 股")).toBeInTheDocument();
  });

  it("stores watchlist symbols under the A-share-only key", async () => {
    renderSelector();
    openShortTermCandidates();
    await screen.findByRole("button", { pressed: true });
    fireEvent.click(screen.getByRole("button", { name: "将 600000 加入自选" }));
    await waitFor(() => expect(localStorage.getItem("qibao.a_share.watchlist.v1")).toBe('["600000"]'));
    expect(localStorage.getItem("qibao.watchlist")).toBeNull();
  });

  it("restores watchlist identity after the stock leaves all candidate lists", async () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["000001"]');
    renderSelector({ loadCandidates: () => Promise.resolve(empty) });
    fireEvent.click(screen.getByRole("tab", { name: "自选股" }));
    expect(await screen.findByText("平安银行")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /000001.*平安银行/ })).toBeInTheDocument();
  });

  it("renders watchlist rows with code, name, and an independent watchlist score only", async () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["600000"]');
    renderSelector({ loadWatchlistScores: () => Promise.resolve(watchlistScores) });
    fireEvent.click(screen.getByRole("tab", { name: "自选股" }));

    const row = await screen.findByRole("button", { pressed: true });
    expect(row).toHaveTextContent("600000");
    expect(row).toHaveTextContent("浦发银行");
    expect(row).toHaveTextContent("42.0");
    expect(row).toHaveTextContent("自选分");
    expect(row).not.toHaveTextContent("68.5");
    expect(row).not.toHaveTextContent("最新价不可用");
    expect(row).not.toHaveTextContent("当前涨跌不可用");
    expect(row).not.toHaveTextContent("行情可用");
    expect(row).not.toHaveTextContent("数据截至");
  });

  it("explains missing watchlist history and refreshes it before rescoring", async () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["600000"]');
    const missing = {
      ...watchlistScores,
      items: [{ symbol: "600000", status: "insufficient_history" as const, score: null, latest_trade_date: null, reason: "history_requires_60_bars" }],
    };
    const loadWatchlistScores = vi.fn()
      .mockResolvedValueOnce(missing)
      .mockResolvedValue(watchlistScores);
    const prepare = vi.fn(() => Promise.resolve({ symbol: "600000" }));
    renderSelector({ loadWatchlistScores, prepare });
    fireEvent.click(screen.getByRole("tab", { name: "自选股" }));

    expect(await screen.findByText("待补60日日线")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "刷新自选评分" }));

    await waitFor(() => expect(prepare).toHaveBeenCalledWith("600000"));
    await waitFor(() => expect(loadWatchlistScores).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("42.0")).toBeInTheDocument();
  });

  it("keeps market sentiment out of the watchlist selector", async () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["000001"]');
    renderSelector({ loadCandidates: () => Promise.resolve(empty) });

    expect(screen.queryByRole("region", { name: "自选股市场环境" })).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /000001.*平安银行/ })).toBeInTheDocument();
  });

  it("shows a search failure reason and retries the same query", async () => {
    let attempts = 0;
    const search = vi.fn((query: string) => {
      if (query !== "平安") return Promise.resolve(query === "600000" ? puFaResult : searchResult);
      attempts += 1;
      return attempts === 1 ? Promise.reject(new Error("目录暂不可用")) : Promise.resolve(searchResult);
    });
    renderSelector({ search });
    fireEvent.change(screen.getByRole("searchbox", { name: "搜索 A 股" }), { target: { value: "平安" } });
    expect(await screen.findByRole("alert")).toHaveTextContent("股票搜索暂不可用，请稍后重试。");
    expect(screen.queryByText("目录暂不可用")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重试搜索" }));
    expect(await screen.findByRole("option", { name: /000001.*平安银行/ })).toBeInTheDocument();
    expect(search.mock.calls.filter(([query]) => query === "平安")).toHaveLength(2);
  });

  it("distinguishes an unavailable verification source from an unknown stock", async () => {
    renderSelector({
      loadCandidates: () => Promise.resolve(empty),
      search: (query) => Promise.resolve({
        query,
        items: [],
        source_status: "unavailable",
        server_time: "2026-07-16T09:30:00+08:00",
      }),
    });

    fireEvent.change(screen.getByRole("searchbox", { name: "搜索 A 股" }), {
      target: { value: "600519" },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("行情验证源暂不可用");
    expect(screen.queryByText("没有找到已验证的 A 股")).not.toBeInTheDocument();
  });

  it("adds a search result to watchlist", async () => {
    renderSelector();
    fireEvent.change(screen.getByRole("searchbox", { name: "搜索 A 股" }), { target: { value: "平安" } });
    await screen.findByRole("option", { name: /000001.*平安银行/ });
    fireEvent.click(screen.getByRole("button", { name: "将 000001 加入自选" }));
    expect(localStorage.getItem("qibao.a_share.watchlist.v1")).toBe('["000001"]');
  });

  it("shows verified historical price without presenting it as live quote data", async () => {
    renderSelector();
    openShortTermCandidates();
    const selected = await screen.findByRole("button", { pressed: true });
    expect(await screen.findByText(/浦发银行/)).toBeInTheDocument();
    expect(selected).toHaveTextContent("600000");
    expect(selected).toHaveTextContent("浦发银行");
    expect(selected).toHaveTextContent("68.5");
    expect(selected).not.toHaveTextContent("最近收盘");
    expect(selected).not.toHaveTextContent("近 20 日");
    expect(selected).not.toHaveTextContent("近 5 日");
    expect(selected).not.toHaveTextContent("数据日");
    expect(selected).not.toHaveTextContent("动量");
    expect(selected).not.toHaveTextContent("量能");
    expect(screen.queryByText("最新价不可用")).not.toBeInTheDocument();
    expect(screen.queryByText("当前涨跌不可用")).not.toBeInTheDocument();
  });

  it("polls candidates without replacing an explicit search selection", async () => {
    vi.useFakeTimers();
    const loadCandidates = vi.fn(() => Promise.resolve(first));
    renderSelector({ loadCandidates, pollIntervalMs: 1000 });
    await vi.advanceTimersByTimeAsync(1);
    fireEvent.click(screen.getByRole("tab", { name: "波段候选" }));
    fireEvent.click(screen.getByRole("button", { pressed: false }));
    await vi.advanceTimersByTimeAsync(1000);
    expect(loadCandidates).toHaveBeenCalledTimes(2);
    expect(new URL(window.location.href).searchParams.get("symbol")).toBe("000001");
    vi.useRealTimers();
  });

  it("links tabs to their panel and supports arrow-key switching", async () => {
    renderSelector();
    const watchlist = screen.getByRole("tab", { name: "自选股" });
    expect(watchlist).toHaveAttribute("aria-controls", "stock-selector-panel");
    fireEvent.keyDown(watchlist, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "短线候选" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveAttribute("aria-labelledby", "stock-selector-tab-short");
  });

  it("invalidates an in-flight search immediately when a new debounced query is typed", async () => {
    let resolveOld!: (value: InstrumentSearchResponse) => void;
    const old = new Promise<InstrumentSearchResponse>((resolve) => { resolveOld = resolve; });
    const search = vi.fn((query: string) => query === "旧词" ? old : Promise.resolve(searchResult));
    renderSelector({ loadCandidates: () => Promise.resolve(empty), search });
    fireEvent.change(screen.getByRole("searchbox", { name: "搜索 A 股" }), { target: { value: "旧词" } });
    await waitFor(() => expect(search).toHaveBeenCalledWith("旧词"));
    fireEvent.change(screen.getByRole("searchbox", { name: "搜索 A 股" }), { target: { value: "新词" } });
    resolveOld({ ...searchResult, query: "旧词", items: [{ ...searchResult.items[0], name: "旧结果" }] });
    await Promise.resolve();
    expect(screen.queryByText("旧结果")).not.toBeInTheDocument();
    expect(await screen.findByText("平安银行")).toBeInTheDocument();
  });

  it("keeps a watchlist identity error visible and retries that symbol", async () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["000001"]');
    let attempts = 0;
    const search = vi.fn((query: string) => {
      if (query !== "000001") return Promise.resolve(puFaResult);
      attempts += 1;
      return attempts === 1 ? Promise.reject(new Error("身份目录离线")) : Promise.resolve(searchResult);
    });
    renderSelector({ loadCandidates: () => Promise.resolve(empty), search });
    fireEvent.click(screen.getByRole("tab", { name: "自选股" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("股票身份数据暂不可用，请稍后重试。");
    expect(screen.queryByText("身份目录离线")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重试 000001 身份" }));
    expect(await screen.findByText("平安银行")).toBeInTheDocument();
  });

  it("removes convertible bonds and invalid codes from persisted A-share watchlist", () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["600000","113065","123001","not-code"]');
    renderSelector({ loadCandidates: () => Promise.resolve(empty) });
    expect(localStorage.getItem("qibao.a_share.watchlist.v1")).toBe('["600000"]');
  });

  it("ignores an older candidate refresh that resolves after a newer refresh", async () => {
    let resolveOld!: (value: CandidateBoard) => void;
    const old = new Promise<CandidateBoard>((resolve) => { resolveOld = resolve; });
    const loadCandidates = vi.fn().mockReturnValueOnce(old).mockResolvedValue(empty);
    renderSelector({ loadCandidates });
    openShortTermCandidates();
    fireEvent.click(screen.getByRole("button", { name: "刷新候选" }));
    expect(await screen.findByText("本地候选池为空")).toBeInTheDocument();
    resolveOld(first);
    await Promise.resolve();
    expect(screen.queryByRole("button", { pressed: true })).not.toBeInTheDocument();
  });

  it("only handles horizontal arrow keys and prevents their default behavior", () => {
    renderSelector();
    const watchlist = screen.getByRole("tab", { name: "自选股" });
    const vertical = new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true, cancelable: true });
    act(() => { watchlist.dispatchEvent(vertical); });
    expect(vertical.defaultPrevented).toBe(false);
    expect(watchlist).toHaveAttribute("aria-selected", "true");
    const horizontal = new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true });
    act(() => { watchlist.dispatchEvent(horizontal); });
    expect(horizontal.defaultPrevented).toBe(true);
    expect(screen.getByRole("tab", { name: "短线候选" })).toHaveAttribute("aria-selected", "true");
  });

  it("does not let an old identity failure overwrite a newer successful retry", async () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["000001"]');
    let rejectOld!: (reason: Error) => void;
    const old = new Promise<InstrumentSearchResponse>((_, reject) => { rejectOld = reject; });
    const search = vi.fn().mockReturnValueOnce(old).mockResolvedValue(searchResult);
    renderSelector({ loadCandidates: () => Promise.resolve(empty), search });
    fireEvent.click(screen.getByRole("tab", { name: "自选股" }));
    await waitFor(() => expect(search).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("button", { name: "刷新候选" }));
    expect(await screen.findByText("平安银行")).toBeInTheDocument();
    await act(async () => { rejectOld(new Error("迟到的旧错误")); await old.catch(() => undefined); });
    await waitFor(() => expect(screen.queryByText("迟到的旧错误")).not.toBeInTheDocument());
    expect(screen.getByText("平安银行")).toBeInTheDocument();
  });

  it("does not let an old identity success replace a newer successful retry", async () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["000001"]');
    let resolveOld!: (value: InstrumentSearchResponse) => void;
    const old = new Promise<InstrumentSearchResponse>((resolve) => { resolveOld = resolve; });
    const newer = { ...searchResult, items: [{ ...searchResult.items[0], name: "新名称" }] };
    const search = vi.fn().mockReturnValueOnce(old).mockResolvedValue(newer);
    renderSelector({ loadCandidates: () => Promise.resolve(empty), search });
    fireEvent.click(screen.getByRole("tab", { name: "自选股" }));
    await waitFor(() => expect(search).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("button", { name: "刷新候选" }));
    expect(await screen.findByText("新名称")).toBeInTheDocument();
    await act(async () => { resolveOld(searchResult); await old; });
    await waitFor(() => expect(screen.queryByText("平安银行")).not.toBeInTheDocument());
    expect(screen.getByText("新名称")).toBeInTheDocument();
  });

  it("loads sentiment only for short-term candidates and refreshes stale data once", async () => {
    const stale = candidateSentimentBatch(first, [candidateSentiment("600000", {
      freshness: "stale",
      primary_reason: "历史情绪仅供参考。",
    })]);
    const fresh = candidateSentimentBatch();
    const loadCandidateSentiments = vi.fn(() => Promise.resolve(stale));
    const refreshCandidateSentiments = vi.fn(() => Promise.resolve(fresh));
    const onCandidateSentiments = vi.fn();
    renderSelector({
      loadCandidateSentiments,
      refreshCandidateSentiments,
      onCandidateSentiments,
    });
    openShortTermCandidates();

    await waitFor(() => expect(refreshCandidateSentiments).toHaveBeenCalledTimes(1));
    expect(loadCandidateSentiments).toHaveBeenCalledWith("candidate-1");
    expect(onCandidateSentiments).toHaveBeenLastCalledWith(fresh);
    expect(screen.queryByRole("group", { name: "600000 个股综合情绪" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "刷新候选" }));
    await waitFor(() => expect(loadCandidateSentiments).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("tab", { name: "波段候选" }));
    fireEvent.click(screen.getByRole("tab", { name: "自选股" }));
    expect(loadCandidateSentiments).toHaveBeenCalledTimes(1);
    expect(refreshCandidateSentiments).toHaveBeenCalledTimes(1);
  });

  it("reuses sentiment when polling changes only the candidate snapshot id", async () => {
    const equivalent: CandidateBoard = { ...first, snapshot_id: "candidate-2" };
    const loadCandidates = vi.fn().mockResolvedValueOnce(first).mockResolvedValue(equivalent);
    const batch = candidateSentimentBatch();
    const loadCandidateSentiments = vi.fn(() => Promise.resolve(batch));
    const onCandidateSentiments = vi.fn();
    renderSelector({ loadCandidates, loadCandidateSentiments, onCandidateSentiments });
    openShortTermCandidates();

    await waitFor(() => expect(onCandidateSentiments).toHaveBeenCalledWith(batch));
    fireEvent.click(screen.getByRole("button", { name: "刷新候选" }));
    await waitFor(() => expect(loadCandidates).toHaveBeenCalledTimes(2));
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });

    expect(loadCandidateSentiments).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("group", { name: "600000 个股综合情绪" })).not.toBeInTheDocument();
  });

  it("keeps candidate rows selectable and shows one retryable batch error", async () => {
    const recovered = candidateSentimentBatch();
    const loadCandidateSentiments = vi.fn()
      .mockRejectedValueOnce(new Error("https://secret.example/token"))
      .mockResolvedValueOnce(recovered);
    const onCandidateSentiments = vi.fn();
    renderSelector({ loadCandidateSentiments, onCandidateSentiments });
    openShortTermCandidates();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("短线候选情绪暂不可用，请稍后重试。");
    expect(screen.getAllByText("短线候选情绪暂不可用，请稍后重试。")).toHaveLength(1);
    expect(screen.getByRole("button", { pressed: true })).toHaveTextContent("600000");

    fireEvent.click(screen.getByRole("button", { name: "重试情绪" }));
    await waitFor(() => expect(onCandidateSentiments).toHaveBeenLastCalledWith(recovered));
    expect(screen.queryByRole("group", { name: "600000 个股综合情绪" })).not.toBeInTheDocument();
    expect(loadCandidateSentiments).toHaveBeenCalledTimes(2);
  });

  it("ignores an older sentiment response after the candidate snapshot changes", async () => {
    const second: CandidateBoard = {
      ...first,
      snapshot_id: "candidate-2",
      input_snapshot_hash: "b".repeat(64),
      short_term: [{
        ...first.swing[0],
        horizon: "short_term",
      }],
      swing: [],
    };
    let resolveOld!: (value: CandidateSentimentBatch) => void;
    const old = new Promise<CandidateSentimentBatch>((resolve) => { resolveOld = resolve; });
    const loadCandidates = vi.fn().mockResolvedValueOnce(first).mockResolvedValue(second);
    const newer = candidateSentimentBatch(second, [candidateSentiment("000001", {
      primary_reason: "新快照原因。",
    })]);
    const loadCandidateSentiments = vi.fn((snapshotId: string) => (
      snapshotId === "candidate-1" ? old : Promise.resolve(newer)
    ));
    const onCandidateSentiments = vi.fn();
    renderSelector({ loadCandidates, loadCandidateSentiments, onCandidateSentiments });
    openShortTermCandidates();

    await waitFor(() => expect(loadCandidateSentiments).toHaveBeenCalledWith("candidate-1"));
    fireEvent.click(screen.getByRole("button", { name: "刷新候选" }));
    await waitFor(() => expect(onCandidateSentiments).toHaveBeenLastCalledWith(newer));

    const older = candidateSentimentBatch(first, [candidateSentiment("600000", {
      primary_reason: "旧快照原因。",
    })]);
    await act(async () => {
      resolveOld(older);
      await old;
    });
    expect(onCandidateSentiments).not.toHaveBeenCalledWith(older);
    expect(onCandidateSentiments).toHaveBeenLastCalledWith(newer);
  });

  it("preserves candidate order when sentiment scores differ", async () => {
    const ordered: CandidateBoard = {
      ...first,
      short_term: [
        first.short_term[0],
        { ...first.short_term[0], symbol: "000001", factor_snapshot: { ...factor, symbol: "000001" } },
      ],
      swing: [],
    };
    const batch = candidateSentimentBatch(ordered, [
      candidateSentiment("600000", { score: "20", band: "cautious" }),
      candidateSentiment("000001", { score: "90", band: "overheated" }),
    ]);
    const onCandidateSentiments = vi.fn();
    const view = renderSelector({
      loadCandidates: () => Promise.resolve(ordered),
      loadCandidateSentiments: () => Promise.resolve(batch),
      onCandidateSentiments,
    });
    openShortTermCandidates();

    await waitFor(() => expect(onCandidateSentiments).toHaveBeenCalledWith(batch));
    const rows = [...view.container.querySelectorAll(".stock-option > button:first-child")];
    expect(rows.map((row) => row.textContent?.includes("600000") ? "600000" : "000001")).toEqual([
      "600000",
      "000001",
    ]);
  });
});
