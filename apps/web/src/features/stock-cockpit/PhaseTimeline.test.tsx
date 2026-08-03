import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PhaseTimeline } from "./PhaseTimeline";
import type { StockCockpitSnapshot } from "./types";

function advice() {
  return { advice_id: "a1", snapshot_id: "s1", asset: "a_share" as const, symbol: "600000", horizon: "intraday" as const, observation_state: "watching", action: "wait" as const, conclusion: "等待确认", confidence: "0.5", supporting_evidence: [{ evidence_id: "e1", source: "tencent", snapshot_id: "q1", summary: "价格变化", observed_at: "2026-07-15T10:29:00+08:00" }], contrary_evidence: [], risks: ["波动"], invalidation_conditions: ["条件变化"], plain_language_explanation: "这是通俗解释，不是盘后归因", quantitative_result: {}, ai_interpretation_id: null, risk_decision_id: null, strategy_version: "v1", created_at: "2026-07-15T10:30:00+08:00", previous_advice_id: "a0", changed_fields: ["conclusion"] };
}

describe("PhaseTimeline", () => {
  it("shows only the selected stock in a beginner three-phase summary", () => {
    const item = advice();
    const foreign = { ...item, advice_id: "a2", symbol: "000001" };
    const phases: StockCockpitSnapshot["phases"] = {
      premarket: { advice: [item, foreign], change_stream: [{ snapshot_id: "s1", sequence: 1, generated_at: item.created_at, status: "ready" }] },
      intraday: { advice: [], change_stream: [{ snapshot_id: "s2", sequence: 1, generated_at: item.created_at, status: "partial" }] },
      postclose: { advice: [], change_stream: [] },
    };
    render(<PhaseTimeline phases={phases} symbol="600000" />);
    expect(screen.getByText("盘前研判")).toBeInTheDocument();
    expect(screen.getByText("盘中观察")).toBeInTheDocument();
    expect(screen.getByText("盘后验证")).toBeInTheDocument();
    expect(screen.queryByText("000001")).not.toBeInTheDocument();
    expect(screen.getByText("暂不参与")).toBeInTheDocument();
    expect(screen.getByText("暂不参与").closest("article")).toHaveClass("action-wait");
    expect(screen.getByText("这是通俗解释，不是盘后归因")).toBeInTheDocument();
    expect(screen.queryByText(/前序建议|版本 #|变更字段/)).not.toBeInTheDocument();
    expect(screen.getByText("本阶段已运行，当时未纳入这只股票")).toBeInTheDocument();
    expect(screen.getByText("本阶段没有生成可核验记录")).toBeInTheDocument();
  });

  it("shows the authoritative scheduled time instead of a generic missing message", () => {
    const phases = {
      premarket: { advice: [], change_stream: [], execution: { status: "scheduled", scheduled_at: "2026-07-17T09:20:00+08:00", next_scheduled_at: "2026-07-17T09:20:00+08:00", last_completed_at: null, last_attempt_at: null, attempts: 0, error_code: null } },
      intraday: { advice: [], change_stream: [], execution: { status: "scheduled", scheduled_at: "2026-07-17T10:30:00+08:00", next_scheduled_at: "2026-07-17T10:30:00+08:00", last_completed_at: null, last_attempt_at: null, attempts: 0, error_code: null } },
      postclose: { advice: [], change_stream: [], execution: { status: "scheduled", scheduled_at: "2026-07-17T15:30:00+08:00", next_scheduled_at: "2026-07-17T15:30:00+08:00", last_completed_at: null, last_attempt_at: null, attempts: 0, error_code: null } },
    } as unknown as StockCockpitSnapshot["phases"];

    render(<PhaseTimeline phases={phases} symbol="600000" />);

    expect(screen.getByText("计划 09:20 生成")).toBeInTheDocument();
    expect(screen.getByText("计划 09:20 生成")).toHaveClass("execution-scheduled");
    expect(screen.getByText("计划 10:30 首次生成")).toBeInTheDocument();
    expect(screen.getByText("计划 15:30 生成")).toBeInTheDocument();
    expect(screen.queryByText("本阶段没有生成可核验记录")).not.toBeInTheDocument();
  });

  it("explains a blocked run while retaining the last verified advice", () => {
    const item = advice();
    const phases = {
      premarket: { advice: [], change_stream: [] },
      intraday: {
        advice: [item], phase_status: "blocked",
        quality_reasons: ["live_quotes_stale"],
        change_stream: [{ snapshot_id: "blocked-2", sequence: 2, generated_at: item.created_at, status: "blocked" }],
      },
      postclose: { advice: [], change_stream: [] },
    } as unknown as StockCockpitSnapshot["phases"];

    render(<PhaseTimeline phases={phases} symbol="600000" />);

    expect(screen.getByText(
      "本轮盘中观察已拦截：盘中行情已超过有效时间。下方保留最近一次可验证判断。",
    )).toBeInTheDocument();
    expect(screen.getByText(/本轮盘中观察已拦截/).closest("section")).toHaveClass("state-blocked");
    expect(screen.getByText("这是通俗解释，不是盘后归因")).toBeInTheDocument();
  });

  it("explains a blocked run without claiming the stock was absent", () => {
    const phases = {
      premarket: { advice: [], change_stream: [] },
      intraday: {
        advice: [], phase_status: "blocked",
        quality_reasons: ["live_quotes_unavailable"],
        change_stream: [{ snapshot_id: "blocked-1", sequence: 1, generated_at: "2026-07-15T10:30:00+08:00", status: "blocked" }],
      },
      postclose: { advice: [], change_stream: [] },
    } as unknown as StockCockpitSnapshot["phases"];

    render(<PhaseTimeline phases={phases} symbol="600000" />);

    expect(screen.getByText(
      "本轮盘中观察已拦截：盘中行情暂未返回。当前没有新的可验证判断。",
    )).toBeInTheDocument();
    expect(screen.queryByText("本阶段已运行，当时未纳入这只股票")).not.toBeInTheDocument();
  });
});
