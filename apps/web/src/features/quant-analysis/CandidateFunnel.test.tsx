import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CandidateFunnel } from "./CandidateFunnel";

describe("CandidateFunnel", () => {
  it("shows deterministic stages, exclusion reasons, and incomplete blockers", () => {
    render(<CandidateFunnel funnel={{
      stages: [
        { key: "universe", label: "全市场股票", count: 5000 },
        { key: "history_ready", label: "日线历史完整", count: 4700 },
        { key: "factor_ready", label: "因子计算完成", count: 4650 },
        { key: "liquidity_ready", label: "流动性达标", count: 4200 },
        { key: "ranked", label: "策略排名入选", count: 12 },
        { key: "trigger_confirmed", label: "盘中触发确认", count: 2 },
        { key: "final_candidates", label: "最终候选", count: 1 },
      ],
      exclusion_reasons: { insufficient_history: 300, insufficient_liquidity: 450 },
      completeness: "partial",
      blockers: ["incomplete_daily_history"],
    }} />);

    expect(screen.getByRole("region", { name: "候选筛选漏斗" })).toBeInTheDocument();
    expect(screen.getByText("日线历史完整")).toBeInTheDocument();
    expect(screen.getByText("4,700")).toBeInTheDocument();
    expect(screen.getByText("历史覆盖不完整")).toBeInTheDocument();
    expect(screen.getByText("日线历史不足").closest("span")).toHaveTextContent("300 只");
  });
});
