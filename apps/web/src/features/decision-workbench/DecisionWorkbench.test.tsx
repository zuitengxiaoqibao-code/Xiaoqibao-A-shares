import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DecisionWorkbench } from "./DecisionWorkbench";
import type { Advice, DecisionResponse, PhaseSlot } from "./types";

const emptySlot: PhaseSlot = {
  phase_status: "empty", quality: "empty", aggregate_version: null,
  ai_status: "not_requested", advice: [], evidence: [],
};

function advice(overrides: Partial<Advice> = {}): Advice {
  return {
    advice_id: "a1", snapshot_id: "s1", asset: "a_share", symbol: "600000",
    horizon: "intraday", observation_state: "watching", action: "observe",
    conclusion: "保持观察", confidence: "0.7",
    supporting_evidence: [{ evidence_id: "e1", source: "tencent", snapshot_id: "q1", summary: "价格有效", observed_at: "2026-07-15T10:29:00+08:00" }],
    contrary_evidence: [], risks: ["波动"], invalidation_conditions: ["条件变化"],
    plain_language_explanation: null, quantitative_result: {}, ai_interpretation_id: null,
    risk_decision_id: null, previous_advice_id: null, changed_fields: [],
    strategy_version: "v1", created_at: "2026-07-15T10:30:00+08:00", ...overrides,
  };
}

function response(overrides: Partial<DecisionResponse> = {}): DecisionResponse {
  return {
    server_time: "2026-07-15T10:30:00+08:00", trading_date: "2026-07-15",
    current_phase: "intraday", market_session: "open",
    phases: { premarket: emptySlot, intraday: emptySlot, postclose: emptySlot },
    polling: { focus_interval_seconds: 60, universe_interval_seconds: 240, stale_after_seconds: 180, next_check_seconds: 60 },
    ...overrides,
  };
}

describe("DecisionWorkbench", () => {
  it("renders research advice and evidence without plan or gate fields", async () => {
    const item = advice();
    const slot: PhaseSlot = { ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1", advice: [item], evidence: item.supporting_evidence };
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({ phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot } }))} />);

    expect(await screen.findByText("600000 · 保持观察")).toBeInTheDocument();
    expect(screen.getByText("价格有效")).toBeInTheDocument();
    expect(screen.queryByText(/模拟操作计划|行情门禁|仓位/)).not.toBeInTheDocument();
  });

  it("shows baseline evidence and only the latest quote in current intraday advice", async () => {
    const item = advice({
      supporting_evidence: [
        { evidence_id: "factor-1", evidence_kind: "candidate_factor", source: "baidu", snapshot_id: "candidate-1", summary: "候选因子有效", observed_at: "2026-07-15T09:20:00+08:00" },
        { evidence_id: "tencent-old", source: "tencent", snapshot_id: "tencent-old", summary: "旧行情 10.10", observed_at: "2026-07-15T10:10:00+08:00" },
        { evidence_id: "tencent-latest", source: "tencent", snapshot_id: "tencent-latest", summary: "最新行情 10.30", observed_at: "2026-07-15T10:29:00+08:00" },
      ],
    });
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1",
      advice: [item], evidence: item.supporting_evidence,
    };
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot },
    }))} />);

    expect(await screen.findByText("候选因子有效")).toBeInTheDocument();
    expect(screen.getByText("最新行情 10.30")).toBeInTheDocument();
    expect(screen.queryByText("旧行情 10.10")).not.toBeInTheDocument();
  });

  it("does not mark unchanged market-wide advice stale after a recent universe poll", async () => {
    const item = advice();
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1",
      generated_at: "2026-07-15T10:00:00+08:00", advice: [item], evidence: item.supporting_evidence,
    };
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot },
      polling: {
        status: "normal", focus_interval_seconds: 60, universe_interval_seconds: 240,
        stale_after_seconds: 180, next_check_seconds: 60,
        last_focus_success_at: "2026-07-15T10:29:55+08:00",
        last_universe_success_at: "2026-07-15T10:29:00+08:00",
      },
    }))} />);

    expect(await screen.findByText("600000 · 保持观察")).toBeInTheDocument();
    expect(screen.queryByText("聚合数据已过期")).not.toBeInTheDocument();
    expect(screen.queryByText("行情更新已超过有效时间")).not.toBeInTheDocument();
  });

  it("uses the focus poll for selected-stock freshness", async () => {
    const item = advice();
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1",
      generated_at: "2026-07-15T10:00:00+08:00", advice: [item], evidence: item.supporting_evidence,
    };
    render(<DecisionWorkbench selectedSymbol="600000" loadCurrent={() => Promise.resolve(response({
      phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot },
      polling: {
        status: "normal", focus_interval_seconds: 60, universe_interval_seconds: 240,
        stale_after_seconds: 180, next_check_seconds: 60,
        last_focus_success_at: "2026-07-15T10:29:30+08:00",
        last_universe_success_at: "2026-07-15T10:00:00+08:00",
      },
    }))} />);

    expect(await screen.findByText("600000 · 保持观察")).toBeInTheDocument();
    expect(screen.queryByText("聚合数据已过期")).not.toBeInTheDocument();
    expect(screen.queryByText("行情更新已超过有效时间")).not.toBeInTheDocument();
  });

  it("warns when the relevant live quote poll exceeds its effective threshold", async () => {
    const item = advice();
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1",
      generated_at: "2026-07-15T10:25:00+08:00", advice: [item], evidence: item.supporting_evidence,
    };
    render(<DecisionWorkbench selectedSymbol="600000" loadCurrent={() => Promise.resolve(response({
      phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot },
      polling: {
        status: "degraded", focus_interval_seconds: 60, universe_interval_seconds: 240,
        stale_after_seconds: 180, next_check_seconds: 60,
        last_focus_success_at: "2026-07-15T10:26:00+08:00",
        last_universe_success_at: "2026-07-15T10:29:30+08:00",
      },
    }))} />);

    expect(await screen.findByText("行情更新已超过有效时间")).toBeInTheDocument();
    expect(screen.getByText(/焦点行情最近成功于/)).toHaveTextContent("2026/7/15 10:26:00");
    expect(screen.queryByText("聚合数据已过期")).not.toBeInTheDocument();
  });

  it("explains a selected stock polling failure in beginner language", async () => {
    const item = advice();
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1",
      generated_at: "2026-07-15T10:29:00+08:00", advice: [item], evidence: item.supporting_evidence,
    };
    render(<DecisionWorkbench selectedSymbol="600000" loadCurrent={() => Promise.resolve(response({
      phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot },
      polling: {
        status: "degraded", focus_interval_seconds: 120, universe_interval_seconds: 240,
        stale_after_seconds: 180, next_check_seconds: 120,
        consecutive_focus_failures: 2, consecutive_universe_failures: 0,
        focus_error_code: "incomplete_quote_batch_error", universe_error_code: null,
        last_focus_success_at: "2026-07-15T10:29:00+08:00",
        last_universe_success_at: "2026-07-15T10:29:00+08:00",
      },
    }))} />);

    expect(await screen.findByText("焦点行情更新暂时失败")).toBeInTheDocument();
    expect(screen.getByText(/已连续失败 2 次/)).toBeInTheDocument();
    expect(screen.getByText(/部分股票行情缺失，完整性检查未通过/)).toBeInTheDocument();
    expect(screen.getByText("焦点行情异常 · 2 次")).toBeInTheDocument();
  });

  it("does not attribute a focus failure to the market-wide view", async () => {
    const item = advice();
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1",
      generated_at: "2026-07-15T10:29:00+08:00", advice: [item], evidence: item.supporting_evidence,
    };
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot },
      polling: {
        status: "degraded", focus_interval_seconds: 120, universe_interval_seconds: 240,
        stale_after_seconds: 180, next_check_seconds: 120,
        consecutive_focus_failures: 2, consecutive_universe_failures: 0,
        focus_error_code: "timeout_error", universe_error_code: null,
        last_focus_success_at: "2026-07-15T10:29:00+08:00",
        last_universe_success_at: "2026-07-15T10:29:00+08:00",
      },
    }))} />);

    expect(await screen.findByText("全市场行情正常")).toBeInTheDocument();
    expect(screen.queryByText("焦点行情更新暂时失败")).not.toBeInTheDocument();
    expect(screen.queryByText("轮询 degraded")).not.toBeInTheDocument();
  });

  it("does not show a live freshness warning for a frozen premarket phase", async () => {
    const item = advice({ horizon: "swing" });
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1",
      generated_at: "2026-07-15T09:20:00+08:00", advice: [item], evidence: item.supporting_evidence,
    };
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      current_phase: "premarket",
      phases: { premarket: slot, intraday: emptySlot, postclose: emptySlot },
    }))} />);

    expect(await screen.findByText("600000 · 保持观察")).toBeInTheDocument();
    expect(screen.getByText("当前阶段不检查实时行情")).toBeInTheDocument();
    expect(screen.queryByText("聚合数据已过期")).not.toBeInTheDocument();
    expect(screen.queryByText("行情更新已超过有效时间")).not.toBeInTheDocument();
  });

  it("explains that an empty premarket phase is scheduled rather than broken", async () => {
    const scheduled = {
      ...emptySlot,
      execution: {
        status: "scheduled", scheduled_at: "2026-07-17T09:20:00+08:00",
        next_scheduled_at: "2026-07-17T09:20:00+08:00", last_completed_at: null,
        last_attempt_at: null, attempts: 0, error_code: null,
      },
    } as PhaseSlot;
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      server_time: "2026-07-17T09:00:00+08:00", trading_date: "2026-07-17",
      current_phase: "premarket", market_session: "closed",
      phases: { premarket: scheduled, intraday: emptySlot, postclose: emptySlot },
    }))} />);

    expect(await screen.findByText("盘前研判计划 09:20 生成")).toBeInTheDocument();
    expect(screen.getByText("尚未到计划时间，不会提前编造结论。")).toBeInTheDocument();
  });

  it("keeps every phase lifecycle visible before the user switches tabs", async () => {
    const scheduled = {
      ...emptySlot,
      execution: {
        status: "scheduled", scheduled_at: "2026-07-17T09:20:00+08:00",
        next_scheduled_at: "2026-07-17T09:20:00+08:00", last_completed_at: null,
        last_attempt_at: null, attempts: 0, error_code: null,
      },
    } as PhaseSlot;
    const item = advice();
    const ready = {
      ...emptySlot, phase_status: "ready" as const, quality: "ready" as const,
      aggregate_version: "s1", advice: [item], evidence: item.supporting_evidence,
    };
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      server_time: "2026-07-17T10:30:00+08:00", trading_date: "2026-07-17",
      phases: { premarket: scheduled, intraday: ready, postclose: emptySlot },
    }))} />);

    expect(await screen.findByText("计划 09:20 生成")).toBeInTheDocument();
    expect(screen.getByText("已生成 1 条建议")).toBeInTheDocument();
    expect(screen.getByText("暂无已验证结果")).toBeInTheDocument();
  });

  it("loads explicit history and returns to the current endpoint", async () => {
    const loadCurrent = vi.fn().mockResolvedValue(response());
    const loadDate = vi.fn().mockResolvedValue(response({ trading_date: "2026-07-14", market_session: "closed" }));
    render(<DecisionWorkbench loadCurrent={loadCurrent} loadDate={loadDate} />);
    await screen.findByRole("tab", { name: "盘中监测" });

    fireEvent.change(screen.getByLabelText("交易日期"), { target: { value: "2026-07-14" } });
    expect(await screen.findByRole("button", { name: "返回实时" })).toBeInTheDocument();
    expect(loadDate).toHaveBeenCalledWith("2026-07-14");
    fireEvent.click(screen.getByRole("button", { name: "返回实时" }));
    expect(loadCurrent).toHaveBeenCalledTimes(2);
  });

  it("filters advice and change history to the selected A-share", async () => {
    const selected = advice();
    const foreign = advice({ advice_id: "a2", symbol: "000001", conclusion: "其他股票" });
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s1",
      advice: [selected, foreign], evidence: [...selected.supporting_evidence, ...foreign.supporting_evidence],
      change_stream: [{ snapshot_id: "s1", sequence: 1, generated_at: selected.created_at, delta_advice: [selected, foreign] }],
    };
    render(<DecisionWorkbench selectedSymbol="600000" loadCurrent={() => Promise.resolve(response({ phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot } }))} />);

    expect(await screen.findByText("600000 · 保持观察")).toBeInTheDocument();
    expect(screen.queryByText("其他股票")).not.toBeInTheDocument();
    expect(screen.getByText(/变化版本 #1/)).toBeInTheDocument();
  });

  it("shows the newest three collapsed change versions and discloses older history", async () => {
    const versions = [1, 5, 2, 4, 3].map((sequence) => ({
      snapshot_id: `s${sequence}`, sequence,
      generated_at: `2026-07-15T10:3${sequence}:00+08:00`,
      delta_advice: [advice({ advice_id: `a${sequence}`, snapshot_id: `s${sequence}` })],
    }));
    const item = advice({ snapshot_id: "s5" });
    const slot: PhaseSlot = {
      ...emptySlot, phase_status: "ready", quality: "ready", aggregate_version: "s5",
      advice: [item], evidence: item.supporting_evidence, change_stream: versions,
    };
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      phases: { premarket: emptySlot, intraday: slot, postclose: emptySlot },
    }))} />);

    expect(await screen.findByText(/变化版本 #5/)).toBeInTheDocument();
    expect(screen.getByText(/变化版本 #4/)).toBeInTheDocument();
    expect(screen.getByText(/变化版本 #3/)).toBeInTheDocument();
    expect(screen.queryByText(/变化版本 #2/)).not.toBeInTheDocument();
    expect(screen.queryByText(/变化版本 #1/)).not.toBeInTheDocument();
    expect(Array.from(document.querySelectorAll(".change-stream details"))).toHaveLength(3);
    expect(Array.from(document.querySelectorAll(".change-stream details")).every(
      (details) => !details.hasAttribute("open"),
    )).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "查看更早 2 个版本" }));
    expect(screen.getByText(/变化版本 #2/)).toBeInTheDocument();
    expect(screen.getByText(/变化版本 #1/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "收起早期版本" }));
    expect(screen.queryByText(/变化版本 #2/)).not.toBeInTheDocument();
  });

  it("renders verified market, industry, news and risk context from the phase snapshot", async () => {
    const slot = {
      ...emptySlot, phase_status: "partial", quality: "partial", aggregate_version: "s1",
      context: {
        market_state: "range", window_start: "2026-07-14T15:00:00+08:00",
        window_end: "2026-07-15T09:20:00+08:00", candidate_snapshot_id: "candidates-1",
        risk_event_count: 1, quality_reasons: [],
        news: {
          status: "ready", missing_event_ids: [], error_code: null,
          events: [{
            event_id: "news-1", event_type: "company_update", headline: "已核验公司事件",
            occurred_at: "2026-07-15T08:40:00+08:00", industries: ["银行"], themes: ["业绩"],
            affected_symbols: ["600000"], association_confidence: "0.92",
            publisher: "权威来源", source_url: "https://example.com/news-1",
          }],
        },
      },
    } as unknown as PhaseSlot;
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      current_phase: "premarket", phases: { premarket: slot, intraday: emptySlot, postclose: emptySlot },
    }))} />);

    expect(await screen.findByRole("heading", { name: "市场震荡" })).toBeInTheDocument();
    expect(screen.getByText("已核验公司事件")).toBeInTheDocument();
    expect(screen.getByText("银行 · 业绩")).toBeInTheDocument();
    expect(screen.getByText("1 项风险证据")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "权威来源" })).toHaveAttribute("href", "https://example.com/news-1");
  });

  it("keeps unrelated company events out of selected-stock context", async () => {
    const slot = {
      ...emptySlot, phase_status: "partial", quality: "partial", aggregate_version: "s1",
      context: {
        market_state: "range", window_start: null, window_end: null,
        candidate_snapshot_id: "candidates-1", risk_event_count: 0, quality_reasons: [],
        news: {
          status: "ready", missing_event_ids: [], error_code: null,
          events: [
            { event_id: "n1", event_type: "company_update", headline: "浦发银行事件", occurred_at: "2026-07-15T08:40:00+08:00", industries: ["银行"], themes: [], affected_symbols: ["600000"], association_confidence: "0.9", publisher: null, source_url: null },
            { event_id: "n2", event_type: "company_update", headline: "平安银行事件", occurred_at: "2026-07-15T08:41:00+08:00", industries: ["银行"], themes: [], affected_symbols: ["000001"], association_confidence: "0.9", publisher: null, source_url: null },
          ],
        },
      },
    } as unknown as PhaseSlot;
    render(<DecisionWorkbench selectedSymbol="600000" loadCurrent={() => Promise.resolve(response({
      current_phase: "premarket", phases: { premarket: slot, intraday: emptySlot, postclose: emptySlot },
    }))} />);

    expect(await screen.findByText("浦发银行事件")).toBeInTheDocument();
    expect(screen.queryByText("平安银行事件")).not.toBeInTheDocument();
  });

  it("explains missing referenced news instead of inventing event content", async () => {
    const slot = {
      ...emptySlot, phase_status: "partial", quality: "partial", aggregate_version: "s1",
      context: {
        market_state: "insufficient_data", window_start: null, window_end: null,
        candidate_snapshot_id: null, risk_event_count: 0,
        quality_reasons: ["compliance_unavailable"],
        news: {
          status: "partial", events: [], missing_event_ids: ["news-missing"], error_code: null,
        },
      },
    } as unknown as PhaseSlot;
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response({
      current_phase: "premarket", phases: { premarket: slot, intraday: emptySlot, postclose: emptySlot },
    }))} />);

    expect(await screen.findByText("1 条快照新闻引用当前无法读取")).toBeInTheDocument();
    expect(screen.getByText("不会用推测内容补位。")).toBeInTheDocument();
    expect(screen.getByText("合规检查数据不可用")).toBeInTheDocument();
  });

  it("ignores a stale historical response after a newer date wins", async () => {
    let resolveOld!: (value: DecisionResponse) => void;
    const old = new Promise<DecisionResponse>((resolve) => { resolveOld = resolve; });
    const loadDate = vi.fn((value: string) => value === "2026-07-14" ? old : Promise.resolve(response({ trading_date: value })));
    render(<DecisionWorkbench loadCurrent={() => Promise.resolve(response())} loadDate={loadDate} />);
    await screen.findByRole("tab", { name: "盘中监测" });
    fireEvent.change(screen.getByLabelText("交易日期"), { target: { value: "2026-07-14" } });
    fireEvent.change(screen.getByLabelText("交易日期"), { target: { value: "2026-07-13" } });
    await act(async () => resolveOld(response({ trading_date: "2026-07-14" })));
    expect((screen.getByLabelText("交易日期") as HTMLInputElement).value).toBe("2026-07-13");
  });
});
