import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BondTaskFlow } from "./BondTaskFlow";

describe("BondTaskFlow", () => {
  it("renders a bounded overview and reports records kept outside the stack", () => {
    const cards = Array.from({ length: 11 }, (_, index) => ({
      code: `12${index}`,
      name: `转债 ${index}`,
      linkedStockCode: null,
      stateLabel: "未诊断",
      reason: null,
      tone: "pending" as const,
    }));

    render(<BondTaskFlow cards={cards} selectedCode={null} onSelect={vi.fn()} />);

    expect(screen.getAllByRole("button")).toHaveLength(7);
    expect(screen.getByText("展示 7 / 共 11 项真实记录")).toBeInTheDocument();
    expect(screen.getByText("其余 4 项保留在发现池")).toBeInTheDocument();
  });
});
