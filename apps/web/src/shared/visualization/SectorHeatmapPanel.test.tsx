import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SectorHeatmapPanel } from "./SectorHeatmapPanel";

describe("SectorHeatmapPanel", () => {
  it("renders real sector changes as a red-up green-down heat board", () => {
    const onSelect = vi.fn();
    render(<SectorHeatmapPanel sectors={[
      { sector_id: "s1", name: "银行", change_percent: "2.5", amount_yi: "420", limit_up_count: 1, rising_count: 30, falling_count: 4, stock_count: 40 },
      { sector_id: "s2", name: "医药", change_percent: "-1.2", amount_yi: "380", limit_up_count: 0, rising_count: 8, falling_count: 32, stock_count: 45 },
    ]} selectedSectorId="s1" onSelectSector={onSelect} />);

    const bank = screen.getByText("银行").closest("button");
    const medicine = screen.getByText("医药").closest("button");
    expect(bank).toHaveAttribute("data-direction", "up");
    expect(medicine).toHaveAttribute("data-direction", "down");
    fireEvent.click(medicine!);
    expect(onSelect).toHaveBeenCalledWith("s2");
  });

  it("keeps missing sector changes unavailable instead of displaying zero", () => {
    render(<SectorHeatmapPanel sectors={[
      { sector_id: "s1", name: "未知板块", change_percent: null, amount_yi: null, limit_up_count: 0, rising_count: 0, falling_count: 0, stock_count: 0 },
    ]} selectedSectorId={null} onSelectSector={() => undefined} />);

    const item = screen.getByText("未知板块").closest("button");
    expect(item).toHaveAttribute("data-direction", "unavailable");
    expect(item).toHaveTextContent("--");
    expect(item).not.toHaveTextContent("0.00%");
  });
});
