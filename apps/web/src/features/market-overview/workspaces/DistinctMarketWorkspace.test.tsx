import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { MarketOverviewResponse } from "../types";
import { DistinctMarketWorkspace } from "./DistinctMarketWorkspace";
import { WORKSPACE_DEFINITIONS } from "./workspaceRegistry";

const overview = {
  status: "partial", as_of: "2026-07-29", observed_at: "2026-07-29T10:30:00+08:00",
  sentiment: { score: "61", band: "轮动", coverage_percent: "90", quality: "ready", observed_at: "2026-07-29T10:30:00+08:00" },
  breadth: { rising_count: 2800, falling_count: 2100, flat_count: 100, valid_count: 5000 },
  limit_ecology: { limit_up_count: 2, limit_down_count: 1, broken_limit_up_count: 1, seal_rate_percent: "66.67" },
  liquidity: { total_amount_yi: "9800", baseline_amount_yi: "10000", relative_amount: "0.98" },
  market_data: { source: "tdx-local-rpc", quality: "ready", observed_at: "2026-07-29T10:30:00+08:00", quote_count: 5000, universe_count: 5200 },
  indices: [], minute_series: [],
  anomalies: [{ anomaly_id: "a1", occurred_at: "2026-07-29T10:20:00+08:00", label: "算力拉升", headline: "算力板块快速拉升", direction: "positive", themes: ["算力"], symbols: ["600001"] }],
  live_feed: [{ event_id: "n1", occurred_at: "2026-07-29T10:22:00+08:00", headline: "算力需求增长", summary: "公开新闻摘要", themes: ["算力", "数据中心"], symbols: ["600001"], source: "公开资讯", review_state: "verified" }],
  sectors: [{ sector_id: "s1", name: "算力", change_percent: "4.2", amount_yi: "220", limit_up_count: 2, rising_count: 40, falling_count: 5, stock_count: 50 }],
  sector_stocks: { s1: [{ symbol: "600001", name: "封板股", change_percent: "10", amount_yi: "30", market_cap_yi: "300", first_limit_time: "10:05", position: "前排", quality: "ready" }] },
  market_stocks: [
    { symbol: "600001", name: "封板股", price: "11", previous_close: "10", open: "10.4", high: "11", low: "10.2", volume: "1000", amount_yi: "30", change_percent: "10", state: "limit_up", observed_at: "2026-07-29T10:30:00+08:00", source: "tdx-local-rpc", quality: "ready" },
    { symbol: "600002", name: "炸板股", price: "10.5", previous_close: "10", open: "10.1", high: "11", low: "10", volume: "900", amount_yi: "20", change_percent: "5", state: "broken_limit_up", observed_at: "2026-07-29T10:30:00+08:00", source: "tdx-local-rpc", quality: "ready" },
    { symbol: "600005", name: "低开股", price: "9.7", previous_close: "10", open: "9.5", high: "9.9", low: "9.4", volume: "700", amount_yi: "8", change_percent: "-3", state: "active", observed_at: "2026-07-29T10:30:00+08:00", source: "tdx-local-rpc", quality: "ready" },
    { symbol: "300006", name: "非异动高热股", price: "23.8", previous_close: "20", open: "20.8", high: "23.8", low: "20.6", volume: "2000", amount_yi: "100", change_percent: "19", state: "limit_up", observed_at: "2026-07-29T10:30:00+08:00", source: "tdx-local-rpc", quality: "ready" },
  ],
  review: {
    as_of: "2026-07-29", observed_at: "2026-07-29T16:20:00+08:00",
    latest_trade_date: "2026-07-29", source: "tdx-local-day", quality: "ready",
    universe_count: 5200, history_ready_count: 5150, formula_version: "a-share-market-review-v1", warnings: [],
    consecutive_limit_up: [{ symbol: "600001", name: "封板股", trade_date: "2026-07-29", category: "consecutive_limit_up", close: "11", change_percent: "10", amount_yi: "30", source: "tdx-local-day", board_count: 3, limit_statistics: "3/3", turnover_rate: null, seal_amount_yi: null, failed_limit_count: null, first_seal_time: null, volume_multiple: "1.5", reference_high: null, window_days: null, range_position_percent: null }],
    first_limit_up: [{ symbol: "600003", name: "首板股", trade_date: "2026-07-29", category: "first_limit_up", close: "8.8", change_percent: "10", amount_yi: "18", source: "tdx-local-day", board_count: 1, limit_statistics: "1/1", turnover_rate: null, seal_amount_yi: null, failed_limit_count: null, first_seal_time: null, volume_multiple: "2.2", reference_high: null, window_days: null, range_position_percent: null }],
    volume_breakouts: [{ symbol: "600004", name: "突破股", trade_date: "2026-07-29", category: "volume_breakout", close: "20", change_percent: "5", amount_yi: "12", source: "tdx-local-day", board_count: null, limit_statistics: null, turnover_rate: null, seal_amount_yi: null, failed_limit_count: null, first_seal_time: null, volume_multiple: "2.5", reference_high: "19", window_days: 60, range_position_percent: null }],
    previous_high_breakouts: [], low_position_volume: [],
    dragon_tiger: [{ symbol: "300308", name: "中际旭创", trade_date: "2026-07-28", reason: "日涨幅偏离值", change_percent: "19.99", buy_amount_yi: "28.39", sell_amount_yi: "18.11", net_amount_yi: "10.28", source: "eastmoney-dragon-tiger", seats: [{ symbol: "300308", trade_date: "2026-07-28", seat_name: "深股通专用", direction: "buy", buy_amount_yi: "59.25", sell_amount_yi: "48.96", net_amount_yi: "10.29", source: "eastmoney-dragon-tiger" }] }],
  },
  warnings: [], sources: ["tdx-local-realtime", "local-news-cache"],
} as unknown as MarketOverviewResponse;

describe("DistinctMarketWorkspace", () => {
  it("renders auction, limit failure and calendar as materially different workspaces", () => {
    const { rerender } = render(<DistinctMarketWorkspace feature="竞价异动" data={overview} />);
    expect(screen.getByRole("region", { name: "竞价异动专属工作区" })).toHaveAttribute("data-layout", "auction-radar");
    expect(screen.getByRole("region", { name: "开盘缺口分布" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "开盘缺口分布" })).toHaveTextContent("低开股");

    rerender(<DistinctMarketWorkspace feature="炸板" data={overview} />);
    expect(screen.getByRole("region", { name: "炸板专属工作区" })).toHaveAttribute("data-layout", "failure-lab");
    expect(screen.getByRole("region", { name: "炸板风险台" })).toHaveTextContent("炸板股");
    expect(screen.queryByRole("region", { name: "开盘缺口分布" })).not.toBeInTheDocument();

    rerender(<DistinctMarketWorkspace feature="投资日历" data={overview} />);
    expect(screen.getByRole("region", { name: "投资日历专属工作区" })).toHaveAttribute("data-layout", "calendar-ledger");
    expect(screen.getByRole("region", { name: "A 股事件日历" })).toHaveTextContent("算力需求增长");
  });

  it("does not label a previous-close workspace as connected real-time evidence", () => {
    const previousClose = {
      ...overview,
      market_data: {
        ...overview.market_data,
        phase: "premarket" as const,
        freshness: "previous_close" as const,
      },
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="盘中异动" data={previousClose} />);

    expect(screen.getByText("上一交易日收盘快照 · 等待开盘")).toBeInTheDocument();
    expect(screen.queryByText("5 秒刷新 · 不生成模拟值")).not.toBeInTheDocument();
  });

  it("uses real public seat records for seat tracking without amount proxies", () => {
    render(<DistinctMarketWorkspace feature="游资追踪" data={overview} />);
    expect(screen.getByRole("region", { name: "席位净额追踪榜" })).toHaveTextContent("深股通专用");
    expect(screen.getByRole("region", { name: "席位净额追踪榜" })).toHaveTextContent("+10.29亿");
    expect(screen.getByRole("region", { name: "席位净额追踪榜" })).not.toHaveTextContent("成交活跃");
  });

  it("keeps unavailable dragon-tiger evidence unavailable across seat workspaces", () => {
    const unavailableSeats = {
      ...overview,
      review: { ...overview.review!, dragon_tiger: [], warnings: ["dragon_tiger_unavailable"] },
    } as MarketOverviewResponse;

    const { rerender } = render(<DistinctMarketWorkspace feature="游资追踪" data={unavailableSeats} />);
    expect(screen.getByRole("region", { name: "席位净额追踪榜" })).toHaveTextContent("龙虎榜公开接口当前不可用");
    expect(screen.getByRole("region", { name: "席位来源与字段审计" })).toHaveTextContent("龙虎榜席位");

    rerender(<DistinctMarketWorkspace feature="游资动向" data={unavailableSeats} />);
    expect(screen.getByRole("region", { name: "席位买卖方向分布" })).toHaveTextContent("龙虎榜公开接口当前不可用");
    expect(screen.getByRole("region", { name: "龙虎榜资金概览" })).toHaveTextContent("龙虎榜公开接口当前不可用");

    rerender(<DistinctMarketWorkspace feature="龙虎榜" data={unavailableSeats} />);
    expect(screen.getByRole("region", { name: "龙虎榜股票与席位" })).toHaveTextContent("龙虎榜公开接口当前不可用");
    expect(screen.getByRole("region", { name: "龙虎榜资金仪表" })).toHaveTextContent("龙虎榜公开接口当前不可用");
  });

  it("limits the sector limit-up table to verified members of the leading limit-up sector", () => {
    render(<DistinctMarketWorkspace feature="板块涨停" data={overview} />);

    const board = screen.getByRole("region", { name: "板块涨停成员" });
    expect(board).toHaveTextContent("算力");
    expect(board).toHaveTextContent("封板股");
    expect(board).not.toHaveTextContent("非异动高热股");
  });

  it("uses actual anomaly-linked stocks for the anomaly popularity ranking", () => {
    render(<DistinctMarketWorkspace feature="七大人气榜" data={overview} />);

    const board = screen.getByRole("region", { name: "七大人气榜单" });
    expect(board).toHaveTextContent("封板股");
    expect(within(board).getByText("异动榜首").parentElement).toHaveTextContent("封板股");
    expect(within(board).getByText("异动榜首").parentElement).not.toHaveTextContent("非异动高热股");
  });

  it("uses the full row for an unpaired hotspot timeline", () => {
    render(<DistinctMarketWorkspace feature="热点播报" data={overview} />);

    expect(screen.getByRole("region", { name: "热点时间轴" })).toHaveClass("size-wide");
  });

  it("keeps real stock navigation on feature-specific tables", () => {
    const onOpenAShare = vi.fn();
    render(<DistinctMarketWorkspace feature="涨停板" data={overview} onOpenAShare={onOpenAShare} />);
    screen.getByRole("button", { name: "查看 600001 封板股" }).click();
    expect(onOpenAShare).toHaveBeenCalledWith("600001");
  });

  it("opens a stock when any cell in a feature table row is activated", () => {
    const onOpenAShare = vi.fn();
    render(<DistinctMarketWorkspace feature="涨停板" data={overview} onOpenAShare={onOpenAShare} />);

    const row = screen.getByRole("link", { name: "查看 600001 封板股" });
    fireEvent.click(within(row).getByText("30.00亿"));

    expect(onOpenAShare).toHaveBeenCalledWith("600001");
  });

  it("does not present unavailable evidence as live or as zero-percent coverage", () => {
    const unavailable = {
      ...overview,
      market_data: {
        source: "unavailable",
        quality: "unavailable",
        observed_at: null,
        quote_count: 0,
        universe_count: 0,
      },
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="涨停板" data={unavailable} />);

    expect(screen.getByText("当前行情不可用")).toBeInTheDocument();
    expect(screen.getAllByText("--").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/0\.0%/)).not.toBeInTheDocument();
  });

  it("does not turn unavailable market fields into zero-valued workspace metrics", () => {
    const unavailable = {
      ...overview,
      status: "unavailable" as const,
      market_data: {
        source: "unavailable",
        quality: "unavailable" as const,
        observed_at: null,
        quote_count: 0,
        universe_count: 0,
      },
      breadth: { rising_count: 0, falling_count: 0, flat_count: 0, valid_count: 0 },
      limit_ecology: { limit_up_count: 0, limit_down_count: 0, broken_limit_up_count: 0, seal_rate_percent: null },
    } as unknown as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="涨停板" data={unavailable} />);

    const dashboard = screen.getByRole("region", { name: "涨停板关键仪表" });
    expect(dashboard).toHaveTextContent("未接入");
    expect(dashboard).not.toHaveTextContent("严格涨停0");
  });

  it("does not expose zero-valued market pulse cards when the quote source is unavailable", () => {
    const unavailable = {
      ...overview,
      status: "unavailable" as const,
      market_data: {
        source: "unavailable",
        quality: "unavailable" as const,
        observed_at: null,
        quote_count: 0,
        universe_count: 0,
      },
      breadth: { rising_count: 0, falling_count: 0, flat_count: 0, valid_count: 0 },
      limit_ecology: { limit_up_count: 0, limit_down_count: 0, broken_limit_up_count: 0, seal_rate_percent: null },
      liquidity: { total_amount_yi: null, baseline_amount_yi: null, relative_amount: null },
      regime: null,
      sentiment: { ...overview.sentiment, score: null, band: "数据不足", quality: "unavailable" },
    } as unknown as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="情绪周期" data={unavailable} />);

    const pulse = screen.getByRole("region", { name: "市场风格仪表" });
    expect(pulse).toHaveTextContent("未接入");
    expect(pulse).not.toHaveTextContent("上涨 / 下跌0 / 0");
    expect(pulse).not.toHaveTextContent("涨停 / 跌停0 / 0");
  });

  it("uses score bands for the popularity composition instead of price-return bins", () => {
    render(<DistinctMarketWorkspace feature="人气榜" data={overview} />);

    const distribution = screen.getByRole("region", { name: "人气构成分布" });
    expect(distribution).toHaveTextContent("人气分 0-20");
    expect(distribution).toHaveTextContent("人气分 80-100");
    expect(distribution).not.toHaveTextContent("跌幅 > 7%");
  });

  it("uses opening-gap checks for the opening checklist instead of repeating the regime cards", () => {
    render(<DistinctMarketWorkspace feature="开盘啦" data={overview} />);

    const opening = screen.getByRole("region", { name: "开盘市场检查单" });
    expect(opening).toHaveTextContent("高开 >= 2%");
    expect(opening).toHaveTextContent("高开延续");
    expect(opening).not.toHaveTextContent("市场风格");
  });

  it("keeps hotspot interpretation on verified, symbol-linked A-share news", () => {
    const mixedNews = {
      ...overview,
      live_feed: [
        ...overview.live_feed,
        { event_id: "n2", occurred_at: "2026-07-29T10:25:00+08:00", headline: "未关联传闻", summary: "待核验", themes: [], symbols: [], source: "未知来源", review_state: "pending" },
      ],
    } as unknown as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="热点解读" data={mixedNews} />);

    const news = screen.getByRole("region", { name: "热点原始资讯" });
    expect(news).toHaveTextContent("算力需求增长");
    expect(news).not.toHaveTextContent("未关联传闻");
  });

  it("keeps the full hotspot evidence chain scoped to verified A-share-linked themes", () => {
    const mixedNews = {
      ...overview,
      live_feed: [
        ...overview.live_feed,
        { event_id: "n2", occurred_at: "2026-07-29T10:25:00+08:00", headline: "未关联传闻", summary: "待核验", themes: [], symbols: [], source: "未知来源", review_state: "pending" },
      ],
    } as unknown as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="热点解读" data={mixedNews} />);

    const chain = screen.getByRole("region", { name: "热点证据链" });
    expect(chain).toHaveTextContent("算力需求增长");
    expect(chain).not.toHaveTextContent("未关联传闻");
  });

  it("shows local, evidence-first gates for AI selection and Wencai instead of the generic market checklist", () => {
    const { rerender } = render(<DistinctMarketWorkspace feature="AI+选股" data={overview} />);
    const aiGates = screen.getByRole("region", { name: "AI 选股证据闸门" });
    expect(aiGates).toHaveTextContent("行情字段完整");
    expect(aiGates).toHaveTextContent("AI 只解释证据");

    rerender(<DistinctMarketWorkspace feature="问财选股" data={overview} />);
    const localGates = screen.getByRole("region", { name: "本地选股规则器" });
    expect(localGates).toHaveTextContent("本地规则执行");
    expect(localGates).toHaveTextContent("不调用问财官方接口");
  });

  it("uses a crowding-specific risk board for concept overlap", () => {
    render(<DistinctMarketWorkspace feature="概念叠加" data={overview} />);

    const risk = screen.getByRole("region", { name: "题材拥挤提示" });
    expect(risk).toHaveTextContent("封板股");
    expect(risk).not.toHaveTextContent("炸板股");
  });

  it("renders the newly available historical new-high and previous-limit records", () => {
    const historyData = {
      ...overview,
      review: {
        ...overview.review!,
        new_high_100: [{ symbol: "600010", name: "新高股", trade_date: "2026-07-29", category: "new_high_100", close: "20", change_percent: "4", amount_yi: "12", source: "tdx-local-day", board_count: null, limit_statistics: null, prior_close: null, prior_change_percent: null, turnover_rate: null, seal_amount_yi: null, failed_limit_count: null, first_seal_time: null, volume_multiple: "1.4", reference_high: "19", window_days: 100, range_position_percent: null }],
        previous_limit_up: [{ symbol: "600011", name: "反馈股", trade_date: "2026-07-29", category: "previous_limit_feedback", close: "9.5", change_percent: "-5", amount_yi: "8", source: "tdx-local-day", board_count: null, limit_statistics: "上一日涨停", prior_close: "10", prior_change_percent: "10", turnover_rate: null, seal_amount_yi: null, failed_limit_count: null, first_seal_time: null, volume_multiple: null, reference_high: null, window_days: 1, range_position_percent: null }],
      },
    } as unknown as MarketOverviewResponse;

    const { rerender } = render(<DistinctMarketWorkspace feature="百日新高" data={historyData} />);
    expect(screen.getByRole("region", { name: "已验证新高清单" })).toHaveTextContent("新高股");
    expect(screen.getByRole("region", { name: "已验证新高清单" })).not.toHaveTextContent("逐股结果尚未");

    rerender(<DistinctMarketWorkspace feature="昨涨停" data={historyData} />);
    expect(screen.getByRole("region", { name: "可验证反馈明细" })).toHaveTextContent("反馈股");
    expect(screen.getByRole("region", { name: "今日反馈分组" })).toHaveTextContent("回撤");
  });

  it("does not silently turn unsupported historical rankings into a generic empty stock table", () => {
    render(<DistinctMarketWorkspace feature="百日新高" data={overview} />);

    const ranking = screen.getByRole("region", { name: "已验证新高清单" });
    expect(ranking).toHaveTextContent("100 日新高逐股结果尚未由当前复盘接口返回");
    expect(ranking).not.toHaveTextContent("严格筛选后没有记录");
  });

  it("mounts all 50 workspaces without falling back to the retired generic dashboard", () => {
    for (const definition of WORKSPACE_DEFINITIONS) {
      const view = render(<DistinctMarketWorkspace feature={definition.label} data={overview} />);
      const workspace = screen.getByRole("region", { name: `${definition.label}专属工作区` });
      expect(workspace).toHaveAttribute("data-layout", definition.layout);
      expect(workspace).not.toHaveTextContent("核心排行");
      expect(workspace).not.toHaveTextContent("候选明细");
      view.unmount();
      cleanup();
    }
  });

  it("renders real review records in dedicated ladder, breakout and seat views", () => {
    const { rerender } = render(<DistinctMarketWorkspace feature="连板梯队" data={overview} />);
    expect(screen.getByRole("region", { name: "连板高度与明细" })).toHaveTextContent("封板股");
    expect(screen.getByRole("region", { name: "连板高度与明细" })).toHaveTextContent("3板");

    rerender(<DistinctMarketWorkspace feature="放量突破" data={overview} />);
    expect(screen.getByRole("region", { name: "60 日放量突破清单" })).toHaveTextContent("突破股");
    expect(screen.getByRole("region", { name: "60 日放量突破清单" })).toHaveTextContent("2.50x");

    rerender(<DistinctMarketWorkspace feature="龙虎榜" data={overview} />);
    expect(screen.getByRole("region", { name: "龙虎榜股票与席位" })).toHaveTextContent("中际旭创");
    expect(screen.getByRole("region", { name: "龙虎榜股票与席位" })).toHaveTextContent("深股通专用");
  });

  it("mounts the real interval statistics workspace when its loader is available", () => {
    const loadIntervalReview = vi.fn().mockResolvedValue({
      requested_start_date: "2026-07-01",
      requested_end_date: "2026-07-29",
      start_date: null,
      end_date: null,
      observed_at: "2026-07-29T16:20:00+08:00",
      source: "unavailable",
      quality: "unavailable",
      universe_count: 0,
      valid_count: 0,
      rows: [],
      warnings: ["tdx_vipdoc_unavailable"],
      formula_version: "a-share-interval-review-v1",
    });

    render(<DistinctMarketWorkspace feature="区间统计" data={overview} loadIntervalReview={loadIntervalReview} />);

    expect(screen.getByRole("region", { name: "区间统计专属工作区" })).toHaveTextContent("真实区间统计");
    expect(screen.getByLabelText("起始日")).toBeInTheDocument();
  });
});
