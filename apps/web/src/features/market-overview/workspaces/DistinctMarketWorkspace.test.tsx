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
  it("uses the established flat menu name without changing the stable workspace key", () => {
    render(<DistinctMarketWorkspace feature="问财选股" data={overview} />);

    expect(screen.getByRole("heading", { name: "问财选股" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "条件选股" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "问财选股专属工作区" })).toBeInTheDocument();
  });

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
    expect(screen.getByRole("button", { name: /查看事件：算力需求增长/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("公开新闻摘要");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("600001");
    expect(screen.queryByRole("region", { name: "当日事项明细" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "日期口径与来源" })).toHaveClass("size-wide");
  });

  it("keeps the four anomaly pivot metrics on one desktop row", () => {
    render(<DistinctMarketWorkspace feature="异动统计大全" data={overview} />);

    const pivot = screen.getByRole("region", { name: "异动统计透视" }).querySelector(".statistics-pivot");
    expect(pivot).toHaveClass("statistics-pivot-four");
    expect(pivot?.children).toHaveLength(4);
  });

  it("keeps the first-board review compact and rounds derived values to at most two decimals", () => {
    const preciseOverview = {
      ...overview,
      review: {
        ...overview.review!,
        first_limit_up: [
          overview.review!.first_limit_up[0],
          {
            ...overview.review!.first_limit_up[0],
            symbol: "600006",
            name: "第二首板",
            change_percent: "11.444303797468358",
          },
        ],
      },
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="首板梯队" data={preciseOverview} />);

    const summary = screen.getByRole("region", { name: "首板分布仪表" });
    expect(summary.querySelector(".review-summary-grid")?.children).toHaveLength(4);
    expect(summary).toHaveTextContent("10.72%");
    expect(summary).not.toHaveTextContent("10.722151898734179%");
  });

  it("drills an exact review count into named stocks and exposes all research destinations", () => {
    const onOpenAShare = vi.fn();
    const onOpenCompanyResearch = vi.fn();
    const onOpenQuantAnalysis = vi.fn();
    render(<DistinctMarketWorkspace
      feature="首板梯队"
      data={overview}
      onOpenAShare={onOpenAShare}
      onOpenCompanyResearch={onOpenCompanyResearch}
      onOpenQuantAnalysis={onOpenQuantAnalysis}
    />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：首板数量 1" }));

    const detail = screen.getByRole("region", { name: "首板数量 明细" });
    expect(detail).toHaveTextContent("首板股");
    expect(detail).toHaveTextContent("600003");
    fireEvent.click(within(detail).getByRole("button", { name: "个股观察：600003 首板股" }));
    fireEvent.click(within(detail).getByRole("button", { name: "公司研究：600003 首板股" }));
    fireEvent.click(within(detail).getByRole("button", { name: "量化分析：600003 首板股" }));
    expect(onOpenAShare).toHaveBeenCalledWith("600003");
    expect(onOpenCompanyResearch).toHaveBeenCalledWith("600003");
    expect(onOpenQuantAnalysis).toHaveBeenCalledWith("600003");
  });

  it("turns the top key instrument into an exact named-stock filter", () => {
    const onOpenAShare = vi.fn();
    render(<DistinctMarketWorkspace feature="涨停板" data={overview} onOpenAShare={onOpenAShare} />);

    fireEvent.click(screen.getByRole("button", { name: "关键仪表：严格涨停 2" }));

    const detail = screen.getByRole("region", { name: "严格涨停 明细" });
    expect(detail).toHaveTextContent("全市场统计 2");
    expect(detail).toHaveTextContent("封板股");
    expect(detail).toHaveTextContent("600001");
    expect(detail).toHaveTextContent("非异动高热股");
    fireEvent.click(within(detail).getByRole("button", { name: "个股观察：600001 封板股" }));
    expect(onOpenAShare).toHaveBeenCalledWith("600001");
  });

  it("shows named clickable stocks instead of a bare code string in the theme atlas", () => {
    const onOpenAShare = vi.fn();
    render(<DistinctMarketWorkspace feature="题材库" data={overview} onOpenAShare={onOpenAShare} />);

    const atlas = screen.getByRole("region", { name: "题材索引库" });
    const stock = within(atlas).getAllByRole("button", { name: "查看 600001 封板股" })[0];
    expect(stock).toHaveTextContent("封板股");
    expect(stock).toHaveTextContent("600001");
    fireEvent.click(stock);
    expect(onOpenAShare).toHaveBeenCalledWith("600001");
  });

  it("drills a consecutive-board height into its exact named members", () => {
    render(<DistinctMarketWorkspace feature="连板表现" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：3 板 1" }));

    const detail = screen.getByRole("region", { name: "3 板 明细" });
    expect(detail).toHaveTextContent("封板股");
    expect(detail).toHaveTextContent("600001");
    expect(detail).toHaveTextContent("连续 3 个交易日收盘涨停");
  });

  it("drills a seat stock count into the exact named public-list members", () => {
    render(<DistinctMarketWorkspace feature="游资追踪" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：深股通专用涉及股票 1" }));

    const detail = screen.getByRole("region", { name: "深股通专用涉及股票 明细" });
    expect(detail).toHaveTextContent("中际旭创");
    expect(detail).toHaveTextContent("300308");
    expect(detail).toHaveTextContent("席位：深股通专用");
  });

  it("drills seat-direction counts into exact named stocks", () => {
    render(<DistinctMarketWorkspace feature="游资动向" data={overview} />);

    const direction = screen.getByRole("region", { name: "席位买卖方向分布" });
    fireEvent.click(within(direction).getByRole("button", { name: "筛选：净买入 1" }));

    const detail = screen.getByRole("region", { name: "净买入 明细" });
    expect(detail).toHaveTextContent("中际旭创");
    expect(detail).toHaveTextContent("300308");
  });

  it("shows event-calendar linked stocks as names plus codes and opens the stock", () => {
    const onOpenAShare = vi.fn();
    render(<DistinctMarketWorkspace feature="投资日历" data={overview} onOpenAShare={onOpenAShare} />);

    const detail = screen.getByRole("region", { name: "当前事件详情" });
    const stock = within(detail).getByRole("button", { name: "查看 600001 封板股" });
    expect(stock).toHaveTextContent("封板股");
    expect(stock).toHaveTextContent("600001");
    fireEvent.click(stock);
    expect(onOpenAShare).toHaveBeenCalledWith("600001");
  });

  it("resolves anomaly-linked codes to stock names in drill-down details", () => {
    render(<DistinctMarketWorkspace feature="异动统计大全" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：正向异动 1" }));

    const detail = screen.getByRole("region", { name: "正向异动 明细" });
    expect(detail).toHaveTextContent("封板股");
    expect(detail).toHaveTextContent("600001");
    expect(detail).toHaveTextContent("算力拉升");
  });

  it("does not pretend a full-market aggregate has exact member details", () => {
    render(<DistinctMarketWorkspace feature="复盘统计大全" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: `查看口径：上涨家数 ${overview.breadth.rising_count}` }));

    expect(screen.getByRole("region", { name: "上涨家数 明细" })).toHaveTextContent("当前接口仅返回全市场聚合值，暂无成员级明细");
  });

  it("shows names beside linked stock codes in news evidence", () => {
    render(<DistinctMarketWorkspace feature="热点解读" data={overview} />);

    const news = screen.getByRole("region", { name: "热点原始资讯" });
    expect(news).toHaveTextContent("封板股");
    expect(news).toHaveTextContent("600001");
  });

  it("drills limit-ecology totals into the currently loaded named members", () => {
    render(<DistinctMarketWorkspace feature="涨停板" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：已封涨停 2" }));

    const detail = screen.getByRole("region", { name: "已封涨停 明细" });
    expect(detail).toHaveTextContent("全市场统计 2");
    expect(detail).toHaveTextContent("当前已加载可钻取明细 2");
    expect(detail).toHaveTextContent("封板股");
    expect(detail).toHaveTextContent("600001");
    expect(detail).toHaveTextContent("非异动高热股");
    expect(detail).toHaveTextContent("300006");
  });

  it("drills opening metrics into the exact representative-stock filter", () => {
    render(<DistinctMarketWorkspace feature="开盘啦" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：高开 >= 2% 2" }));

    const detail = screen.getByRole("region", { name: "高开 >= 2% 明细" });
    expect(detail).toHaveTextContent("封板股");
    expect(detail).toHaveTextContent("非异动高热股");
    expect(detail).not.toHaveTextContent("低开股");
  });

  it("shows names and real stock navigation in anomaly timelines and evidence maps", () => {
    const onOpenAShare = vi.fn();
    const { rerender } = render(<DistinctMarketWorkspace feature="盘中异动" data={overview} onOpenAShare={onOpenAShare} />);

    const timeline = screen.getByRole("region", { name: "盘中异动时间线" });
    expect(timeline).toHaveTextContent("封板股");
    fireEvent.click(within(timeline).getByRole("button", { name: "查看 600001 封板股" }));
    expect(onOpenAShare).toHaveBeenCalledWith("600001");

    rerender(<DistinctMarketWorkspace feature="AI+题材" data={overview} onOpenAShare={onOpenAShare} />);
    const evidence = screen.getByRole("region", { name: "新闻到股票证据链" });
    expect(evidence).toHaveTextContent("封板股");
    fireEvent.click(within(evidence).getByRole("button", { name: "查看 600001 封板股" }));
    expect(onOpenAShare).toHaveBeenCalledTimes(2);
  });

  it("makes each seven-ranking winner a named stock entry instead of a dead code card", () => {
    const onOpenAShare = vi.fn();
    render(<DistinctMarketWorkspace feature="七大人气榜" data={overview} onOpenAShare={onOpenAShare} />);

    const rankings = screen.getByRole("region", { name: "七大人气榜单" });
    const winner = within(rankings).getAllByRole("link", { name: /查看 300006 非异动高热股/ })[0];
    fireEvent.click(winner);
    expect(onOpenAShare).toHaveBeenCalledWith("300006");
  });

  it("drills representative-stock distribution bins into their exact named members", () => {
    render(<DistinctMarketWorkspace feature="人气榜" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：人气分 80-100 1" }));

    const detail = screen.getByRole("region", { name: "人气分 80-100 明细" });
    expect(detail).toHaveTextContent("非异动高热股");
    expect(detail).not.toHaveTextContent("低开股");
  });

  it("drills promotion-funnel stages into exact named stock sets", () => {
    render(<DistinctMarketWorkspace feature="龙头晋级" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：当前封板 2" }));

    const detail = screen.getByRole("region", { name: "当前封板 明细" });
    expect(detail).toHaveTextContent("封板股");
    expect(detail).toHaveTextContent("非异动高热股");
  });

  it("makes review-column totals filterable and keeps each stock named", () => {
    render(<DistinctMarketWorkspace feature="涨停复盘啦" data={overview} />);

    fireEvent.click(screen.getByRole("button", { name: "筛选：封板 2" }));

    const detail = screen.getByRole("region", { name: "封板 明细" });
    expect(detail).toHaveTextContent("封板股");
    expect(detail).toHaveTextContent("非异动高热股");
  });

  it("replaces code-only industry links with stock names and navigation", () => {
    const onOpenAShare = vi.fn();
    render(<DistinctMarketWorkspace feature="非研产业库" data={overview} onOpenAShare={onOpenAShare} />);

    const map = screen.getByRole("region", { name: "A 股产业主题地图" });
    expect(map).toHaveTextContent("封板股");
    fireEvent.click(within(map).getAllByRole("link", { name: "查看 600001 封板股" })[0]);
    expect(onOpenAShare).toHaveBeenCalledWith("600001");
  });

  it("gives the seven-rank cross matrix and its audit separate full-width rows", () => {
    render(<DistinctMarketWorkspace feature="七大人气榜" data={overview} />);

    expect(screen.getByRole("region", { name: "重复上榜矩阵" }).closest("section")).toHaveClass("size-wide");
    expect(screen.getByRole("region", { name: "榜单口径说明" }).closest("section")).toHaveClass("size-wide");
  });

  it("stacks dense primary panels above compact audit or summary panels", () => {
    const cases = [
      ["AI+题材", ["新闻到股票证据链", "题材行情验证"]],
      ["隔夜单/抢筹", ["抢筹观察榜", "隔夜委托证据"]],
      ["竞价选股", ["规则通过候选", "竞价字段完整度"]],
      ["板块赛道", ["涨幅与广度矩阵", "赛道强弱分层"]],
      ["连板表现", ["连板历史覆盖", "当前强势候选"]],
      ["龙头晋级", ["晋级条件与阻断", "晋级失败信号"]],
      ["炸板", ["封板与炸板对照", "炸板风险分层"]],
      ["昨涨停", ["今日反馈分组", "可验证反馈明细"]],
      ["连板梯队", ["连板结构仪表", "日线覆盖与字段边界"]],
      ["首板梯队", ["首板分布仪表", "首板判定口径"]],
      ["放量突破", ["突破强度仪表", "放量突破规则"]],
      ["突破前高", ["前高突破仪表", "前高窗口与量能口径"]],
      ["低位放量", ["位置与量能仪表", "低位放量判定口径"]],
      ["龙虎榜", ["龙虎榜资金仪表", "榜单来源与缓存时效"]],
    ] as const;
    const { rerender } = render(<DistinctMarketWorkspace feature={cases[0][0]} data={overview} />);

    cases.forEach(([feature, panels], index) => {
      if (index > 0) rerender(<DistinctMarketWorkspace feature={feature} data={overview} />);
      panels.forEach((panel) => {
        expect(screen.getByRole("region", { name: panel }).closest("section")).toHaveClass("size-wide");
      });
    });
  });

  it("keeps paired dense hotspot evidence panels together after moving the short news list above them", () => {
    render(<DistinctMarketWorkspace feature="热点解读" data={overview} />);

    expect(screen.getByRole("region", { name: "热点原始资讯" }).closest("section")).toHaveClass("size-wide");
    expect(screen.getByRole("region", { name: "热点题材归因" }).closest("section")).toHaveClass("size-half");
    expect(screen.getByRole("region", { name: "行情一致性验证" }).closest("section")).toHaveClass("size-half");
  });

  it("stacks the stock anomaly ranking above its longer news evidence list", () => {
    render(<DistinctMarketWorkspace feature="个股异动" data={overview} />);

    const ranking = screen.getByRole("region", { name: "个股异动榜" }).closest("section");
    const news = screen.getByRole("region", { name: "个股异动解释线索" }).closest("section");
    expect(ranking).not.toBeNull();
    expect(news).not.toBeNull();
    expect(ranking).toHaveClass("size-wide");
    expect(news).toHaveClass("size-wide");
    expect(ranking && news ? ranking.compareDocumentPosition(news) & Node.DOCUMENT_POSITION_FOLLOWING : 0).toBeTruthy();
  });

  it("places the auction strength board first and pairs only the two compact supporting panels", () => {
    render(<DistinctMarketWorkspace feature="竞价封单" data={overview} />);

    const panels = screen.getAllByRole("region").filter((region) => region.closest("section")?.classList.contains("distinct-block"));
    expect(panels.map((panel) => panel.getAttribute("aria-label"))).toEqual([
      "开盘强度对照", "竞价封板状态梯", "封单字段审计", "竞价强势股票",
    ]);
    expect(screen.getByRole("region", { name: "开盘强度对照" }).closest("section")).toHaveClass("size-wide");
    expect(screen.getByRole("region", { name: "竞价封板状态梯" }).closest("section")).toHaveClass("size-half");
    expect(screen.getByRole("region", { name: "封单字段审计" }).closest("section")).toHaveClass("size-half");
  });

  it("shows official investment dates separately from news timestamps", () => {
    const withOfficialCalendar = {
      ...overview,
      official_events: [{
        event_id: "732001-listing-2026-08-06", event_date: "2026-08-06",
        event_type: "listing" as const, code: "732001", name: "测试新股",
        kind: "新股申购", observed_at: "2026-07-29T10:30:00+08:00",
        source: "tdx-local-rpc", quality: "ready" as const,
      }],
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="投资日历" data={withOfficialCalendar} />);

    const event = screen.getByRole("button", { name: "查看事件：测试新股 上市日" });
    expect(event).toHaveTextContent("官方事项日期");
    fireEvent.click(event);
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("通达信官方事项日期");
    expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("732001");
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

  it("distinguishes live quote date from a stale historical review date", () => {
    const staleHistory = {
      ...overview,
      as_of: "2026-08-07",
      market_data: {
        ...overview.market_data,
        observed_at: "2026-08-07T16:15:00+08:00",
        freshness: "final" as const,
      },
      review: {
        ...overview.review!,
        latest_trade_date: "2026-07-17",
      },
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="板块资金动图" data={staleHistory} />);

    expect(screen.getByText("历史日线最新交易日")).toBeInTheDocument();
    expect(screen.getByText("2026-07-17")).toBeInTheDocument();
    expect(screen.getAllByText(/历史日线待补齐/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/实时行情 2026-08-07/)).toBeInTheDocument();
  });

  it("labels full-market aggregates separately from representative stock and strong-sector samples", () => {
    const scoped = {
      ...overview,
      data_scope: {
        market_aggregate: "full_a_share_market" as const,
        market_quote_count: 5197,
        market_universe_count: 5198,
        stock_sample: "representative" as const,
        stock_sample_count: 293,
        sector_sample: "strong_sector" as const,
        sector_sample_count: 12,
      },
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="板块精选" data={scoped} />);

    expect(screen.getByText("A 股全市场聚合")).toBeInTheDocument();
    expect(screen.getByText("5,197 / 5,198 只行情")).toBeInTheDocument();
    expect(screen.getByText("293 只代表股票样本")).toBeInTheDocument();
    expect(screen.getByText("12 个强势板块样本")).toBeInTheDocument();
  });

  it("explains fragmented history without presenting a sparse outlier as the market date", () => {
    const fragmented = {
      ...overview,
      as_of: "2026-08-07",
      review: {
        ...overview.review!,
        latest_trade_date: "2026-07-29",
        latest_available_trade_date: "2026-08-07",
        latest_available_trade_date_count: 5,
        latest_trade_date_coverage_percent: "98.1",
        expected_trade_date: "2026-08-07",
        refresh_required: true,
        refresh_reason: "历史日线覆盖日期分散，不能代表查询日期全市场",
        warnings: ["history_dates_fragmented", "history_latest_outlier"],
      },
    } as unknown as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="板块资金动图" data={fragmented} />);

    expect(screen.getByText("主导历史交易日")).toBeInTheDocument();
    expect(screen.getAllByText("2026-07-29").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/最新零散记录 2026-08-07/)).toBeInTheDocument();
    expect(screen.getByText(/仅 5 只/)).toBeInTheDocument();
    expect(screen.getByText(/覆盖率 98.1%/)).toBeInTheDocument();
    expect(screen.getByText("查询日期")).toBeInTheDocument();
    expect(screen.getByText("2026-08-07")).toBeInTheDocument();
    expect(screen.getByText("快照生成时间")).toBeInTheDocument();
    expect(screen.getByText(/历史日线覆盖日期分散/)).toBeInTheDocument();
  });

  it("uses a full row for the sector flow audit and keeps stock dossier evidence compact", () => {
    const { rerender } = render(<DistinctMarketWorkspace feature="板块资金动图" data={overview} />);
    expect(screen.getByRole("region", { name: "板块资金字段审计" }).closest("section")).toHaveClass("size-wide");
    expect(screen.getByRole("region", { name: "资金动图口径" }).closest("section")).toHaveClass("size-wide");

    rerender(<DistinctMarketWorkspace feature="个股详情" data={overview} />);
    expect(screen.getByRole("region", { name: "个股实时档案" }).closest("section")).toHaveClass("size-wide");
    expect(screen.getByRole("region", { name: "个股证据链" }).closest("section")).toHaveClass("size-half");
    expect(screen.getByRole("region", { name: "个股状态提醒" }).closest("section")).toHaveClass("size-half");
  });

  it("renders cached real large-order direction instead of a turnover proxy", () => {
    const withLargeOrders = {
      ...overview,
      data_scope: {
        market_aggregate: "full_a_share_market" as const,
        market_quote_count: 5000,
        market_universe_count: 5200,
        stock_sample: "representative" as const,
        stock_sample_count: 4,
        sector_sample: "strong_sector" as const,
        sector_sample_count: 1,
        large_order_sample_count: 1,
      },
      large_order_flows: [{
        symbol: "600001", name: "封板股", latest_trade_date: "2026-07-29",
        observed_at: "2026-07-29T10:30:00+08:00", main_net_yi: "2.80",
        large_net_yi: "1.50", super_net_yi: "1.30", direction: "inflow" as const,
        source: "eastmoney-fund-flow", quality: "ready" as const,
      }],
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="主力大单监控" data={withLargeOrders} />);

    const panel = screen.getByRole("region", { name: "主力大单字段审计" });
    expect(panel).toHaveTextContent("封板股");
    expect(panel).toHaveTextContent("大单 +1.50亿");
    expect(panel).toHaveTextContent("超大单 +1.30亿");
    expect(panel).toHaveTextContent("真实资金流缓存样本 1 只");
    expect(panel).not.toHaveTextContent("当前接口未提供真实大单净流入");
  });

  it("renders real sector fund-flow snapshots instead of a sector turnover proxy", () => {
    const withSectorFlow = {
      ...overview,
      data_scope: {
        market_aggregate: "full_a_share_market" as const,
        market_quote_count: 5000,
        market_universe_count: 5200,
        stock_sample: "representative" as const,
        stock_sample_count: 4,
        sector_sample: "strong_sector" as const,
        sector_sample_count: 1,
        sector_fund_flow_sample_count: 2,
        sector_fund_flow_snapshot_count: 2,
      },
      sector_fund_flow: [
        { sector_code: "BK1036", sector_name: "人工智能", observed_at: "2026-07-29T10:29:00+08:00", main_net_yi: "20.00", large_net_yi: "9.00", super_net_yi: "11.00", source: "eastmoney-sector-fund-flow", quality: "ready" as const },
        { sector_code: "BK1036", sector_name: "人工智能", observed_at: "2026-07-29T10:30:00+08:00", main_net_yi: "23.80", large_net_yi: "10.80", super_net_yi: "13.00", source: "eastmoney-sector-fund-flow", quality: "ready" as const },
        { sector_code: "BK0475", sector_name: "银行", observed_at: "2026-07-29T10:29:00+08:00", main_net_yi: "-8.00", large_net_yi: "-4.00", super_net_yi: "-4.00", source: "eastmoney-sector-fund-flow", quality: "ready" as const },
        { sector_code: "BK0475", sector_name: "银行", observed_at: "2026-07-29T10:30:00+08:00", main_net_yi: "-9.60", large_net_yi: "-5.40", super_net_yi: "-4.20", source: "eastmoney-sector-fund-flow", quality: "ready" as const },
      ],
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="板块资金动图" data={withSectorFlow} />);

    const panel = screen.getByRole("region", { name: "板块资金字段审计" });
    expect(panel).toHaveTextContent("人工智能");
    expect(panel).toHaveTextContent("+23.80亿");
    expect(panel).toHaveTextContent("银行");
    expect(panel).toHaveTextContent("-9.60亿");
    expect(panel).toHaveTextContent("2 个板块 · 2 次真实采样");
    expect(panel).not.toHaveTextContent("当前接口未提供板块真实资金流");
    expect(within(panel).getByRole("img", { name: "板块主力净流入时间序列" })).toBeInTheDocument();
    const sectorCards = panel.querySelectorAll(".sector-fund-flow-latest article");
    expect(sectorCards).toHaveLength(2);
    expect(sectorCards[0]).toHaveAttribute("data-sector-color");
    expect(sectorCards[1]).toHaveAttribute("data-sector-color");
    expect(sectorCards[0].getAttribute("data-sector-color")).not.toBe(sectorCards[1].getAttribute("data-sector-color"));
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

  it("renders visual ecology meters and breakout strength instead of only numeric tables", () => {
    render(<DistinctMarketWorkspace feature="涨停板" data={overview} />);

    expect(screen.getByTestId("limit-ecology-meter-sealed")).toHaveAttribute("aria-label", "已封涨停占触板比例");
    expect(screen.getByText("红涨绿跌：红色为上涨/改善，绿色为下跌/风险")).toBeInTheDocument();

    render(<DistinctMarketWorkspace feature="放量突破" data={overview} />);
    expect(screen.getByTestId("breakout-strength-meter")).toHaveAttribute("aria-label", "放量突破强度");
    expect(screen.getByText("量能倍数越高，突破证据越强")).toBeInTheDocument();

    expect(screen.getByTestId("breakout-strength-meter")).toHaveAttribute("aria-label", "放量突破强度");
  });

  it("renders a verified buy-sell flow bar for public dragon-tiger records", () => {
    render(<DistinctMarketWorkspace feature="龙虎榜" data={overview} />);

    expect(screen.getByTestId("dragon-tiger-flow-meter")).toHaveAttribute("aria-label", "龙虎榜买入卖出对照");
    expect(screen.getByText("买入 / 卖出对照")).toBeInTheDocument();
    expect(screen.getByText("只使用公开席位买卖金额")).toBeInTheDocument();
  });

  it("switches a no-variance sector quadrant to a readable strength ranking", () => {
    const narrowSectorSample = {
      ...overview,
      sectors: [
        { sector_id: "s1", name: "先进封装", change_percent: "15.9", amount_yi: "220", limit_up_count: 2, rising_count: 3, falling_count: 0, stock_count: 3 },
        { sector_id: "s2", name: "创新药", change_percent: "15.0", amount_yi: "180", limit_up_count: 2, rising_count: 4, falling_count: 0, stock_count: 4 },
      ],
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="板块赛道" data={narrowSectorSample} />);

    expect(screen.getByTestId("sector-ranked-bars")).toBeInTheDocument();
    expect(screen.getByText("样本上涨占比缺少区分度，改用强度排序")).toBeInTheDocument();
    expect(screen.queryByTestId("sector-quadrant")).not.toBeInTheDocument();
  });

  it("renders readable sector decision quadrants instead of numbered scatter points", () => {
    const variedSectorSample = {
      ...overview,
      sectors: [
        { sector_id: "s1", name: "先进封装", change_percent: "8.2", amount_yi: "220", limit_up_count: 3, rising_count: 18, falling_count: 2, stock_count: 20 },
        { sector_id: "s2", name: "创新药", change_percent: "4.1", amount_yi: "180", limit_up_count: 1, rising_count: 12, falling_count: 8, stock_count: 20 },
        { sector_id: "s3", name: "软件服务", change_percent: "1.2", amount_yi: "160", limit_up_count: 0, rising_count: 8, falling_count: 12, stock_count: 20 },
        { sector_id: "s4", name: "汽车", change_percent: "-1.1", amount_yi: "130", limit_up_count: 0, rising_count: 4, falling_count: 16, stock_count: 20 },
      ],
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="板块赛道" data={variedSectorSample} />);

    expect(screen.getByTestId("sector-decision-quadrants")).toHaveTextContent("赛道领涨");
    expect(screen.getByTestId("sector-decision-quadrants")).toHaveTextContent("先进封装");
    expect(screen.getByTestId("sector-decision-quadrants")).toHaveTextContent("广度 90.0%");
    expect(screen.queryByTestId("sector-quadrant")).not.toBeInTheDocument();
  });

  it("replaces saturated strength dots with readable decision quadrants", () => {
    const saturatedSectorSample = {
      ...overview,
      sectors: [
        { sector_id: "s1", name: "机器人概念", change_percent: "16.0", amount_yi: "220", limit_up_count: 3, rising_count: 20, falling_count: 0, stock_count: 20 },
        { sector_id: "s2", name: "业绩预增", change_percent: "14.0", amount_yi: "180", limit_up_count: 1, rising_count: 18, falling_count: 2, stock_count: 20 },
        { sector_id: "s3", name: "创新药", change_percent: "11.0", amount_yi: "160", limit_up_count: 2, rising_count: 14, falling_count: 6, stock_count: 20 },
        { sector_id: "s4", name: "软件服务", change_percent: "11.0", amount_yi: "130", limit_up_count: 0, rising_count: 11, falling_count: 9, stock_count: 20 },
      ],
    } as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="板块精选" data={saturatedSectorSample} />);

    const matrix = screen.getByTestId("sector-decision-quadrants");
    expect(matrix).toHaveTextContent("主线扩散");
    expect(matrix).toHaveTextContent("核心抱团");
    expect(matrix).toHaveTextContent("普涨偏弱");
    expect(matrix).toHaveTextContent("弱势收缩");
    expect(matrix).toHaveTextContent("机器人概念");
    expect(matrix).toHaveTextContent("广度 100.0%");
    expect(matrix).toHaveTextContent("涨停 3");
    expect(screen.queryByTestId("sector-quadrant")).not.toBeInTheDocument();
    expect(matrix).not.toHaveTextContent("强度 100.0");
    expect(matrix).not.toHaveTextContent("100.0 100.0");
  });

  it("uses dedicated quadrant meanings for sector race and strength wind", () => {
    const sample = {
      ...overview,
      sectors: [
        { sector_id: "s1", name: "先进封装", change_percent: "8.2", amount_yi: "220", limit_up_count: 3, rising_count: 18, falling_count: 2, stock_count: 20 },
        { sector_id: "s2", name: "创新药", change_percent: "4.1", amount_yi: "180", limit_up_count: 1, rising_count: 12, falling_count: 8, stock_count: 20 },
        { sector_id: "s3", name: "软件服务", change_percent: "1.2", amount_yi: "160", limit_up_count: 0, rising_count: 8, falling_count: 12, stock_count: 20 },
        { sector_id: "s4", name: "汽车", change_percent: "-1.1", amount_yi: "130", limit_up_count: 0, rising_count: 4, falling_count: 16, stock_count: 20 },
      ],
    } as MarketOverviewResponse;

    const view = render(<DistinctMarketWorkspace feature="板块赛道" data={sample} />);
    expect(screen.getByTestId("sector-decision-quadrants")).toHaveTextContent("赛道领涨");
    expect(screen.getByTestId("sector-decision-quadrants")).toHaveTextContent("局部抱团");

    view.rerender(<DistinctMarketWorkspace feature="强度风口" data={sample} />);
    expect(screen.getByTestId("sector-decision-quadrants")).toHaveTextContent("涨停扩散");
    expect(screen.getByTestId("sector-decision-quadrants")).toHaveTextContent("龙头集中");
    expect(screen.getByTestId("sector-decision-quadrants")).toHaveTextContent("涨停密度");
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

  it("collapses an evidence map when no news-to-theme-to-stock edge is verifiable", () => {
    const noEdges = {
      ...overview,
      anomalies: [],
      live_feed: [{ event_id: "orphan", occurred_at: "2026-07-29T10:25:00+08:00", headline: "未关联信息", summary: "无股票代码", themes: ["未关联题材"], symbols: [], source: "未知来源", review_state: "pending" }],
      sectors: [],
      sector_stocks: {},
    } as unknown as MarketOverviewResponse;

    render(<DistinctMarketWorkspace feature="热点解读" data={noEdges} />);

    const chain = screen.getByRole("region", { name: "热点证据链" });
    expect(chain).toHaveTextContent("当前没有可验证记录");
    expect(chain).toHaveTextContent("没有同时具备资讯、题材和 A 股关联");
    expect(chain.querySelector(".evidence-map")).toBeNull();
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
  }, 15_000);

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
