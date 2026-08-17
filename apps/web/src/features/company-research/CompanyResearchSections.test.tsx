import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CompanyResearchSections } from "./CompanyResearchSections";
import type { CompanyResearchSection } from "./types";

const sections: CompanyResearchSection[] = [
  { key: "business_model", label: "商业模式", status: "ready", summary: "主营高端白酒", facts: ["收入来自酒类销售"], evidence_ids: ["f10-1"], limitation: null },
  { key: "industry_space", label: "行业空间", status: "partial", summary: "行业需求仍在增长", facts: [], evidence_ids: [], limitation: "缺少行业规模序列" },
  { key: "financial_trend", label: "财务趋势", status: "ready", summary: "营收利润同步增长", facts: [], evidence_ids: [], limitation: null },
  { key: "profit_quality", label: "利润质量", status: "ready", summary: "经营现金流覆盖利润", facts: [], evidence_ids: [], limitation: null },
  { key: "competitive_position", label: "竞争地位", status: "unavailable", summary: "不能确认竞争优势", facts: [], evidence_ids: [], limitation: "缺少市场份额" },
  { key: "valuation_percentile", label: "估值分位", status: "partial", summary: "当前估值已核验", facts: [], evidence_ids: [], limitation: "缺少历史估值序列" },
  { key: "future_catalysts", label: "未来催化", status: "ready", summary: "识别一项正向事件", facts: [], evidence_ids: [], limitation: null },
  { key: "contrary_risks", label: "反方风险", status: "triggered", summary: "触发一项风险", facts: ["利润与现金流背离"], evidence_ids: ["risk-1"], limitation: null },
  { key: "invalidation_conditions", label: "失效条件", status: "triggered", summary: "需要重新核验", facts: [], evidence_ids: [], limitation: null },
  { key: "verification_checklist", label: "核验清单", status: "ready", summary: "逐项回到原始来源复核", facts: ["核对财报原文"], evidence_ids: [], limitation: null },
];

describe("CompanyResearchSections", () => {
  it("shows the fixed ten-section research structure with explicit evidence limits", () => {
    render(<CompanyResearchSections sections={sections} />);

    expect(screen.getByRole("region", { name: "十段公司研究账本" })).toBeInTheDocument();
    expect(screen.getAllByRole("group")).toHaveLength(10);
    expect(screen.getByText("商业模式")).toBeInTheDocument();
    expect(screen.getByText("反方风险")).toBeInTheDocument();
    expect(screen.getByText("缺少市场份额")).toBeInTheDocument();
    expect(screen.getByText("核对财报原文")).toBeInTheDocument();

    const firstSummary = screen.getAllByRole("group")[0].querySelector("summary");
    expect(firstSummary).toHaveAttribute("data-layout", "ledger-card");
    expect(firstSummary?.querySelector('[data-part="chevron"]')).toBeInTheDocument();
    expect(firstSummary?.querySelector('[data-part="index"]')).toBeInTheDocument();
    expect(firstSummary?.querySelector('[data-part="content"]')).toBeInTheDocument();
    expect(firstSummary?.querySelector('[data-part="status"]')).toBeInTheDocument();
    expect(firstSummary?.children).toHaveLength(4);
    expect(screen.getAllByRole("group")[8]).toHaveAttribute("open");
  });
});
