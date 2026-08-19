import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FieldEvidenceDetails } from "./FieldEvidenceDetails";


describe("FieldEvidenceDetails", () => {
  it("keeps field provenance compact until the user expands it", () => {
    render(<FieldEvidenceDetails entries={[{
      field_path: "sentiment.score",
      value: "76.00",
      source: "market-sentiment-cache",
      source_field: "score",
      status: "live",
      trade_date: "2026-08-12",
      observed_at: "2026-08-12T10:30:00+08:00",
      coverage_percent: "88.50",
      derived: true,
      formula: "a-share-sentiment-v2",
      evidence_ids: ["sentiment-2026-08-12"],
      limitations: [],
    }]} />);

    expect(screen.getByRole("group", { name: "关键字段证据" })).toHaveTextContent("1 项实时");
    expect(screen.getByRole("group", { name: "关键字段证据" })).not.toHaveAttribute("open");

    fireEvent.click(screen.getByText("关键字段真实性"));
    expect(screen.getByRole("group", { name: "关键字段证据" })).toHaveAttribute("open");
    expect(screen.getByText("市场情绪评分")).toHaveAttribute("title", "sentiment.score");
    expect(screen.getByText("本地市场情绪快照")).toHaveAttribute("title", "market-sentiment-cache");
    expect(screen.getByText("情绪评分")).toHaveAttribute("title", "score");
    expect(screen.getByText("A股市场情绪模型 v2")).toHaveAttribute("title", "a-share-sentiment-v2");
    expect(screen.queryByText("sentiment.score")).not.toBeInTheDocument();
    expect(screen.queryByText("market-sentiment-cache")).not.toBeInTheDocument();
    expect(screen.getByText("原始字段")).toBeInTheDocument();
    expect(screen.getByText("88.50%")).toBeInTheDocument();
  });

  it("makes missing and conflicting evidence visible without fabricating a value", () => {
    render(<FieldEvidenceDetails entries={[
      {
        field_path: "liquidity.relative_amount", value: null, source: "unavailable", source_field: "relative_amount",
        status: "missing", trade_date: null, observed_at: null, coverage_percent: null, derived: false,
        formula: null, evidence_ids: [], limitations: ["20 日成交基准尚未形成"],
      },
      {
        field_path: "breadth.rising_count", value: 3000, source: "tdx-local-rpc", source_field: "rising_count",
        status: "conflict", trade_date: "2026-08-12", observed_at: "2026-08-12T10:30:00+08:00", coverage_percent: "98.00",
        derived: false, formula: null, evidence_ids: [], limitations: ["备用来源相差 12 家，采用本地全市场快照"],
      },
    ]} defaultOpen />);

    expect(screen.getByRole("group", { name: "关键字段证据" })).toHaveTextContent("1 项缺失");
    expect(screen.getByRole("group", { name: "关键字段证据" })).toHaveTextContent("1 项冲突");
    expect(screen.getByText("20 日成交基准尚未形成")).toBeInTheDocument();
    expect(screen.getByText("备用来源相差 12 家，采用本地全市场快照")).toBeInTheDocument();
    expect(screen.getByTitle("breadth.rising_count")).toHaveTextContent("上涨家数");
    expect(screen.getAllByText("--").length).toBeGreaterThan(0);
  });

  it("shows the selected and alternative values for a real source conflict", () => {
    render(<FieldEvidenceDetails entries={[{
      field_path: "valuation.pe_ttm", value: "12.50", source: "tdx-local-rpc-detail",
      source_field: "pe_ttm", status: "conflict", trade_date: "2026-08-12",
      observed_at: "2026-08-12T10:30:00+08:00", coverage_percent: null,
      derived: false, formula: null, evidence_ids: [], limitations: ["估值来源存在差异"],
      alternatives: [{ value: "12.90", source: "tencent", source_field: "pe_ttm", observed_at: "2026-08-12T10:30:00+08:00" }],
      difference: "-0.40 (-3.10%)", selection_reason: "采用本地通达信估值明细",
      affects_conclusion: false,
    }]} defaultOpen />);

    expect(screen.getByText("12.90 · 腾讯行情")).toBeInTheDocument();
    expect(screen.getByText("-0.40 (-3.10%)")).toBeInTheDocument();
    expect(screen.getByText("采用本地通达信估值明细")).toBeInTheDocument();
    expect(screen.getByText("不影响当前结论")).toBeInTheDocument();
  });

  it("uses a Chinese fallback for unknown internal identifiers", () => {
    render(<FieldEvidenceDetails entries={[{
      field_path: "experimental.unknown_metric", value: "1", source: "vendor-unknown-feed",
      source_field: "mystery_value", status: "derived", trade_date: null, observed_at: null,
      coverage_percent: null, derived: true, formula: "experimental-formula-v9",
      evidence_ids: [], limitations: ["unknown_backend_blocker"],
    }]} defaultOpen />);

    expect(screen.getByText("未识别指标")).toHaveAttribute("title", "experimental.unknown_metric");
    expect(screen.getByText("未识别数据来源")).toHaveAttribute("title", "vendor-unknown-feed");
    expect(screen.getByText("未识别原始字段")).toHaveAttribute("title", "mystery_value");
    expect(screen.getByText("未登记公式版本")).toHaveAttribute("title", "experimental-formula-v9");
    expect(screen.getByText("数据完整性限制")).toHaveAttribute("title", "unknown_backend_blocker");
  });
});
