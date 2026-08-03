import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { KronosForecastResponse } from "./types";
import { KronosForecastPanel } from "./KronosForecastPanel";

vi.mock("./QuantChart", () => ({
  QuantChart: ({ ariaLabel }: { ariaLabel: string }) => <div role="img" aria-label={ariaLabel} />,
}));

function readyForecast(): KronosForecastResponse {
  return {
    status: "ready",
    symbol: "600000",
    as_of: "2026-07-24",
    observed_through: "2026-07-24",
    model: "Kronos-mini",
    frequency: "1d",
    lookback_bars: 250,
    horizon_bars: 5,
    sample_count: 20,
    summary: {
      median_return_pct: "3.40",
      upper_return_pct: "11.20",
      lower_return_pct: "-6.10",
      path_dispersion_pct: "17.30",
      downside_probability_pct: "35.00",
    },
    points: [
      { trade_date: "2026-07-27", median_close: "10.42", lower_close: "10.12", upper_close: "10.71" },
      { trade_date: "2026-07-28", median_close: "10.50", lower_close: "10.00", upper_close: "11.00" },
    ],
    reasons: [],
    sources: ["local-daily-bars", "kronos"],
    warnings: [],
  };
}

describe("KronosForecastPanel", () => {
  it("renders a path chart and risk summary when ready", () => {
    render(<KronosForecastPanel forecast={readyForecast()} loading={false} error="" />);

    expect(screen.getByRole("img", { name: "Kronos 价格路径预测" })).toBeInTheDocument();
    expect(screen.getByText("预测中位收益")).toBeInTheDocument();
    expect(screen.getByText("+3.40%")).toBeInTheDocument();
    expect(screen.getByText("下行概率")).toBeInTheDocument();
  });

  it("explains unavailable configuration without showing a fake chart", () => {
    render(<KronosForecastPanel
      forecast={{ ...readyForecast(), status: "unavailable", summary: null, points: [], reasons: ["kronos_repo_not_configured"] }}
      loading={false}
      error=""
    />);

    expect(screen.getByText("Kronos 模型未启用")).toBeInTheDocument();
    expect(screen.getByText(/未配置 Kronos 源码目录/)).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Kronos 价格路径预测" })).not.toBeInTheDocument();
  });

  it("keeps insufficient history explicit", () => {
    render(<KronosForecastPanel
      forecast={{ ...readyForecast(), status: "insufficient", summary: null, points: [], reasons: ["daily_history_insufficient"] }}
      loading={false}
      error=""
    />);

    expect(screen.getByText("历史日线不足")).toBeInTheDocument();
    expect(screen.getByText(/日线历史长度不足/)).toBeInTheDocument();
  });

  it("shows a retryable load error without inventing forecast numbers", () => {
    render(<KronosForecastPanel forecast={null} loading={false} error="预测接口暂不可用" />);

    expect(screen.getByText("预测接口暂不可用")).toBeInTheDocument();
    expect(screen.queryByText(/预测中位收益/)).not.toBeInTheDocument();
  });
});
