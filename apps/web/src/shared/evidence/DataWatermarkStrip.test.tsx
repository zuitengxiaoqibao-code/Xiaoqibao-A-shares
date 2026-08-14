import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataWatermarkStrip } from "./DataWatermarkStrip";


describe("DataWatermarkStrip", () => {
  it("shows status, trade date, timestamps, sources, samples and limitations", () => {
    render(<DataWatermarkStrip
      status="partial"
      tradeDate="2026-08-11"
      observedAt="2026-08-11T15:00:00+08:00"
      generatedAt="2026-08-11T15:00:05+08:00"
      sourceCount={3}
      sampleCount={120}
      refreshState="pending"
      limitations={["资金流字段待补"]}
    />);

    expect(screen.getByLabelText("数据证据水印")).toHaveTextContent("部分可用");
    expect(screen.getByText("2026-08-11")).toBeInTheDocument();
    expect(screen.getByText("3 个来源")).toBeInTheDocument();
    expect(screen.getByText("120 条样本")).toBeInTheDocument();
    expect(screen.getByText("后台刷新中")).toBeInTheDocument();
    expect(screen.getByText("资金流字段待补")).toBeInTheDocument();
  });

  it("translates known data blockers into readable Chinese copy", () => {
    render(<DataWatermarkStrip
      status="partial"
      tradeDate="2026-08-13"
      limitations={["stale_daily_history"]}
    />);

    expect(screen.getByText("日线历史落后请求日")).toBeInTheDocument();
    expect(screen.queryByText("stale_daily_history")).not.toBeInTheDocument();
  });
});
