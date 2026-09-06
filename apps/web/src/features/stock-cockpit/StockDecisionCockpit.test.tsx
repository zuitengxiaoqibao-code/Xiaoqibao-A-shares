import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SelectedInstrumentProvider, useSelectedInstrument } from "../instrument-selection/SelectedInstrumentProvider";
import type { Advice } from "../decision-workbench/types";
import { StockDecisionCockpit } from "./StockDecisionCockpit";
import type { CockpitSection, StockCockpitSnapshot } from "./types";
import type { CandidateSentimentSnapshot } from "../candidate-sentiment/types";
import type { MarketSentimentResponse } from "../market-sentiment/types";
import type { StockTimelineResponse } from "../stock-timeline/types";
import type { BreakingNewsAlertResponse } from "../news-alerts/types";
import { writeDailySnapshot } from "../../shared/dailySnapshotCache";
import type { LoadProgressCallback } from "../../shared/fetchJsonWithProgress";

const observedAt = "2026-07-15T10:29:00+08:00";

function panelSentiment(
  overrides: Partial<CandidateSentimentSnapshot> = {},
): CandidateSentimentSnapshot {
  return {
    snapshot_id: "candidate-sentiment-600000",
    candidate_snapshot_id: "candidate-1",
    candidate_input_hash: "a".repeat(64),
    symbol: "600000",
    quality: "ready",
    freshness: "current",
    score: "82",
    band: "overheated",
    coverage_percent: "100",
    components: [
      { name: "news", status: "ready", score: "75", weight: "40", summary: "新闻偏积极", observed_at: observedAt, evidence_ids: ["news-1"] },
      { name: "hotspot", status: "ready", score: "90", weight: "30", summary: "热点延续", observed_at: observedAt, evidence_ids: ["hotspot-1"] },
      { name: "fund_flow", status: "ready", score: "80", weight: "30", summary: "资金偏流入", observed_at: observedAt, evidence_ids: ["fund-1"] },
    ],
    primary_reason: "热点延续并有资金配合。",
    primary_risk: "追涨和拥挤风险上升。",
    beginner_guidance: "关注拥挤和回落风险。",
    observed_at: observedAt,
    generated_at: "2026-07-15T10:29:05+08:00",
    source_snapshot_ids: ["news-1", "hotspot-1", "fund-1"],
    formula_version: "candidate-sentiment-v1",
    ...overrides,
  };
}

function advice(overrides: Partial<Advice> = {}): Advice {
  return {
    advice_id: "a1", snapshot_id: "s1", asset: "a_share", symbol: "600000",
    horizon: "intraday", observation_state: "watching", action: "observe",
    conclusion: "保持观察", confidence: "0.72",
    supporting_evidence: [{ evidence_id: "e1", source: "tencent", snapshot_id: "q1", summary: "量价稳定", observed_at: observedAt }],
    contrary_evidence: [], risks: ["市场波动"], invalidation_conditions: ["趋势改变"],
    plain_language_explanation: "等待更多确认", quantitative_result: {}, ai_interpretation_id: null,
    risk_decision_id: null, previous_advice_id: null, changed_fields: [],
    strategy_version: "v1", created_at: "2026-07-15T10:30:00+08:00", ...overrides,
  };
}

function section(name: string): CockpitSection {
  return { status: "ready", source: `fixture-${name}`, observed_at: observedAt, snapshot_id: `snapshot-${name}`, reason: null, payload: { metrics: name === "market" ? { latest_price: "10.25", change_percent: "1.49" } : {} } };
}

function snapshot(overrides: Partial<StockCockpitSnapshot> = {}): StockCockpitSnapshot {
  const item = advice();
  const sections = Object.fromEntries(["market", "price_volume", "trend", "valuation", "fundamentals", "funds", "news", "industry", "risk", "backtest"].map((name) => [name, section(name)]));
  return {
    symbol: "600000", as_of: "2026-07-15", cutoff: "2026-07-15T10:30:00+08:00", overall_quality: "ready",
    instrument: { symbol: "600000", name: "浦发银行", exchange: "sh", observed_at: observedAt, quote_quality: "ready" },
    preparation: { symbol: "600000", status: "ready", refreshed: true, started_at: observedAt, completed_at: observedAt, sources: [
      { name: "quote", status: "ready", observed_at: observedAt, reason: null },
      { name: "history", status: "ready", observed_at: observedAt, reason: null },
      { name: "finance", status: "partial", observed_at: null, reason: "source unavailable" },
      { name: "news", status: "ready", observed_at: observedAt, reason: null },
    ] },
    candidate_membership: ["short_term"],
    assessment: { assessment_id: "assessment-1", symbol: "600000", action: "observe", conclusion: "行情与趋势可用，保持观察。", confidence: "0.75", supporting_evidence: item.supporting_evidence, contrary_evidence: [], risks: ["市场波动"], invalidation_conditions: ["趋势改变"], generated_at: "2026-07-15T10:30:00+08:00" },
    field_evidence: [{
      field_path: "market.latest_price", value: "10.25", source: "tencent", source_field: "price",
      status: "live", trade_date: "2026-07-15", observed_at: observedAt, coverage_percent: "100.00",
      derived: false, formula: null, evidence_ids: ["market-evidence"], limitations: [],
    }, {
      field_path: "assessment.confidence", value: "0.75", source: "stock-assessor", source_field: null,
      status: "derived", trade_date: "2026-07-15", observed_at: observedAt, coverage_percent: "100.00",
      derived: true, formula: "deterministic-stock-assessor-v1", evidence_ids: ["market-evidence"], limitations: [],
    }],
    ai_status: "unconfigured", ai_explanation: null, current_advice: [item], sections,
    phases: { premarket: { advice: [], change_stream: [] }, intraday: { advice: [item], change_stream: [] }, postclose: { advice: [], change_stream: [] } },
    ...overrides,
  };
}

function renderCockpit(load: (symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback) => Promise<StockCockpitSnapshot>, asOf?: string) {
  window.history.replaceState({}, "", "/?symbol=600000");
  return render(<SelectedInstrumentProvider><StockDecisionCockpit load={load} asOf={asOf} /></SelectedInstrumentProvider>);
}

const watchlistMarketSentiment: MarketSentimentResponse = {
  trading_date: "2026-07-15", phase: "intraday", display_mode: "current",
  current: {
    snapshot_id: "sentiment-watchlist", previous_snapshot_id: null, trading_date: "2026-07-15",
    phase: "intraday", quality: "ready", freshness: "current", score: "64", band: "active",
    coverage_percent: "88", components: [], drivers: [], risks: [], beginner_guidance: "顺势观察，但不要追高。",
    observed_at: observedAt, generated_at: observedAt, source_snapshot_ids: ["source-1"], formula_version: "a-share-sentiment-v1",
  },
  previous_close: null, trajectory: [],
};

const stockTimeline: StockTimelineResponse = {
  symbol: "600000", as_of: "2026-07-15", cutoff: observedAt, status: "ready",
  bars: [{ symbol: "600000", trade_date: "2026-07-15", open: "10", high: "10.5", low: "9.8", close: "10.25", volume: 100, amount: "1025", source: "local-daily-bars" }],
  events: [], sources: ["local-daily-bars", "verified-market-news"], warnings: [],
};

const alertResponse: BreakingNewsAlertResponse = {
  status: "ready", observed_at: observedAt, sources: ["上交所"], warnings: [],
  alerts: [{
    event_id: "stock-alert", headline: "浦发银行重要事件已核验", occurred_at: observedAt,
    verification_state: "verified", urgency: "breaking", association_kind: "direct",
    association_reasons: ["company_alias:浦发银行"], affected_symbols: ["600000"], themes: [],
    publishers: ["上交所"], source_urls: ["https://news.example/stock"], source_count: 1,
    impact_direction: "uncertain", impact_confidence: null, ai_degraded: true,
  }],
};

describe("StockDecisionCockpit", () => {
  it("shows an expandable field-level truthfulness summary", async () => {
    renderCockpit(() => Promise.resolve(snapshot()));

    expect(await screen.findByRole("group", { name: "关键字段证据" })).toBeInTheDocument();
    expect(screen.getByText("1 项实时")).toBeInTheDocument();
    expect(screen.getByText("1 项推算")).toBeInTheDocument();
  });
  beforeEach(() => localStorage.clear());

  it("shows today's complete cache while the newest snapshot loads and then replaces it", async () => {
    const cached = snapshot({
      instrument: { ...snapshot().instrument, name: "缓存中的浦发银行" },
    });
    writeDailySnapshot("stock-cockpit", "600000", cached, new Date());
    let finish!: (value: StockCockpitSnapshot) => void;
    const load = vi.fn((
      _symbol: string,
      _asOf?: string,
      _signal?: AbortSignal,
      onProgress?: LoadProgressCallback,
    ) => {
      onProgress?.({ percent: 42, stage: "receiving", detail: "正在接收最新个股数据" });
      return new Promise<StockCockpitSnapshot>((resolve) => { finish = resolve; });
    });

    renderCockpit(load);

    expect(await screen.findByText("缓存中的浦发银行")).toBeInTheDocument();
    const status = screen.getByRole("status", { name: "个股观察数据刷新状态" });
    expect(status).toHaveTextContent("当日缓存");
    expect(status).toHaveTextContent("正在载入最新数据");
    expect(within(status).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "42");

    await act(async () => finish(snapshot({
      instrument: { ...snapshot().instrument, name: "最新浦发银行" },
    })));
    expect(await screen.findByText("最新浦发银行")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "个股观察数据刷新状态" })).toHaveTextContent("已加载实时最新数据");
    expect(screen.getByRole("status", { name: "个股观察数据刷新状态" })).toHaveTextContent("当前状态：实时监控中");
  });

  it("shows a partial completion state while optional data preparation continues", async () => {
    writeDailySnapshot("stock-cockpit", "600000", snapshot(), new Date());
    let finishPreparation!: (value: NonNullable<StockCockpitSnapshot["preparation"]>) => void;
    const prepare = vi.fn().mockReturnValue(new Promise((resolve) => { finishPreparation = resolve; }));
    window.localStorage.setItem("qibao.autoSync", "true");
    window.history.replaceState({}, "", "/?symbol=600000");

    render(
      <SelectedInstrumentProvider>
        <StockDecisionCockpit load={() => Promise.resolve(snapshot())} prepare={prepare} />
      </SelectedInstrumentProvider>,
    );

    await waitFor(() => expect(prepare).toHaveBeenCalledTimes(1));
    const status = screen.getByRole("status", { name: "个股观察数据刷新状态" });
    expect(status).toHaveTextContent("已加载最新可用数据");
    expect(status).toHaveTextContent("核心行情已更新，扩展数据仍待补齐");
    expect(status).not.toHaveTextContent("已加载实时最新数据");
    expect(status).not.toHaveTextContent("正在载入最新数据");
    expect(screen.getByText("正在补齐数据")).toBeInTheDocument();

    await act(async () => finishPreparation({ ...snapshot().preparation!, refreshed: false }));
    await waitFor(() => expect(status).toHaveTextContent("已加载实时最新数据"));
    expect(status).toHaveTextContent("当前状态：实时监控中");
  });

  it("keeps today's cache visible when the newest snapshot fails", async () => {
    writeDailySnapshot("stock-cockpit", "600000", snapshot(), new Date());
    renderCockpit(() => Promise.reject(new Error("offline")));

    expect(await screen.findByText("浦发银行")).toBeInTheDocument();
    expect(await screen.findByRole("status", { name: "个股观察数据刷新状态" })).toHaveTextContent("继续显示当日缓存");
  });

  it("shows a cached refresh failure only once instead of duplicating the timeout alert", async () => {
    writeDailySnapshot("stock-cockpit", "600000", snapshot(), new Date());
    renderCockpit(() => Promise.reject(new Error("请求超时，请稍后重试。")));

    const status = await screen.findByRole("status", { name: "个股观察数据刷新状态" });
    await waitFor(() => expect(status).toHaveTextContent("最新数据更新失败，继续显示当日缓存"));
    expect(screen.getAllByText("请求超时，请稍后重试。")).toHaveLength(1);
  });

  it("opens company research for the currently observed stock", async () => {
    const openCompanyResearch = vi.fn();
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><StockDecisionCockpit
      load={() => Promise.resolve(snapshot())}
      onOpenCompanyResearch={openCompanyResearch}
    /></SelectedInstrumentProvider>);

    fireEvent.click(await screen.findByRole("button", { name: "进入公司研究" }));

    expect(openCompanyResearch).toHaveBeenCalledWith("600000");
  });

  it("places company research immediately before the market time", async () => {
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><StockDecisionCockpit
      load={() => Promise.resolve(snapshot())}
      onOpenCompanyResearch={vi.fn()}
    /></SelectedInstrumentProvider>);

    const link = await screen.findByRole("button", { name: "进入公司研究" });
    const marketTime = screen.getByText("行情时间").closest("div");
    expect(link.parentElement).toBe(marketTime?.parentElement);
    expect(link.nextElementSibling).toBe(marketTime);
  });

  it("uses the shared terminal shell for the selected stock", async () => {
    renderCockpit(() => Promise.resolve(snapshot()));

    const cockpit = await screen.findByRole("main");
    expect(cockpit).toHaveClass("terminal-page", "stock-cockpit");
  });

  it("loads three verified alerts for the selected stock", async () => {
    const loadAlerts = vi.fn().mockResolvedValue(alertResponse);
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><StockDecisionCockpit
      load={() => Promise.resolve(snapshot())}
      loadAlerts={loadAlerts}
    /></SelectedInstrumentProvider>);

    expect(await screen.findByRole("region", { name: "突发事件" })).toHaveTextContent("浦发银行重要事件已核验");
    expect(loadAlerts).toHaveBeenCalledWith("600000", expect.any(AbortSignal), 3);
  });

  it("places the independently loaded event K-line before the decision summary", async () => {
    const loadTimeline = vi.fn().mockResolvedValue(stockTimeline);
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><StockDecisionCockpit load={() => Promise.resolve(snapshot())} loadTimeline={loadTimeline} /></SelectedInstrumentProvider>);

    const eventKline = await screen.findByRole("region", { name: "个股新闻与热点事件 K 线" });
    const timeframeCharts = await screen.findByRole("region", { name: "个股分时与近三十日行情" });
    const summary = screen.getByRole("region", { name: "证据决策摘要" });
    expect(eventKline.nextElementSibling).toBe(timeframeCharts);
    expect(timeframeCharts.compareDocumentPosition(summary) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(eventKline.compareDocumentPosition(summary) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await waitFor(() => expect(loadTimeline).toHaveBeenCalledWith("600000", undefined, expect.any(AbortSignal)));
  });

  it("prepares incomplete live data and reloads the cockpit exactly once", async () => {
    const partial = snapshot({ preparation: { ...snapshot().preparation!, status: "partial", refreshed: false } });
    const load = vi.fn().mockResolvedValueOnce(partial).mockResolvedValueOnce(snapshot());
    let finishPreparation!: (value: NonNullable<StockCockpitSnapshot["preparation"]>) => void;
    const prepare = vi.fn().mockReturnValue(new Promise((resolve) => { finishPreparation = resolve; }));
    window.localStorage.setItem("qibao.autoSync", "true");
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><StockDecisionCockpit load={load} prepare={prepare} /></SelectedInstrumentProvider>);
    expect(await screen.findByText("正在补齐数据")).toBeInTheDocument();
    await act(async () => finishPreparation({ ...partial.preparation!, refreshed: true }));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    expect(prepare).toHaveBeenCalledTimes(1);
  });

  it("prepares a live ready snapshot once so optional sources can refresh", async () => {
    const load = vi.fn()
      .mockResolvedValueOnce(snapshot())
      .mockResolvedValueOnce(snapshot());
    const prepare = vi.fn().mockResolvedValue({
      ...snapshot().preparation!, refreshed: true,
    });
    window.localStorage.setItem("qibao.autoSync", "true");
    window.history.replaceState({}, "", "/?symbol=600000");

    render(
      <SelectedInstrumentProvider>
        <StockDecisionCockpit load={load} prepare={prepare} />
      </SelectedInstrumentProvider>,
    );

    await waitFor(() => expect(prepare).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
  });

  it("never prepares historical snapshots", async () => {
    const load = vi.fn().mockResolvedValue(snapshot({ preparation: { ...snapshot().preparation!, status: "partial" } }));
    const prepare = vi.fn();
    window.localStorage.setItem("qibao.autoSync", "true");
    window.history.replaceState({}, "", "/?symbol=600000");
    render(<SelectedInstrumentProvider><StockDecisionCockpit load={load} prepare={prepare} asOf="2026-07-14" /></SelectedInstrumentProvider>);
    await screen.findByText("浦发银行");
    expect(prepare).not.toHaveBeenCalled();
  });
  it("renders one consolidated beginner decision summary without repeated evidence blocks", async () => {
    const view = renderCockpit(() => Promise.resolve(snapshot()));
    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("关键状态仪表");
    expect(summary).toHaveTextContent("行情与趋势可用，保持观察。");
    expect(screen.getAllByText("加入观察").length).toBeGreaterThan(0);
    expect(screen.getAllByText("主要依据")).toHaveLength(1);
    expect(screen.getAllByText("主要风险")).toHaveLength(1);
    expect(summary).toHaveTextContent("置信度");
    expect(summary).toHaveTextContent("75%");
    expect(summary).toHaveTextContent("AI 补充分析未启用");
    expect(screen.queryByText("新手行动卡")).not.toBeInTheDocument();
    expect(screen.queryByText("现在怎么做")).not.toBeInTheDocument();
    expect(screen.getByText("数据详情")).toBeInTheDocument();
    expect(screen.queryByText("资金数据尚未接入")).not.toBeInTheDocument();
    expect(screen.queryByText("尚未为该股票运行回测")).not.toBeInTheDocument();
    expect(screen.queryByText(/模拟操作|候选账本|策略：|研判编号|中书省|工部/)).not.toBeInTheDocument();
    expect(view.container.querySelector(".evidence-decision-verdict")).not.toBeInTheDocument();
  });

  it("keeps a ready AI explanation inside the consolidated evidence summary", async () => {
    const explained = snapshot({
      ai_status: "ready",
      ai_explanation: {
        plain_language: "量价暂时稳定，仍需等待资金确认。",
        news_impact: "新闻影响中性。",
        hotspot_attribution: "暂无持续热点。",
        uncertainty: "资金流证据仍不完整。",
        contrary_view: "若趋势转弱则应重新判断。",
        evidence_ids: ["e1"],
      },
    });
    renderCockpit(() => Promise.resolve(explained));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("AI 补充解释");
    expect(summary).toHaveTextContent("量价暂时稳定，仍需等待资金确认。");
    expect(screen.getAllByText("AI 补充解释")).toHaveLength(1);
    expect(within(summary).getByText("AI 补充解释").closest("section")).toHaveClass("status-ready");
    expect(within(summary).getByText("不确定性").closest("div")).toHaveClass("tone-warning");
    expect(within(summary).getByText("反方观点").closest("div")).toHaveClass("tone-danger");
  });

  it("renders verified analysis first and fills AI explanation in the background", async () => {
    let finishAI!: (value: StockCockpitSnapshot) => void;
    const loadAI = vi.fn().mockReturnValue(new Promise<StockCockpitSnapshot>(
      (resolve) => { finishAI = resolve; },
    ));
    window.history.replaceState({}, "", "/?symbol=600000");
    render(
      <SelectedInstrumentProvider>
        <StockDecisionCockpit
          load={() => Promise.resolve(snapshot({ ai_status: "deferred" }))}
          loadAI={loadAI}
        />
      </SelectedInstrumentProvider>,
    );

    expect(await screen.findByText("浦发银行")).toBeInTheDocument();
    expect(screen.getByText("AI 补充分析后台生成中")).toBeInTheDocument();
    expect(loadAI).toHaveBeenCalledWith("600000", undefined, expect.any(AbortSignal));

    await act(async () => finishAI(snapshot({
      ai_status: "ready",
      ai_explanation: {
        plain_language: "AI 已完成证据解释。",
        news_impact: "新闻中性",
        hotspot_attribution: "暂无热点",
        uncertainty: "样本有限",
        contrary_view: "趋势可能反转",
        evidence_ids: ["e1"],
      },
    })));

    expect(await screen.findByText("AI 已完成证据解释。")).toBeInTheDocument();
  });

  it.each([
    ["timeout", "AI 服务响应超时", "配置已生效"],
    ["http_error", "AI 服务返回错误", "检查服务地址、模型权限或账户状态"],
    ["invalid", "AI 返回内容未通过校验", "没有采用未经验证的内容"],
  ] as const)("explains the %s AI failure without claiming it is unconfigured", async (status, title, detail) => {
    renderCockpit(() => Promise.resolve(snapshot({ ai_status: status })));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent(title);
    expect(summary).toHaveTextContent(detail);
    expect(summary).not.toHaveTextContent("AI 补充分析未启用");
    expect(summary).not.toHaveTextContent("AI 解释暂不可用");
  });

  it("shows an evidence decision summary before the detailed cockpit sections", async () => {
    const complete = snapshot({
      assessment: { ...snapshot().assessment, invalidation_conditions: ["趋势改变。"] },
      preparation: {
        ...snapshot().preparation!,
        status: "ready",
        sources: snapshot().preparation!.sources.map((source) => ({ ...source, status: "ready" as const })),
      },
    });
    renderCockpit(() => Promise.resolve(complete));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveClass("action-observe", "evidence-ready");
    expect(within(summary).getByText("当前行动").closest("section")).toHaveClass("tone-positive");
    expect(within(summary).getByRole("meter", { name: "证据覆盖率" })).toHaveAttribute("aria-valuenow", "100");
    expect(within(summary).getByText("主要依据").closest("section")).toHaveClass("tone-positive");
    expect(within(summary).getByText("主要风险").closest("section")).toHaveClass("tone-danger");
    expect(within(summary).getByText("下一步").closest("section")).toHaveClass("tone-positive");
    expect(within(summary).getByText("何时推翻").closest("section")).toHaveClass("tone-danger");
    expect(summary).toHaveTextContent("有证据的辅助决策");
    expect(summary).toHaveTextContent("关键状态仪表");
    expect(summary).toHaveTextContent("加入观察");
    expect(summary).toHaveTextContent("证据较完整");
    expect(summary).toHaveTextContent("4 / 4 类可用");
    expect(summary).toHaveTextContent("下一步");
    expect(summary).toHaveTextContent("若趋势改变，重新判断");
    expect(summary).not.toHaveTextContent("趋势改变。，重新判断");
    expect(summary).toHaveTextContent("盘前研判");
    expect(summary).toHaveTextContent("尚无记录");
    expect(summary).toHaveTextContent("盘中观察");
    expect(summary).toHaveTextContent("已生成建议");
    expect(summary).toHaveTextContent("盘后验证");
    expect(screen.queryByText("现在怎么做")).not.toBeInTheDocument();
  });

  it.each([
    ["wait", "tone-warning"],
    ["avoid", "tone-danger"],
  ] as const)("uses a semantic %s action tone for the verdict and next step", async (action, tone) => {
    renderCockpit(() => Promise.resolve(snapshot({
      assessment: { ...snapshot().assessment, action },
    })));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveClass(`action-${action}`);
    expect(within(summary).getByText("当前行动").closest("section")).toHaveClass(tone);
    expect(within(summary).getByText("下一步").closest("section")).toHaveClass(tone);
  });

  it("shows blocked and scheduled phase states without inventing a conclusion", async () => {
    const phased = snapshot({
      phases: {
        premarket: {
          advice: [], change_stream: [], phase_status: "blocked", quality_reasons: ["live_quotes_unavailable"],
        },
        intraday: {
          advice: [], change_stream: [], phase_status: "empty",
          execution: { status: "scheduled", scheduled_at: observedAt, next_scheduled_at: observedAt, last_completed_at: null, last_attempt_at: null, attempts: 0, error_code: null },
        },
        postclose: { advice: [], change_stream: [], phase_status: "partial" },
      },
    });
    renderCockpit(() => Promise.resolve(phased));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("盘前研判");
    expect(summary).toHaveTextContent("已拦截");
    expect(summary).toHaveTextContent("盘中观察");
    expect(summary).toHaveTextContent("已计划");
    expect(summary).toHaveTextContent("盘后验证");
    expect(summary).toHaveTextContent("部分可用");
    expect(summary).not.toHaveTextContent("盘前研判已生成建议");
  });

  it("explains that an empty phase is separate from the available single-stock conclusion", async () => {
    renderCockpit(() => Promise.resolve(snapshot()));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("当前结论来自单股研判");
    expect(summary).toHaveTextContent("盘后复盘尚未生成");
  });

  it("explains what changed since the previous verified advice", async () => {
    const previous = advice({ advice_id: "a0", action: "wait", conclusion: "等待确认" });
    const current = advice({ advice_id: "a1", previous_advice_id: "a0", changed_fields: ["action", "conclusion"], action: "observe", conclusion: "保持观察" });
    const phased = snapshot({
      phases: {
        premarket: { advice: [], change_stream: [] },
        intraday: { advice: [previous, current], change_stream: [] },
        postclose: { advice: [], change_stream: [] },
      },
    });
    renderCockpit(() => Promise.resolve(phased));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("与上次相比");
    expect(summary).toHaveTextContent("暂不参与 → 加入观察");
    expect(summary).toHaveTextContent("建议状态发生变化");
    expect(summary).not.toHaveTextContent("a0");
  });

  it("shows a beginner observation checklist from verified section status", async () => {
    const checked = snapshot();
    checked.sections.news.status = "partial";
    checked.sections.funds.status = "unavailable";
    renderCockpit(() => Promise.resolve(checked));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("观察检查清单");
    expect(summary).toHaveTextContent("行情");
    expect(summary).toHaveTextContent("已验证");
    expect(summary).toHaveTextContent("新闻与热点");
    expect(summary).toHaveTextContent("部分可用");
    expect(summary).toHaveTextContent("资金");
    expect(summary).toHaveTextContent("暂不可用");
    expect(within(summary).getByText("新闻与热点").parentElement).toHaveClass("partial");
    expect(within(summary).getByText("资金").parentElement).toHaveClass("unavailable");
  });

  it("connects a verified postclose outcome back to the original conclusion", async () => {
    const original = advice({ advice_id: "a0", conclusion: "等待确认", action: "wait" });
    const reviewed = advice({
      advice_id: "postclose-a1", action: "observe", conclusion: "复盘验证通过，列入次日观察",
      previous_advice_id: "a0", changed_fields: ["outcome_status"],
      quantitative_result: { outcome_status: "correct", error_attribution: "trend_failure", original_advice_id: "a0" },
    });
    const phased = snapshot({ phases: {
      premarket: { advice: [], change_stream: [] },
      intraday: { advice: [original], change_stream: [] },
      postclose: { advice: [reviewed], change_stream: [] },
    } });
    renderCockpit(() => Promise.resolve(phased));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("盘后反馈");
    expect(summary).toHaveTextContent("判断成立");
    expect(summary).toHaveTextContent("对应原判断：等待确认");
    expect(summary).toHaveTextContent("趋势结果");
    expect(summary).not.toHaveTextContent("original_advice_id");
  });

  it("downgrades the evidence label when core sources are only partially available", async () => {
    const partial = snapshot({
      overall_quality: "partial",
      preparation: {
        ...snapshot().preparation!,
        status: "partial",
        sources: [
          { name: "quote", status: "ready", observed_at: observedAt, reason: null },
          { name: "history", status: "partial", observed_at: null, reason: "history unavailable" },
          { name: "finance", status: "partial", observed_at: null, reason: "finance unavailable" },
          { name: "news", status: "partial", observed_at: null, reason: "news unavailable" },
        ],
      },
    });
    renderCockpit(() => Promise.resolve(partial));

    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("证据部分可用");
    expect(summary).toHaveTextContent("1 / 4 类可用");
    expect(summary).toHaveTextContent("不确定性更高");
  });

  it("renders matching candidate sentiment after the action conclusion", async () => {
    window.history.replaceState({}, "", "/?symbol=600000");
    const view = render(
      <SelectedInstrumentProvider>
        <StockDecisionCockpit
          load={() => Promise.resolve(snapshot())}
          candidateSentiment={panelSentiment()}
        />
      </SelectedInstrumentProvider>,
    );

    const panel = await screen.findByRole("region", { name: "个股情绪观察" });
    const summary = view.container.querySelector(".evidence-decision-summary") as HTMLElement;
    expect(summary).toHaveTextContent("行情与趋势可用，保持观察。");
    expect(summary).toHaveTextContent("82");
    expect(within(summary).getByRole("meter", { name: "个股情绪" })).toHaveAttribute("aria-valuenow", "82");
    expect(panel).toHaveTextContent("不改变候选排序与行动结论");
    expect(summary.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("renders watchlist market sentiment in the right-side cockpit after a watchlist selection", async () => {
    window.history.replaceState({}, "", "/?symbol=600000");
    const loadMarketSentiment = vi.fn(() => Promise.resolve(watchlistMarketSentiment));
    function WatchlistSelection() {
      const selection = useSelectedInstrument();
      return <><button type="button" onClick={() => selection.select("600000", "watchlist")}>选择自选股</button><StockDecisionCockpit load={() => Promise.resolve(snapshot())} loadMarketSentiment={loadMarketSentiment} /></>;
    }

    render(<SelectedInstrumentProvider><WatchlistSelection /></SelectedInstrumentProvider>);
    fireEvent.click(screen.getByRole("button", { name: "选择自选股" }));

    const panel = await screen.findByRole("region", { name: "自选股市场环境" });
    expect(panel).toHaveTextContent("A 股全市场环境");
    await waitFor(() => expect(loadMarketSentiment).toHaveBeenCalledTimes(1));
  });

  it("does not render an empty or mismatched sentiment panel", async () => {
    renderCockpit(() => Promise.resolve(snapshot()));
    await screen.findByText("浦发银行");
    expect(screen.queryByRole("region", { name: "个股情绪观察" })).not.toBeInTheDocument();

    window.history.replaceState({}, "", "/?symbol=600000");
    render(
      <SelectedInstrumentProvider>
        <StockDecisionCockpit
          load={() => Promise.resolve(snapshot())}
          candidateSentiment={panelSentiment({ symbol: "000001" })}
        />
      </SelectedInstrumentProvider>,
    );
    await screen.findAllByText("浦发银行");
    expect(screen.queryByRole("region", { name: "个股情绪观察" })).not.toBeInTheDocument();
  });

  it("shows verified trend and fundamental metrics with beginner units", async () => {
    const detailed = snapshot();
    detailed.sections.market.payload.metrics = { latest_price: "10.25", change_percent: "0.633862484613048135" };
    detailed.sections.price_volume.payload.metrics = { close: "10.25", return_5d: "0.052", average_amount_20d: "880000000", volume_ratio: "1.18" };
    detailed.sections.fundamentals.source = "mootdx-finance";
    detailed.sections.fundamentals.payload.metrics = { data_updated_on: "2026-04-25", eps: "1.33", roe: "11.43", net_profit: "3200000000", revenue: "88000000000", total_shares: "2400000000" };
    renderCockpit(() => Promise.resolve(detailed));
    fireEvent.click(await screen.findByText("数据详情"));
    expect(screen.getByText("近5日涨跌")).toBeInTheDocument();
    expect(screen.getByText("5.20%")).toBeInTheDocument();
    expect(screen.getByText("净资产收益率")).toBeInTheDocument();
    expect(screen.getByText("11.43%")).toBeInTheDocument();
    expect(screen.getByText("净利润")).toBeInTheDocument();
    expect(screen.getByText("32.00 亿元")).toBeInTheDocument();
    expect(screen.getByText("数据更新日")).toBeInTheDocument();
    expect(screen.getByText("2026-04-25")).toBeInTheDocument();
    expect(screen.getAllByText("0.63%")).toHaveLength(2);
    expect(screen.queryByText("0.633862484613048135%")).not.toBeInTheDocument();
    expect(screen.getByText("来源：通达信财务快照")).toBeInTheDocument();
  });

  it("shows signed verified fund flow and preserves missing values", async () => {
    const detailed = snapshot();
    detailed.sections.funds.source = "eastmoney-fund-flow";
    detailed.sections.funds.payload.metrics = {
      latest_trade_date: "2026-07-15",
      latest_main_net: "120000000",
      latest_super_net: "70000000",
      latest_large_net: "50000000",
      main_net_5d: "350000000",
      main_net_20d: "-120000000",
      intraday_main_net: null,
      daily_sample_count: 20,
      intraday_sample_count: 0,
      flow_direction: "inflow",
    };
    detailed.sections.funds.payload.evidence_ids = [
      "fund-flow-1234567890abcdef12345678",
    ];

    renderCockpit(() => Promise.resolve(detailed));
    fireEvent.click(await screen.findByText("数据详情"));

    const funds = screen.getByRole("region", { name: "资金流" });
    fireEvent.click(within(funds).getByText("查看详细指标"));
    expect(within(funds).getByText("近5日主力净额")).toBeInTheDocument();
    expect(within(funds).getByText("+3.50 亿元")).toBeInTheDocument();
    expect(within(funds).getByText("-1.20 亿元")).toBeInTheDocument();
    expect(within(funds).getByText("未提供")).toBeInTheDocument();
    expect(within(funds).getByText("净流入")).toBeInTheDocument();
    expect(within(funds).getByText("来源：东方财富资金流")).toBeInTheDocument();
    expect(within(funds).getByText(/时间：.*2026/)).toBeInTheDocument();
    fireEvent.click(within(funds).getByText("1 条证据编号"));
    expect(within(funds).getByText(
      "fund-flow-1234567890abcdef12345678",
    )).toBeInTheDocument();
  });

  it("explains when daily fund flow is available but intraday data is missing", async () => {
    const detailed = snapshot();
    detailed.sections.funds.status = "partial";
    detailed.sections.funds.source = "eastmoney-fund-flow";
    detailed.sections.funds.reason = "fund_flow_intraday_unavailable";

    renderCockpit(() => Promise.resolve(detailed));
    fireEvent.click(await screen.findByText("数据详情"));

    const funds = screen.getByRole("region", { name: "资金流" });
    expect(within(funds).getByText(
      "日级资金流可用，盘中分钟资金流暂未返回；本项仅供历史观察。",
    )).toBeInTheDocument();
    expect(within(funds).getByText("部分可用")).toBeInTheDocument();
  });

  it("explains unavailable fund flow without implying it affected the decision", async () => {
    const detailed = snapshot();
    detailed.sections.funds = {
      status: "unavailable",
      source: "eastmoney-fund-flow",
      observed_at: null,
      snapshot_id: "diagnosis-section-unavailable-funds",
      reason: "diagnosis_section_unavailable",
      payload: { metrics: {}, evidence_ids: [] },
    };

    renderCockpit(() => Promise.resolve(detailed));
    fireEvent.click(await screen.findByText("数据详情"));

    const funds = screen.getByRole("region", { name: "资金流" });
    expect(within(funds).getByText(
      "东方财富资金流暂未返回可核验数据，本项未参与当前研判。",
    )).toBeInTheDocument();
    expect(within(funds).queryByText("该分区数据暂不可用")).not.toBeInTheDocument();
  });

  it("explains unavailable industry data without implying it affected the decision", async () => {
    const detailed = snapshot();
    detailed.sections.industry = {
      status: "unavailable",
      source: "eastmoney-stock-classification",
      observed_at: null,
      snapshot_id: "diagnosis-section-unavailable-industry",
      reason: "diagnosis_section_unavailable",
      payload: { metrics: {}, evidence_ids: [] },
    };

    renderCockpit(() => Promise.resolve(detailed));
    fireEvent.click(await screen.findByText("数据详情"));

    const industry = screen.getByRole("region", { name: "申万行业与题材" });
    expect(within(industry).getByText(
      "申万行业分类暂未返回可核验数据，本项未参与当前研判。",
    )).toBeInTheDocument();
    expect(within(industry).queryByText("该分区数据暂不可用")).not.toBeInTheDocument();
  });

  it("separates structured classification from news event labels", async () => {
    const detailed = snapshot();
    const allBoardTags = Array.from(
      { length: 29 },
      (_, index) => `已核验板块${String(index + 1).padStart(2, "0")}`,
    ).join("、");
    detailed.sections.industry.source = "eastmoney-stock-classification";
    detailed.sections.industry.payload.metrics = {
      industry: "食品饮料",
      board_tags: allBoardTags,
    };
    detailed.sections.industry.payload.evidence_ids = [
      "stock-classification-1234567890abcdef12345678",
    ];
    detailed.sections.news.source = "frozen-news-events";
    detailed.sections.news.payload.metrics = {
      event_count: 1,
      adverse_event_count: 0,
      event_industries: "消费行业",
    };
    detailed.sections.news.payload.evidence_ids = ["event-verified-news-1"];

    renderCockpit(() => Promise.resolve(detailed));
    fireEvent.click(await screen.findByText("数据详情"));

    expect(screen.getByText("所属行业")).toBeInTheDocument();
    expect(screen.getByText("板块标签")).toBeInTheDocument();
    expect(screen.getByText("新闻事件行业标签")).toBeInTheDocument();
    expect(screen.getByText(allBoardTags)).toBeInTheDocument();
    expect(screen.getByText(/已核验板块29$/)).toBeInTheDocument();
    expect(screen.getByText("来源：申万行业分类（来源：东方财富）")).toBeInTheDocument();
    expect(screen.getByText("来源：已核验新闻事件")).toBeInTheDocument();
    const industrySection = screen.getByRole("region", { name: "申万行业与题材" });
    const newsSection = screen.getByRole("region", { name: "新闻与事件" });
    fireEvent.click(within(industrySection).getByText("1 条证据编号"));
    fireEvent.click(within(newsSection).getByText("1 条证据编号"));
    expect(within(industrySection).getByText(
      "stock-classification-1234567890abcdef12345678",
    )).toBeInTheDocument();
    expect(within(newsSection).getByText("event-verified-news-1")).toBeInTheDocument();
    expect(within(industrySection).queryByText("event-verified-news-1")).not.toBeInTheDocument();
    expect(screen.queryByText("已核验行业标签")).not.toBeInTheDocument();
  });

  it("keeps a missing market percentage visibly unknown", async () => {
    const missing = snapshot();
    missing.sections.market.payload.metrics = { latest_price: "10.25", change_percent: null };

    renderCockpit(() => Promise.resolve(missing));

    await screen.findByText("浦发银行");
    expect(screen.getByText("--")).toBeInTheDocument();
    expect(screen.queryByText("0.00%")).not.toBeInTheDocument();
    expect(document.querySelector(".cockpit-quote .lucide-trending-up")).not.toBeInTheDocument();
    expect(document.querySelector(".cockpit-quote .lucide-trending-down")).not.toBeInTheDocument();
  });

  it("translates internal assessment codes into deduplicated beginner language", async () => {
    const hostile = snapshot();
    hostile.assessment.risks = ["source_snapshot_unavailable:market", "source_snapshot_unavailable:market", "缺失或晚于截止时间的分区：industry、news。", "SECRET_INTERNAL_CODE"];
    hostile.assessment.invalidation_conditions = ["source_snapshot_unavailable:trend", "source_snapshot_unavailable:fundamentals", "source_snapshot_unavailable:risk", "unknown_internal_token"];
    renderCockpit(() => Promise.resolve(hostile));
    const summary = await screen.findByRole("region", { name: "证据决策摘要" });
    expect(summary).toHaveTextContent("实时行情发生变化需重评");
    expect(summary).toHaveTextContent("新闻或行业信息晚于研判截止时间或暂缺");
    expect(summary).toHaveTextContent("走势数据发生变化需重评");
    expect(screen.queryByText(/source_snapshot|industry|news|SECRET|unknown_internal|fundamentals/)).not.toBeInTheDocument();
  });

  it("describes an already-ready snapshot without claiming preparation never ran", async () => {
    renderCockpit(() => Promise.resolve(snapshot({ preparation: { ...snapshot().preparation!, status: "ready", refreshed: false } })));
    expect(await screen.findByText("数据无需再次补齐")).toBeInTheDocument();
    expect(screen.queryByText("尚未执行自动补齐")).not.toBeInTheDocument();
  });

  it("keeps the last snapshot visible and reports the failed refresh", async () => {
    const load = vi.fn().mockResolvedValueOnce(snapshot()).mockRejectedValueOnce(new Error("offline"));
    renderCockpit(load);
    await screen.findByText("浦发银行");
    fireEvent.click(screen.getByRole("button", { name: "刷新驾驶舱" }));
    expect(await screen.findByRole("status", { name: "个股观察数据刷新状态" })).toHaveTextContent("最新数据更新失败，继续显示当日缓存");
    expect(screen.queryByText("offline")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("浦发银行")).toBeInTheDocument();
  });

  it("refreshes the visible stock cockpit periodically without changing the selected symbol", async () => {
    vi.useFakeTimers();
    try {
      const load = vi.fn(async () => snapshot());
      renderCockpit(load);
      await act(async () => { await Promise.resolve(); await Promise.resolve(); });
      expect(load).toHaveBeenCalledTimes(1);
      await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
      expect(load).toHaveBeenCalledTimes(2);
      expect(screen.getByText("浦发银行")).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the consolidated decision summary available when an older API snapshot has no preparation report", async () => {
    renderCockpit(() => Promise.resolve(snapshot({ preparation: undefined })));
    expect((await screen.findAllByText("加入观察")).length).toBeGreaterThan(0);
    expect(screen.getByText("尚未执行自动补齐")).toBeInTheDocument();
  });

  it("never exposes hostile raw keys, JSON, reason codes, or source identifiers", async () => {
    const hostile = snapshot();
    hostile.sections.market = { status: "partial", source: "internal_secret_feed", observed_at: observedAt, snapshot_id: "hidden", reason: "SECRET_REASON_CODE", payload: { explanation: "工部 internal-id-999", metrics: { latest_price: "10", secret_alpha: "LEAK", nested: { token: "LEAK_JSON" } } } };
    renderCockpit(() => Promise.resolve(hostile));
    await screen.findByText("数据详情");
    fireEvent.click(screen.getByText("数据详情"));
    expect(screen.getByText("未提供可展示说明")).toBeInTheDocument();
    expect(screen.queryByText(/SECRET|internal_secret|secret_alpha|LEAK|\{"token"|工部|internal-id/)).not.toBeInTheDocument();
  });

  it("does not retain live data when a historical request fails", async () => {
    const load = vi.fn().mockResolvedValueOnce(snapshot()).mockRejectedValueOnce(new Error("history unavailable"));
    const view = renderCockpit(load);
    await screen.findByText("浦发银行");
    view.rerender(<SelectedInstrumentProvider><StockDecisionCockpit load={load} asOf="2026-07-14" /></SelectedInstrumentProvider>);
    expect(await screen.findByText("驾驶舱暂不可用")).toBeInTheDocument();
    expect(screen.queryByText("浦发银行")).not.toBeInTheDocument();
  });

  it("prevents an older stock response from replacing a newer selection", async () => {
    let resolveOld!: (value: StockCockpitSnapshot) => void;
    const load = vi.fn((symbol: string) => symbol === "600000"
      ? new Promise<StockCockpitSnapshot>((resolve) => { resolveOld = resolve; })
      : Promise.resolve(snapshot({ symbol: "000001", instrument: { ...snapshot().instrument, symbol: "000001", name: "平安银行" } })));
    renderCockpit(load);
    await act(async () => {
      window.history.pushState({}, "", "/?symbol=000001");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(await screen.findByText("平安银行")).toBeInTheDocument();
    await act(async () => resolveOld(snapshot()));
    expect(screen.queryByText("浦发银行")).not.toBeInTheDocument();
  });

  it("shows a previously viewed stock immediately while refreshing it in the background", async () => {
    let firstBankLoads = 0;
    const load = vi.fn((symbol: string) => {
      if (symbol === "600000") {
        firstBankLoads += 1;
        return firstBankLoads === 1
          ? Promise.resolve(snapshot())
          : new Promise<StockCockpitSnapshot>(() => undefined);
      }
      return Promise.resolve(snapshot({
        symbol: "000001",
        instrument: {
          ...snapshot().instrument,
          symbol: "000001",
          name: "平安银行",
          exchange: "sz",
        },
      }));
    });
    renderCockpit(load);
    await screen.findByText("浦发银行");

    await act(async () => {
      window.history.pushState({}, "", "/?symbol=000001");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await screen.findByText("平安银行");

    await act(async () => {
      window.history.pushState({}, "", "/?symbol=600000");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(await screen.findByText("浦发银行")).toBeInTheDocument();
    expect(screen.getByText("后台更新中")).toBeInTheDocument();
  });
});
