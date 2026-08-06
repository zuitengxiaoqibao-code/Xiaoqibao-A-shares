import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  ChartPanel,
  DataStateNotice,
  EvidenceBadge,
  GaugeRow,
  MetricBand,
  RankBarList,
} from "./VisualPrimitives";
import type { EvidenceState } from "./types";

const state = (status: EvidenceState["status"]): EvidenceState => ({
  status,
  source: "通达信本地行情",
  observedAt: "2026-08-06T09:31:00+08:00",
  coverage: 86,
  warnings: [],
});

describe("VisualPrimitives", () => {
  it.each(["ready", "partial", "stale", "unavailable", "error"] as const)(
    "renders %s evidence as text and aria state",
    (status) => {
      render(<DataStateNotice state={state(status)} title="行情状态" />);
      const notice = screen.getByRole("status", { name: "行情状态" });
      expect(notice).toHaveAttribute("data-status", status);
      expect(notice).toHaveTextContent({
        ready: "数据已就绪",
        partial: "数据部分可用",
        stale: "使用历史数据",
        unavailable: "数据不可用",
        error: "数据加载失败",
      }[status]);
      expect(notice).toHaveTextContent("通达信本地行情");
    },
  );

  it("offers retry for errors", () => {
    const onRetry = vi.fn();
    render(<DataStateNotice state={state("error")} title="加载失败" onRetry={onRetry} />);
    screen.getByRole("button", { name: "重试加载失败" }).click();
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("does not expose NaN coverage when an upstream value is invalid", () => {
    render(<DataStateNotice state={{ ...state("partial"), coverage: Number.NaN }} />);
    expect(screen.getByRole("status")).not.toHaveTextContent("NaN");
    expect(screen.getByRole("status")).toHaveTextContent("覆盖未知");
  });

  it("keeps chart title and content inside a labelled panel", () => {
    render(
      <ChartPanel title="板块强度" subtitle="今日" ariaLabel="板块强度图表">
        <div data-testid="chart-content">chart</div>
      </ChartPanel>,
    );
    expect(screen.getByRole("region", { name: "板块强度图表" })).toHaveTextContent("板块强度");
    expect(screen.getByTestId("chart-content")).toBeInTheDocument();
  });

  it("renders metric tones and never turns null into a synthetic number", () => {
    render(
      <MetricBand
        items={[
          { label: "上涨家数", value: 123, tone: "up" },
          { label: "成交额", value: null, tone: "unavailable" },
        ]}
      />,
    );
    expect(screen.getByText("123")).toBeInTheDocument();
    expect(screen.getByText("数据不可用")).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("renders gauge bars with missing values as unavailable", () => {
    render(<GaugeRow label="风险" value={null} tone="warning" />);
    const gauge = screen.getByRole("meter", { name: "风险" });
    expect(gauge).toHaveAttribute("aria-valuetext", "数据不可用");
    expect(screen.getByText("数据不可用")).toBeInTheDocument();
  });

  it("keeps null rank values visibly unavailable instead of zero", () => {
    render(
      <RankBarList
        items={[
          { label: "金融", value: 72 },
          { label: "医药", value: null },
        ]}
      />,
    );
    expect(screen.getByText("72")).toBeInTheDocument();
    expect(screen.getByText("--")).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it.each(["ready", "partial", "stale", "unavailable", "error"] as const)(
    "renders evidence badge label for %s",
    (status) => {
      render(<EvidenceBadge status={status} />);
      expect(screen.getByRole("status")).toHaveAttribute("data-status", status);
    },
  );
});
