import { describe, expect, it } from "vitest";

import { featureRows } from "../featureCatalog";
import { getWorkspaceDefinition, WORKSPACE_DEFINITIONS } from "./workspaceRegistry";

describe("market overview workspace registry", () => {
  it("covers every information-overview menu without a generic fallback", () => {
    const labels = featureRows.flat();

    expect(WORKSPACE_DEFINITIONS).toHaveLength(50);
    expect(new Set(WORKSPACE_DEFINITIONS.map((item) => item.label))).toEqual(new Set(labels));
    expect(() => getWorkspaceDefinition("不存在的栏目")).toThrow(/未登记/);
  });

  it("gives every menu a distinct composition and analytical contract", () => {
    const compositions = WORKSPACE_DEFINITIONS.map((item) => (
      `${item.layout}:${item.blocks.map((block) => `${block.kind}/${block.variant}`).join("|")}`
    ));

    expect(new Set(compositions)).toHaveLength(WORKSPACE_DEFINITIONS.length);
    for (const item of WORKSPACE_DEFINITIONS) {
      expect(item.question.length).toBeGreaterThan(8);
      expect(item.beginnerGuide.length).toBeGreaterThan(8);
      expect(item.truthBoundary.length).toBeGreaterThan(8);
      expect(item.blocks.length).toBeGreaterThanOrEqual(2);
      expect(item.blocks.every((block) => block.title.length > 1)).toBe(true);
    }
  });

  it("uses feature-specific layouts for representative menus", () => {
    expect(getWorkspaceDefinition("隔夜单/抢筹").blocks.map((item) => item.kind)).toContain("auction-gap");
    expect(getWorkspaceDefinition("连板表现").blocks.map((item) => item.kind)).toContain("height-pyramid");
    expect(getWorkspaceDefinition("龙头晋级").blocks.map((item) => item.kind)).toContain("promotion-funnel");
    expect(getWorkspaceDefinition("概念叠加").blocks.map((item) => item.kind)).toContain("theme-matrix");
    expect(getWorkspaceDefinition("投资日历").blocks.map((item) => item.kind)).toContain("event-calendar");
    expect(getWorkspaceDefinition("问财选股").blocks.map((item) => item.kind)).toContain("rule-gates");
    expect(getWorkspaceDefinition("非研产业库").blocks.map((item) => item.kind)).toContain("industry-map");
    expect(getWorkspaceDefinition("连板梯队").blocks.map((item) => item.kind)).toContain("limit-ladder");
    expect(getWorkspaceDefinition("首板梯队").blocks.map((item) => item.kind)).toContain("first-board-table");
    expect(getWorkspaceDefinition("放量突破").blocks.map((item) => item.kind)).toContain("breakout-table");
    expect(getWorkspaceDefinition("龙虎榜").blocks.map((item) => item.kind)).toContain("dragon-tiger-board");
  });

  it("does not leave an unpaired half-width block after a tall lead block", () => {
    const invalid = WORKSPACE_DEFINITIONS.filter((definition) => (
      definition.blocks.length === 3
      && definition.blocks[0].size === "tall"
      && definition.blocks[1].size === "half"
      && definition.blocks[2].size === "half"
    ));

    expect(invalid.map((definition) => definition.label)).toEqual([]);
  });

  it("declares unavailable proprietary evidence instead of proxy claims", () => {
    for (const label of ["游资追踪", "游资动向"]) {
      const definition = getWorkspaceDefinition(label);
      expect(definition.requiredEvidence).toContain("dragon-tiger-seats");
      expect(definition.truthBoundary).toMatch(/龙虎榜|席位/);
      expect(definition.truthBoundary).toMatch(/不.*成交额/);
    }
    expect(getWorkspaceDefinition("主力大单监控").requiredEvidence).toContain("large-order-flow");
    expect(getWorkspaceDefinition("板块资金动图").requiredEvidence).toContain("sector-capital-flow");
    expect(getWorkspaceDefinition("竞价封单").requiredEvidence).toContain("order-book");
    expect(getWorkspaceDefinition("百日新高").requiredEvidence).toContain("daily-history-100");
  });
});
