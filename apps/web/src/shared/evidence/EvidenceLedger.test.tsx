import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvidenceLedger } from "./EvidenceLedger";

describe("EvidenceLedger", () => {
  it("renders compact provenance rows and limitations", () => {
    render(<EvidenceLedger entries={[{
      source: "tdx-local-daily",
      operation: "market_review",
      status: "ready",
      trade_date: "2026-08-10",
      observed_at: "2026-08-10T07:00:00Z",
      formula_version: "a-share-market-review-v2",
      sample_count: 5000,
      total_count: 5200,
      coverage_percent: 96.2,
      limitations: [],
    }, {
      source: "tdx-local-professional",
      operation: "professional_probe",
      status: "unavailable",
      trade_date: null,
      observed_at: null,
      formula_version: null,
      sample_count: null,
      total_count: null,
      coverage_percent: null,
      limitations: ["专业数据包未初始化"],
    }]} />);

    expect(screen.getByRole("region", { name: "证据账本" })).toBeInTheDocument();
    expect(screen.getByText("市场复盘")).toHaveAttribute("title", "market_review");
    expect(screen.getByText("本地通达信日线")).toHaveAttribute("title", "tdx-local-daily");
    expect(screen.getByText("A股市场复盘模型 v2")).toHaveAttribute("title", "a-share-market-review-v2");
    expect(screen.getByText("通达信专业数据探测")).toHaveAttribute("title", "professional_probe");
    expect(screen.queryByText("market_review")).not.toBeInTheDocument();
    expect(screen.getByText("5,000 条样本")).toBeInTheDocument();
    expect(screen.getByText("96.2% 覆盖")).toBeInTheDocument();
    expect(screen.getByText("专业数据包未初始化")).toBeInTheDocument();
  });

  it("translates machine-readable blocker codes while preserving the raw code for audit", () => {
    render(<EvidenceLedger entries={[{
      source: "market-sentiment-cache",
      operation: "market_review",
      status: "partial",
      trade_date: "2026-08-12",
      observed_at: null,
      formula_version: null,
      sample_count: null,
      limitations: ["history_dates_fragmented", "history_coverage_below_98_percent"],
    }]} defaultOpen />);

    expect(screen.getByText("历史日期存在零散分片")).toHaveAttribute("title", "history_dates_fragmented");
    expect(screen.getByText("历史覆盖率低于 98% 就绪门槛")).toHaveAttribute("title", "history_coverage_below_98_percent");
  });
});
