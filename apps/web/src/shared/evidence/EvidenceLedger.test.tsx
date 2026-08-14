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
    expect(screen.getByText("market_review")).toBeInTheDocument();
    expect(screen.getByText("5,000 条样本")).toBeInTheDocument();
    expect(screen.getByText("96.2% 覆盖")).toBeInTheDocument();
    expect(screen.getByText("专业数据包未初始化")).toBeInTheDocument();
  });
});
