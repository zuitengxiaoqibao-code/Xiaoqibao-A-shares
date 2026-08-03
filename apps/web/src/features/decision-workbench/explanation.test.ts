import { describe, expect, it } from "vitest";

import { beginnerAdviceExplanation } from "./explanation";
import type { Advice } from "./types";

const advice = {
  advice_id: "a1", snapshot_id: "s1", asset: "a_share", symbol: "600519",
  horizon: "intraday", observation_state: "waiting", action: "wait",
  conclusion: "小幅走弱，暂不追涨", confidence: "0.42",
  supporting_evidence: [], contrary_evidence: [], risks: ["市场波动"],
  invalidation_conditions: ["行情变化"],
  plain_language_explanation: "最新价 1252.31，盘中涨跌 -0.5305840395872882230994686217%。",
  quantitative_result: {
    price: "1252.31", change_percent: "-0.5305840395872882230994686217",
  },
  ai_interpretation_id: null, strategy_version: "v1",
  created_at: "2026-07-17T11:25:55+08:00", risk_decision_id: null,
  previous_advice_id: null, changed_fields: [],
} satisfies Advice;

describe("beginnerAdviceExplanation", () => {
  it("rounds structured intraday percentages without changing stored evidence", () => {
    expect(beginnerAdviceExplanation(advice, "intraday")).toBe(
      "最新价 1252.31，盘中涨跌 -0.53%。当前建议是小幅走弱，暂不追涨，不是立即交易指令。",
    );
    expect(advice.quantitative_result.change_percent).toBe(
      "-0.5305840395872882230994686217",
    );
  });

  it("preserves the recorded explanation outside the intraday phase", () => {
    expect(beginnerAdviceExplanation(advice, "postclose")).toBe(
      advice.plain_language_explanation,
    );
  });

  it("keeps the AI supplement after rounding the deterministic intraday values", () => {
    const withAI = {
      ...advice,
      plain_language_explanation: `${advice.plain_language_explanation}模型补充：量价变化仍需结合风险观察。`,
      ai_interpretation_id: "decision-ai-1",
    };

    expect(beginnerAdviceExplanation(withAI, "intraday")).toBe(
      "最新价 1252.31，盘中涨跌 -0.53%。当前建议是小幅走弱，暂不追涨，不是立即交易指令。模型补充：量价变化仍需结合风险观察。",
    );
  });
});
