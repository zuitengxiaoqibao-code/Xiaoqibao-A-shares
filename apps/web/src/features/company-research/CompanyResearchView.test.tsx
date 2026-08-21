import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { writeDailySnapshot } from "../../shared/dailySnapshotCache";
import type { LoadProgressCallback } from "../../shared/fetchJsonWithProgress";
import { CompanyResearchView } from "./CompanyResearchView";
import type { CompanyResearchResponse } from "./types";

const dimensions = [
  ["industry_space", "行业空间", "unavailable", null], ["business_model", "商业模式", "unavailable", null],
  ["growth", "增长质量", "ready", "82"], ["profitability", "盈利能力", "ready", "75"],
  ["cash_flow", "现金流质量", "ready", "70"], ["balance_sheet", "资产负债质量", "ready", "78"],
  ["moat", "竞争壁垒", "unavailable", null], ["valuation", "估值吸引力", "ready", "66"],
  ["catalysts", "未来催化", "unavailable", null],
].map(([key, label, status, score], index) => ({
  key, label, weight: index === 2 || index === 4 || index === 7 ? 15 : index === 8 ? 5 : 10,
  status, score, summary: `${label}证据说明`, metrics: {}, evidence_ids: [],
  reason: status === "unavailable" ? "只展示真实原文，不自动评分。" : null,
})) as CompanyResearchResponse["dimensions"];

const research: CompanyResearchResponse = {
  status: "partial", symbol: "600519", name: "贵州茅台", as_of: "2026-08-01",
  generated_at: "2026-08-03T10:00:00+08:00", dimensions, evidence_coverage: "0.65",
  base_score: "74", risk_penalty: "3", final_score: "71",
  field_evidence: [{
    field_path: "final_score", value: "71", source: "sina-finance / tencent", source_field: null,
    status: "derived", trade_date: "2026-08-01", observed_at: "2026-08-03T10:00:00+08:00",
    coverage_percent: "65", derived: true, formula: "base_score - risk_penalty", evidence_ids: [], limitations: [],
  }],
  financial_history: {
    status: "ready", source: "sina-finance", observed_at: "2026-08-01T15:00:00+08:00", reasons: [],
    revenue_cagr_3y: "0.15", net_profit_cagr_3y: "0.18", latest_period: null, periods: [],
    annual_periods: [{ period: "2025-12-31", revenue: "120000000000", revenue_yoy: "0.12", operating_cost: "100", net_profit: "60000000000", net_profit_yoy: "0.15", operating_cash_flow: "65000000000", total_assets: "200000000000", total_liabilities: "40000000000", total_equity: "160000000000", gross_margin: "0.91", cash_to_profit: "1.08", debt_ratio: "0.20" }],
  },
  valuation: { status: "ready", pe_ttm: "25", pb: "8", market_cap_yi: "19000", peer_pe_median: null, peer_pb_median: null, forward_eps_median: null, forward_eps_sample_count: 0, forward_pe: null, forward_pe_status: "unavailable", forward_pe_reason: "没有可用预测。", observation_range_status: "unavailable", observation_range_reason: "缺少历史估值序列，不计算价格区间。", source: "tencent", observed_at: "2026-08-01T15:00:00+08:00" },
  counter_case: Array.from({ length: 10 }, (_, index) => ({ key: `risk-${index}`, title: `反方检查${index + 1}`, status: index === 0 ? "triggered" : "clear", detail: "按真实财务字段核验。", threshold: "公开规则", penalty: index === 0 ? "3" : "0", evidence_ids: [] })),
  profile: { status: "ready", company_overview: "公司概况原文", industry_analysis: "行业分析原文", latest_tips: "最新提示原文", source: "mootdx-f10", observed_at: "2026-08-01T15:00:00+08:00", reasons: [] },
  sources: [{ source: "sina-finance", label: "多年财报三表", status: "ready", observed_at: "2026-08-01T15:00:00+08:00", detail: "按报告期归一化。" }],
  reasons: [],
};

const refreshedResearch: CompanyResearchResponse = {
  ...research,
  name: "贵州茅台（最新）",
  generated_at: "2026-08-03T13:30:00+08:00",
  final_score: "76",
};

const evidenceResearch = {
  ...research,
  enrichment: {
    status: "ready", observed_at: "2026-08-03T10:00:00+08:00",
    stock_reports: [], industry_reports: [], peer_candidates: [],
    unlocks: [{ free_date: "2026-09-01", stock_type: "首发限售", shares: "100000000", ratio_percent: "6.5" }],
    margin: [], holders: [], sources: ["eastmoney-datacenter"], reasons: [],
  },
  profile: {
    ...research.profile,
    latest_tip_items: [
      { id: "notice-1", category: "公告与合同", title: "公告与合同", date: "2026-08-05", tone: "positive", summary: "签署战略合作协议", source: "mootdx-f10", observed_at: research.profile.observed_at, raw_text: "●最新公告：2026-08-05 签署战略合作协议" },
      { id: "risk-1", category: "风险提醒", title: "风险提醒", date: "2026-07-15", tone: "risk", summary: "预计净利润同比下降", source: "mootdx-f10", observed_at: research.profile.observed_at, raw_text: "●业绩预告：2026-07-15 预计净利润同比下降" },
      { id: "neutral-1", category: "交易异动", title: "交易异动", date: "2026-07-10", tone: "neutral", summary: "股票交易出现异动", source: "mootdx-f10", observed_at: research.profile.observed_at, raw_text: "●交易异动：2026-07-10 股票交易出现异动" },
      { id: "neutral-2", category: "其他", title: "年报已披露", date: "2026-06-30", tone: "neutral", summary: "年报已披露", source: "mootdx-f10", observed_at: research.profile.observed_at, raw_text: "2026-06-30 年报已披露" },
      { id: "risk-2", category: "风险提醒", title: "减持风险", date: "2026-06-20", tone: "risk", summary: "股东减持计划待核验", source: "mootdx-f10", observed_at: research.profile.observed_at, raw_text: "●风险提示：2026-06-20 股东减持计划待核验" },
    ],
  },
} as unknown as CompanyResearchResponse;

describe("CompanyResearchView", () => {
  beforeEach(() => localStorage.clear());

  it("renders the evidence gauges, nine dimensions and ten counter-case checks", async () => {
    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => research)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    const gauges = await screen.findByRole("region", { name: "公司研究核心仪表" });
    expect(gauges).toHaveTextContent("研究分");
    expect(gauges).toHaveTextContent("证据覆盖度");
    expect(gauges).toHaveTextContent("风险压力");
    expect(screen.getByRole("region", { name: "九维公司研究矩阵" }).querySelectorAll(".dimension-row")).toHaveLength(9);
    expect(screen.getByRole("region", { name: "逻辑失效条件" }).querySelectorAll(".counter-item")).toHaveLength(10);
    expect(screen.getByRole("group", { name: "关键字段证据" })).toHaveTextContent("1 项推算");
  });

  it("shows forward valuation confidence and never turns thin EPS samples into a forward PE", async () => {
    const thinConsensus = {
      ...research,
      valuation: {
        ...research.valuation,
        forward_eps_median: "2.25", forward_eps_sample_count: 2,
        forward_pe: null, forward_pe_status: "low_confidence" as const,
        forward_pe_reason: "仅有 2 家不同机构预测，少于 3 家，不计算前向 PE。",
      },
    };
    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => thinConsensus)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    const valuation = await screen.findByRole("region", { name: "估值观察" });
    expect(valuation).toHaveTextContent("明年 EPS 中位2.25");
    expect(valuation).toHaveTextContent("前向 PE--");
    expect(valuation).toHaveTextContent("低可信");
    expect(valuation).toHaveTextContent("少于 3 家");
  });

  it("renders a dense financial visual overview with real-period labels", async () => {
    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => research)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    const overview = await screen.findByRole("region", { name: "财务可视化总览" });
    expect(overview).toHaveTextContent("资本结构");
    expect(overview).toHaveTextContent("资产负债构成");
    expect(overview).toHaveTextContent("多年财务趋势");
    expect(overview).toHaveTextContent("综合能力剖面");
    expect(overview).toHaveTextContent("2025-12-31");
    expect(overview.querySelectorAll(".research-visual-card")).toHaveLength(6);
    expect(screen.getByRole("img", { name: "当前估值与同行中位双轴图" })).toBeInTheDocument();
    expect(overview.querySelectorAll(".research-capital-donut")).toHaveLength(2);
    expect(overview.querySelector(".research-trend-combo")).toBeTruthy();
  });

  it("does not turn missing or imbalanced capital fields into fake percentages", async () => {
    const incomplete = {
      ...research,
      financial_history: {
        ...research.financial_history,
        latest_period: {
          ...research.financial_history.annual_periods[0],
          total_liabilities: null,
          total_equity: "155000000000",
        },
      },
    } as CompanyResearchResponse;
    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => incomplete)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    const overview = await screen.findByRole("region", { name: "财务可视化总览" });
    expect(overview).toHaveTextContent("资本结构数据不足");
    expect(overview).toHaveTextContent("构成待核验");
    expect(overview).not.toHaveTextContent("0.0%负债率");
  });

  it("makes unverifiable dimensions explicit and avoids directive language", async () => {
    const { container } = render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => research)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    expect(await screen.findAllByText(/未评分/)).not.toHaveLength(0);
    expect(container).not.toHaveTextContent(/买入|卖出|目标价/);
    expect(screen.getByRole("region", { name: "F10原文证据" })).toHaveTextContent("公司概况原文");
    expect(screen.getByRole("region", { name: "研究来源账本" })).toHaveTextContent("多年财报三表");
  });

  it("marks unscored dimension bars as unavailable instead of rendering a zero score", async () => {
    const incomplete = {
      ...research,
      dimensions: research.dimensions.map((item, index) => index === 0 ? { ...item, score: null, status: "unavailable", reason: "缺少可核验字段" } : item),
    } as CompanyResearchResponse;
    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => incomplete)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);
    const row = (await screen.findAllByText(incomplete.dimensions[0].label)).map((item) => item.closest("article")).find((item) => item?.classList.contains("dimension-row"));
    expect(row).toHaveAttribute("data-state", "unavailable");
    expect(row?.querySelector(".research-meter")).toHaveAttribute("data-state", "unavailable");
  });

  it("shows today's complete cache while refreshing and replaces it with the latest result", async () => {
    writeDailySnapshot("company-research", "600519", research, new Date());
    let finish!: (value: CompanyResearchResponse) => void;
    const pending = new Promise<CompanyResearchResponse>((resolve) => { finish = resolve; });
    const load = vi.fn(async (
      _symbol: string,
      _asOf?: string,
      _signal?: AbortSignal,
      onProgress?: LoadProgressCallback,
    ) => {
      onProgress?.({ percent: 42, stage: "receiving", detail: "已接收 4096 字节" });
      return pending;
    });

    render(<CompanyResearchView
      selectedSymbol="600519"
      load={load}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    expect(await screen.findByRole("region", { name: "公司研究摘要" })).toHaveTextContent("贵州茅台");
    const status = screen.getByRole("status", { name: "公司研究数据刷新状态" });
    expect(status).toHaveTextContent("正在载入最新数据，当前先展示当日缓存");
    expect(status).toHaveTextContent("缓存时间：");
    expect(screen.getByRole("progressbar", { name: "公司研究最新数据加载进度" })).toHaveAttribute("aria-valuenow", "42");

    finish(refreshedResearch);
    await waitFor(() => expect(screen.getByRole("region", { name: "公司研究摘要" })).toHaveTextContent("贵州茅台（最新）"));
    await waitFor(() => expect(status).toHaveTextContent("已加载实时最新数据"));
    expect(status).toHaveTextContent("当前状态：实时监控中");
    expect(screen.getByRole("region", { name: "公司研究核心仪表" })).toHaveTextContent("76.0");
  });

  it("keeps today's complete cache when the latest refresh fails", async () => {
    writeDailySnapshot("company-research", "600519", research, new Date());
    const load = vi.fn(async (
      _symbol: string,
      _asOf?: string,
      _signal?: AbortSignal,
      onProgress?: LoadProgressCallback,
    ) => {
      onProgress?.({ percent: 18, stage: "receiving", detail: "已接收 512 字节" });
      throw new Error("本地财务源暂时不可用");
    });

    render(<CompanyResearchView
      selectedSymbol="600519"
      load={load}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    expect(await screen.findByRole("region", { name: "公司研究摘要" })).toHaveTextContent("贵州茅台");
    const status = await screen.findByRole("status", { name: "公司研究数据刷新状态" });
    await waitFor(() => expect(status).toHaveTextContent("最新数据更新失败，继续显示当日缓存"));
    expect(status).toHaveTextContent("本地财务源暂时不可用");
    expect(screen.queryByText("600519 研究数据不可用")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "九维公司研究矩阵" })).toBeInTheDocument();
  });

  it("keeps a more complete cached research result when refresh coverage degrades", async () => {
    const complete = { ...research, status: "ready" as const, evidence_coverage: "0.95" };
    const degraded = {
      ...refreshedResearch,
      status: "partial" as const,
      name: "不应覆盖的部分结果",
      evidence_coverage: "0.20",
      reasons: ["财务与估值来源本次未返回"],
    };
    writeDailySnapshot("company-research", "600519", complete, new Date());

    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => degraded)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    expect(await screen.findByRole("region", { name: "公司研究摘要" })).toHaveTextContent("贵州茅台");
    await waitFor(() => expect(screen.getByRole("status", { name: "公司研究数据刷新状态" })).toHaveTextContent("新数据覆盖率较低"));
    expect(screen.queryByText("不应覆盖的部分结果")).not.toBeInTheDocument();
  });

  it("refreshes the active company research entry periodically while the page is visible", async () => {
    vi.useFakeTimers();
    try {
      const load = vi.fn(async () => research);
      render(<CompanyResearchView
        selectedSymbol="600519"
        load={load}
        search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
      />);
      await act(async () => { await Promise.resolve(); await Promise.resolve(); });
      expect(load).toHaveBeenCalledTimes(1);
      await act(async () => { await vi.advanceTimersByTimeAsync(300_000); });
      expect(load).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not replace an in-flight company research request during periodic refresh", async () => {
    vi.useFakeTimers();
    try {
      let requestSignal: AbortSignal | undefined;
      const load = vi.fn((_symbol: string, _asOf?: string, signal?: AbortSignal) => {
        requestSignal = signal;
        return new Promise<CompanyResearchResponse>(() => undefined);
      });
      const { unmount } = render(<CompanyResearchView
        selectedSymbol="301526"
        load={load}
        search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
      />);

      await act(async () => { await Promise.resolve(); });
      expect(load).toHaveBeenCalledTimes(1);
      await act(async () => { await vi.advanceTimersByTimeAsync(300_000); });
      expect(load).toHaveBeenCalledTimes(1);
      expect(requestSignal?.aborted).toBe(false);
      unmount();
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not expose an English abort message when company research cannot load", async () => {
    render(<CompanyResearchView
      selectedSymbol="301526"
      load={vi.fn(async () => { throw new Error("signal is aborted without reason"); })}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    expect((await screen.findAllByText("公司研究数据暂不可用，请稍后重试。")).length).toBeGreaterThan(0);
    expect(screen.queryByText(/signal is aborted without reason/i)).not.toBeInTheDocument();
  });

  it("shows today's loaded research and lets the user open it again", async () => {
    writeDailySnapshot("company-research", "600519", research, new Date());
    const load = vi.fn(async () => refreshedResearch);

    render(<CompanyResearchView
      load={load}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    const history = screen.getByRole("region", { name: "今日已加载研究" });
    expect(history).toHaveTextContent("贵州茅台");
    fireEvent.click(screen.getByRole("button", { name: /贵州茅台.*600519/ }));
    expect(await screen.findByRole("region", { name: "公司研究摘要" })).toHaveTextContent("贵州茅台");
    expect(load).toHaveBeenCalledWith("600519", undefined, expect.any(AbortSignal), expect.any(Function));
  });

  it("places the stock cockpit link immediately before the research time", async () => {
    const openAShare = vi.fn();
    render(<CompanyResearchView
      selectedSymbol="600519"
      onOpenAShare={openAShare}
      load={vi.fn(async () => research)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    const link = await screen.findByRole("button", { name: "打开个股观察" });
    const researchTime = screen.getByText("研究时间").closest("div");
    expect(link.parentElement).toBe(researchTime?.parentElement);
    expect(link.nextElementSibling).toBe(researchTime);
    fireEvent.click(link);
    expect(openAShare).toHaveBeenCalledWith("600519");
  });

  it("publishes a company selected from search to the shared stock state", async () => {
    const onSelectSymbol = vi.fn();
    render(<CompanyResearchView
      load={vi.fn(async () => research)}
      search={vi.fn(async (query) => ({
        query,
        items: [{
          symbol: "600519", name: "贵州茅台", exchange: "sh" as const,
          observed_at: "2026-08-06T10:00:00+08:00", quote_quality: "ready" as const,
        }],
        server_time: "2026-08-06T10:00:00+08:00",
        source_status: "ready" as const,
      }))}
      onSelectSymbol={onSelectSymbol}
    />);

    fireEvent.change(screen.getByLabelText("股票代码或名称"), { target: { value: "贵州茅台" } });
    fireEvent.click(screen.getByRole("button", { name: "查询" }));

    await waitFor(() => expect(onSelectSymbol).toHaveBeenCalledWith("600519"));
  });

  it("uses the shared terminal theme shell", async () => {
    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => research)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    expect(await screen.findByRole("main")).toHaveClass("terminal-page", "company-research-page");
  });

  it("renders structured evidence as a summary, filterable cards and expandable raw text", async () => {
    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => evidenceResearch)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    const evidence = await screen.findByRole("region", { name: "催化与最新提示" });
    expect(evidence).toHaveTextContent("重点结论");
    expect(evidence).toHaveTextContent("重点风险：高比例限售股解禁");
    expect(evidence).toHaveTextContent("预计净利润同比下降");
    expect(evidence).toHaveTextContent("高比例限售股解禁");
    expect(evidence).toHaveTextContent("发生了什么");
    expect(evidence).toHaveTextContent("影响判断");
    expect(evidence).toHaveTextContent("后续观察");
    expect(evidence.querySelectorAll(".evidence-event")).toHaveLength(3);
    expect(screen.queryByRole("button", { name: "风险提醒" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "查看其他 3 项" }));
    expect(evidence.querySelectorAll(".evidence-event")).toHaveLength(6);
    expect(evidence).toHaveTextContent("签署战略合作协议");
    fireEvent.click(screen.getAllByText("查看原始证据")[1]);
    expect(evidence).toHaveTextContent("●业绩预告：2026-07-15 预计净利润同比下降");
  });

  it("shows an explicit unavailable state when F10 has no latest tips", async () => {
    render(<CompanyResearchView
      selectedSymbol="600519"
      load={vi.fn(async () => research)}
      search={vi.fn(async () => ({ query: "", items: [], server_time: "", source_status: "ready" as const }))}
    />);

    expect(await screen.findByRole("region", { name: "催化与最新提示" })).toHaveTextContent("当前没有有效事件");
  });
});
