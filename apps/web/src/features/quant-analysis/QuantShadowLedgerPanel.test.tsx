import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QuantShadowLedgerPanel } from "./QuantShadowLedgerPanel";

describe("QuantShadowLedgerPanel", () => {
  it("shows frozen decisions and only displays evaluated outcome windows", () => {
    render(<QuantShadowLedgerPanel loading={false} error="" records={[{
      decision_id: "shadow-1",
      as_of: "2026-08-01",
      symbol: "600519",
      formula_version: "a-share-short-strategy-v2.0",
      candidate_status: "watch",
      strategy_score: "76.5",
      reference_price: "1500",
      frozen_at: "2026-08-01T15:10:00+08:00",
      outcomes: [
        { decision_id: "shadow-1", horizon: 1, status: "ready", evaluated_trade_date: "2026-08-04", return_percent: "1.25", mfe_percent: "2.1", mae_percent: "-0.8", invalidation_state: "unavailable", evaluated_at: "2026-08-04T15:10:00+08:00", limitation: null },
        { decision_id: "shadow-1", horizon: 5, status: "pending", evaluated_trade_date: null, return_percent: null, mfe_percent: null, mae_percent: null, invalidation_state: "unavailable", evaluated_at: null, limitation: "未来交易日不足" },
      ],
    }]} />);

    expect(screen.getByText("策略影子跟踪")).toBeInTheDocument();
    expect(screen.getByText("600519")).toBeInTheDocument();
    expect(screen.getByText("+1.25%")).toBeInTheDocument();
    expect(screen.getByText("5日")).toBeInTheDocument();
    expect(screen.getByText("待评估")).toBeInTheDocument();
    expect(screen.queryByText("+0.00%")).not.toBeInTheDocument();
  });

  it("shows score calibration and drift without claiming reliability on thin buckets", () => {
    render(<QuantShadowLedgerPanel
      loading={false}
      error=""
      records={[]}
      analytics={{
        status: "partial",
        horizon: 5,
        mature_sample_count: 23,
        pending_sample_count: 4,
        hit_rate_percent: "56.52",
        average_return_percent: "1.24",
        average_mfe_percent: "3.40",
        average_mae_percent: "-1.70",
        brier_score: "0.2180",
        buckets: [
          { label: "70-79", score_min: 70, score_max: 79, sample_count: 8, average_score: "75.25", hit_rate_percent: "62.50", average_return_percent: "1.80", average_mfe_percent: "3.60", average_mae_percent: "-1.20", calibration_gap_percent: "12.75", status: "ready" },
          { label: "90-100", score_min: 90, score_max: 100, sample_count: 2, average_score: "92.00", hit_rate_percent: null, average_return_percent: null, average_mfe_percent: null, average_mae_percent: null, calibration_gap_percent: null, status: "insufficient" },
        ],
        regime_performance: [
          { regime: "情绪主升", sample_count: 8, hit_rate_percent: "62.50", average_return_percent: "1.80", expected_value_percent: "1.80", profit_loss_ratio: "1.60", max_consecutive_losses: 2, max_drawdown_percent: "4.20", sharpe_ratio: "0.58" },
          { regime: "高位退潮", sample_count: 3, hit_rate_percent: "0", average_return_percent: "-2.10", expected_value_percent: "-2.10", profit_loss_ratio: null, max_consecutive_losses: 3, max_drawdown_percent: "6.18", sharpe_ratio: "-1.20" },
        ],
        drift: { status: "warning", recent_sample_count: 10, baseline_sample_count: 13, recent_hit_rate_percent: "50.00", baseline_hit_rate_percent: "61.54", recent_average_return_percent: "0.20", baseline_average_return_percent: "2.04", reasons: ["近期命中率较基线下降 10 至 20 个百分点"] },
        generated_at: "2026-08-11T15:10:00+08:00",
        limitations: ["部分评分区间样本不足"],
      }}
    />);

    expect(screen.getByText("评分校准与漂移")).toBeInTheDocument();
    expect(screen.getByText("23 条")).toBeInTheDocument();
    expect(screen.getByText("56.52%")).toBeInTheDocument();
    expect(screen.getByText("漂移预警")).toBeInTheDocument();
    expect(screen.getByText("样本不足", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "分市场风格真实绩效" })).toHaveTextContent("情绪主升");
    expect(screen.getByRole("region", { name: "分市场风格真实绩效" })).toHaveTextContent("EV +1.80%");
    expect(screen.getByRole("region", { name: "分市场风格真实绩效" })).toHaveTextContent("高位退潮");
    expect(screen.getByRole("region", { name: "分市场风格真实绩效" })).toHaveTextContent("连续亏损 3");
  });

  it("records a manual review action without implying automatic trading", async () => {
    const onJournalCreate = vi.fn(async () => undefined);
    render(<QuantShadowLedgerPanel
      loading={false}
      error=""
      records={[]}
      journalRecords={[]}
      journalSymbol="600519"
      onJournalCreate={onJournalCreate}
    />);

    fireEvent.change(screen.getByLabelText("复盘动作"), { target: { value: "no_trade" } });
    fireEvent.change(screen.getByLabelText("复盘备注"), { target: { value: "触发条件不完整，今日不交易" } });
    fireEvent.click(screen.getByRole("button", { name: "写入复盘日志" }));

    await waitFor(() => expect(onJournalCreate).toHaveBeenCalledWith(expect.objectContaining({
      symbol: "600519",
      action: "no_trade",
      note: "触发条件不完整，今日不交易",
    })));
    expect(screen.getByText("只记录人工决策，不连接交易下单")).toBeInTheDocument();
  });

  it("shows calibration integrity separately from shadow outcome statistics", () => {
    render(<QuantShadowLedgerPanel loading={false} error="" records={[]} calibration={{
      status: "partial", horizon: 5, total_sample_count: 4, mature_sample_count: 4, splits: [],
      integrity: { future_function_check: "passed", survivorship_check: "unavailable", duplicate_decision_check: "passed", limitations: ["样本不足"] },
      generated_at: "2026-08-14T08:00:00Z", limitations: ["样本不足"],
    }} />);
    expect(screen.getByRole("region", { name: "量化走样校准报告" })).toHaveTextContent("未来函数检查通过");
    expect(screen.getByRole("region", { name: "量化走样校准报告" })).toHaveTextContent("生存者偏差检查不可用");
    expect(screen.getAllByText("样本不足")).toHaveLength(1);
  });
});
