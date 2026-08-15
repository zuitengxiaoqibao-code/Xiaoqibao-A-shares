import { beforeEach, describe, expect, it } from "vitest";

import {
  clearWorkspaceState,
  loadWorkspaceState,
  saveWorkspaceState,
  rememberDrilldownSymbols,
  updateWorkspaceFilter,
  validateWorkspaceState,
  WORKSPACE_STATE_KEY,
} from "./workspaceState";

describe("workspace state", () => {
  beforeEach(() => localStorage.clear());

  it("round-trips the route, stock, date, filters, drilldown symbols and scroll state", () => {
    saveWorkspaceState({
      route: "/company-research",
      menu: "公司研究",
      symbol: "600519",
      asOf: "2026-08-14",
      filters: { "metric-drilldown": { query: "贵州", excludeST: true } },
      drilldownSymbols: { "涨停家数": ["600519", "000001", "600519"] },
      scrollTop: 812.5,
      scrollById: { "overview-main": 240 },
    });

    expect(loadWorkspaceState()).toMatchObject({
      version: 1,
      route: "/company-research",
      menu: "公司研究",
      symbol: "600519",
      asOf: "2026-08-14",
      filters: { "metric-drilldown": { query: "贵州", excludeST: true } },
      drilldownSymbols: { "涨停家数": ["600519", "000001"] },
      scrollTop: 812.5,
      scrollById: { "overview-main": 240 },
    });
  });

  it("rejects a bad version, invalid route and non A-share symbols", () => {
    const invalid = validateWorkspaceState({
      version: 99,
      route: "javascript:alert(1)",
      symbol: "113065",
      asOf: "2026-99-99",
      filters: {},
      drilldownSymbols: {},
      scrollTop: -1,
      scrollById: {},
    }, ["/market-overview"]);

    expect(invalid).toBeNull();
    localStorage.setItem(WORKSPACE_STATE_KEY, JSON.stringify({ version: 99 }));
    expect(loadWorkspaceState()).toBeNull();
    expect(localStorage.getItem(WORKSPACE_STATE_KEY)).toBeNull();
  });

  it("clears persisted state without throwing when storage is available", () => {
    saveWorkspaceState({ route: "/market-overview", menu: "信息总览" });
    clearWorkspaceState();
    expect(loadWorkspaceState()).toBeNull();
  });

  it("merges one filter scope and one drilldown set without losing the rest of the workspace", () => {
    saveWorkspaceState({ route: "/market-overview", menu: "market_overview", symbol: "600519" });
    updateWorkspaceFilter("market-overview", { activeFeature: "龙虎榜" });
    updateWorkspaceFilter("metric-drilldown", { query: "银行", excludeST: true });
    rememberDrilldownSymbols("涨停家数", ["000001", "113065", "000001", "600000"]);

    expect(loadWorkspaceState()).toMatchObject({
      symbol: "600519",
      filters: {
        "market-overview": { activeFeature: "龙虎榜" },
        "metric-drilldown": { query: "银行", excludeST: true },
      },
      drilldownSymbols: { "涨停家数": ["000001", "600000"] },
    });
  });
});
