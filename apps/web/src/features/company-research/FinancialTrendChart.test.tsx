import { describe, expect, it } from "vitest";

import type { FinancialPeriod } from "./types";
import { financialTrendOption } from "./FinancialTrendChart";


const base: FinancialPeriod = {
  period: "2025-12-31", revenue: "100", revenue_yoy: null, operating_cost: null,
  net_profit: "10", net_profit_yoy: null, operating_cash_flow: "8", total_assets: null,
  total_liabilities: null, total_equity: null, gross_margin: null, cash_to_profit: null,
  debt_ratio: null,
};

describe("FinancialTrendChart", () => {
  it("keeps missing financial values null instead of backfilling zero", () => {
    const option = financialTrendOption([base, { ...base, period: "2026-03-31", net_profit: null }]);
    const series = option.series as Array<{ data: Array<number | null> }>;
    expect(series[1].data).toEqual([10, null]);
  });
});
