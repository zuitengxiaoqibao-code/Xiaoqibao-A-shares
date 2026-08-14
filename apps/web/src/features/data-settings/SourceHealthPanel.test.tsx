import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SourceHealthPanel } from "./SourceHealthPanel";
import type { SourceHealthResponse } from "./types";

const response: SourceHealthResponse = {
  generated_at: "2026-08-11T05:00:00Z",
  window_size: 20,
  sources: [
    {
      source: "tdx",
      operation: "daily-bars",
      target: "A股全市场",
      status: "ready",
      attempts: 20,
      successes: 20,
      failures: 0,
      empty_responses: 0,
      success_rate: 100,
      average_latency_ms: 42,
      latest_latency_ms: 38,
      last_success_at: "2026-08-11T04:59:58Z",
      last_failure_at: null,
      last_error_code: null,
      latest_trade_date: "2026-08-10",
      field_count: 12,
      row_count: 5242,
      validation: "字段已校验",
    },
    {
      source: "sector-flow",
      operation: "snapshot",
      target: "板块资金",
      status: "degraded",
      attempts: 5,
      successes: 3,
      failures: 2,
      empty_responses: 0,
      success_rate: 60,
      average_latency_ms: 900,
      latest_latency_ms: 1200,
      last_success_at: "2026-08-11T04:58:00Z",
      last_failure_at: "2026-08-11T04:59:00Z",
      last_error_code: "remote_disconnect",
      latest_trade_date: null,
      field_count: null,
      row_count: null,
      validation: "保留上次有效缓存",
    },
    {
      source: "tdx-professional",
      operation: "financial",
      target: "专业字段",
      status: "unavailable",
      attempts: 3,
      successes: 0,
      failures: 3,
      empty_responses: 0,
      success_rate: 0,
      average_latency_ms: 20,
      latest_latency_ms: 18,
      last_success_at: null,
      last_failure_at: "2026-08-11T04:57:00Z",
      last_error_code: "plugin_not_initialized",
      latest_trade_date: null,
      field_count: null,
      row_count: null,
      validation: null,
    },
  ],
};

describe("SourceHealthPanel", () => {
  it("is collapsed by default and defers the health request until expanded", async () => {
    const load = vi.fn().mockResolvedValue(response);
    render(<SourceHealthPanel load={load} />);

    expect(screen.getByRole("region", { name: "数据源健康" })).toHaveAttribute("data-expanded", "false");
    expect(load).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "展开数据源健康" }));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("tdx · daily-bars")).toBeInTheDocument();
  });

  it("renders source evidence and keeps unavailable values explicit", async () => {
    const load = vi.fn().mockResolvedValue(response);
    render(<SourceHealthPanel load={load} />);

    fireEvent.click(screen.getByRole("button", { name: "展开数据源健康" }));
    expect(await screen.findByText("tdx · daily-bars")).toBeInTheDocument();
    expect(screen.getByText("就绪")).toBeInTheDocument();
    expect(screen.getByText("降级")).toBeInTheDocument();
    expect(screen.getByText("不可用")).toBeInTheDocument();
    const readyCard = screen.getByText("tdx · daily-bars").closest("article") as HTMLElement;
    const unavailableCard = screen.getByText("tdx-professional · financial").closest("article") as HTMLElement;
    expect(readyCard).toHaveTextContent("最新交易日：2026-08-10");
    expect(unavailableCard).toHaveTextContent("最近错误：plugin_not_initialized");
    expect(unavailableCard).toHaveTextContent("字段数：-- · 行数：--");
  });

  it("refreshes on demand and explains an empty health window", async () => {
    const load = vi.fn()
      .mockResolvedValueOnce({ ...response, sources: [] })
      .mockResolvedValueOnce(response);
    render(<SourceHealthPanel load={load} />);

    fireEvent.click(screen.getByRole("button", { name: "展开数据源健康" }));
    expect(await screen.findByText("当前窗口暂无数据源调用记录")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "刷新数据源健康" }));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("tdx · daily-bars")).toBeInTheDocument();
  });
});
