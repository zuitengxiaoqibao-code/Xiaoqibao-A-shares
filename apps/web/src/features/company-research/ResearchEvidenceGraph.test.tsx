import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResearchEvidenceGraph } from "./ResearchEvidenceGraph";
import type { EvidenceGraph } from "./types";

describe("ResearchEvidenceGraph", () => {
  it("renders directed evidence links and preserves unavailable conclusions", () => {
    const graph: EvidenceGraph = {
      nodes: [
        { node_id: "evidence:filing-1", kind: "evidence", label: "filing-1", claim: "filing-1", evidence_ids: ["filing-1"], observed_at: "2026-08-15T00:00:00Z", limitations: [] },
        { node_id: "conclusion:business_model", kind: "fact", label: "商业模式", claim: "主营业务来自原文。", evidence_ids: ["filing-1"], observed_at: "2026-08-15T00:00:00Z", limitations: [] },
        { node_id: "conclusion:industry_space", kind: "unavailable", label: "行业空间", claim: "行业原文不可用。", evidence_ids: [], observed_at: null, limitations: ["缺少行业来源"] },
      ],
      edges: [{ source_node_id: "evidence:filing-1", target_node_id: "conclusion:business_model", relation: "supports" }],
    };

    render(<ResearchEvidenceGraph graph={graph} />);

    expect(screen.getByRole("region", { name: "公司研究证据图" })).toBeInTheDocument();
    expect(screen.getByText("主营业务来自原文。")).toBeInTheDocument();
    expect(screen.getByText("支持 · filing-1")).toBeInTheDocument();
    expect(screen.getByText("缺少行业来源")).toBeInTheDocument();
    expect(screen.getByText("不可用")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "证据图关系" })).not.toHaveAttribute("open");
  });
});
