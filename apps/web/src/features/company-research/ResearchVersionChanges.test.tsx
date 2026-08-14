import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResearchVersionChanges } from "./ResearchVersionChanges";

describe("ResearchVersionChanges", () => {
  it("separates conclusion, data and source changes from the previous frozen version", () => {
    render(<ResearchVersionChanges version={{
      snapshot_id: "research-2",
      version_number: 2,
      previous_snapshot_id: "research-1",
      content_hash: "a".repeat(64),
      generated_at: "2026-08-12T15:00:00+08:00",
      changes: [
        { category: "conclusion", label: "商业模式", before: "ready · 主营白酒", after: "partial · 渠道结构发生变化" },
        { category: "data", label: "最终评分", before: "72.50", after: "69.00" },
        { category: "source", label: "来源集合", before: "腾讯", after: "腾讯；通达信" },
      ],
    }} />);

    const region = screen.getByRole("region", { name: "研究版本变化" });
    expect(region).toHaveTextContent("研究版本 V2");
    expect(region).toHaveTextContent("结论变化");
    expect(region).toHaveTextContent("数据变化");
    expect(region).toHaveTextContent("来源变化");
    expect(region).toHaveTextContent("72.50");
    expect(region).toHaveTextContent("69.00");
  });
});
