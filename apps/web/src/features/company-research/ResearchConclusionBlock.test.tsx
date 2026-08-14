import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResearchConclusionBlock } from "./ResearchConclusionBlock";
import type { ResearchConclusion } from "./types";

const conclusions: ResearchConclusion[] = [
  {
    key: "business_model", label: "商业模式", kind: "fact",
    claim: "主营高端白酒。", evidence_ids: ["f10-company-overview"],
    source_count: 1, observed_at: "2026-08-03T00:00:00Z", limitations: [],
  },
  {
    key: "valuation_percentile", label: "估值分位", kind: "inference",
    claim: "当前估值高于同行中位。", evidence_ids: ["valuation-pe", "peer-pe"],
    source_count: 2, observed_at: "2026-08-03T00:00:00Z",
    limitations: ["缺少历史估值分位。"],
  },
  {
    key: "competitive_position", label: "竞争地位", kind: "unavailable",
    claim: "尚无市场份额证据。", evidence_ids: [], source_count: 0,
    observed_at: null, limitations: ["缺少可追溯证据编号。"],
  },
];

describe("ResearchConclusionBlock", () => {
  it("separates facts, inferences and unavailable claims with compact evidence counts", () => {
    render(<ResearchConclusionBlock conclusions={conclusions} />);

    expect(screen.getByRole("region", { name: "研究结论分层" })).toBeInTheDocument();
    expect(screen.getByText("事实")).toBeInTheDocument();
    expect(screen.getByText("推导")).toBeInTheDocument();
    expect(screen.getByText("不可用")).toBeInTheDocument();
    expect(screen.getByText("2项证据")).toBeInTheDocument();
    expect(screen.getByText("缺少可追溯证据编号。")).toBeInTheDocument();
  });
});
