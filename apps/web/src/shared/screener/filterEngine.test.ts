import { describe, expect, it } from "vitest";

import { filterMembers } from "./filterEngine";

const rows = [
  { symbol: "600001", name: "样本科技", reason: "异动", value: "+3.25%", tradingStatus: "active" as const },
  { symbol: "000001", name: "ST样本", reason: "风险", value: "-2.00%", tradingStatus: "active" as const },
  { symbol: "300001", name: "停牌样本", reason: "停牌", value: null, tradingStatus: "suspended" as const },
];

describe("filterMembers", () => {
  it("filters by code, name and reason", () => {
    expect(filterMembers(rows, { query: "科技", excludeST: false, excludeSuspended: false, sort: "symbol" }).map((row) => row.symbol)).toEqual(["600001"]);
  });

  it("excludes ST and suspended members without hiding the original total", () => {
    expect(filterMembers(rows, { query: "", excludeST: true, excludeSuspended: true, sort: "symbol" }).map((row) => row.symbol)).toEqual(["600001"]);
  });

  it("sorts numeric display values descending", () => {
    expect(filterMembers(rows, { query: "", excludeST: false, excludeSuspended: false, sort: "value_desc" }).map((row) => row.symbol)).toEqual(["600001", "000001", "300001"]);
  });
});
