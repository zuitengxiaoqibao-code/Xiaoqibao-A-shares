import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

function cssRule(css: string, selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return css.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))?.[1] ?? "";
}

describe("application layout safety", () => {
  const css = readFileSync("src/app/theme.css", "utf8");

  it("keeps ordinary page placeholders compact", () => {
    expect(cssRule(css, ".empty-state")).toContain("min-height: 140px");
    expect(cssRule(css, ".loading-state")).toContain("min-height: 140px");
    expect(cssRule(css, ".diagnosis-wait")).toContain("min-height: 180px");
    expect(cssRule(css, ".decision-message")).toContain("min-height: 180px");
    expect(cssRule(css, ".empty-cockpit")).toContain("min-height: 180px");
    expect(cssRule(css, ".first-limit-up-detail-empty")).toContain("min-height: 180px");
    expect(cssRule(css, ".first-limit-up-empty")).toContain("min-height: 160px");
    expect(cssRule(css, ".sentiment-loading")).toContain("min-height: 180px");
  });

  it("top-aligns independent columns so short panels are not stretched", () => {
    expect(cssRule(css, ".workspace-grid")).toContain("align-items: start");
    expect(cssRule(css, ".first-limit-up-layout")).toContain("align-items: start");
  });

  it("does not force the legacy primary workspace to a fixed empty height", () => {
    expect(cssRule(css, ".primary-workspace")).not.toMatch(/min-height\s*:/);
  });

  it("preserves explicit chart canvases", () => {
    expect(cssRule(css, ".quant-chart")).toMatch(/height:\s*300px/);
    expect(cssRule(css, ".stock-event-chart .quant-chart")).toMatch(/height:\s*560px/);
  });

  it("does not use user-visible font sizes below the 12px readability floor", () => {
    const stylesheets = [
      "src/app/theme.css",
      "src/app/terminal.css",
      "src/features/market-overview/overview.css",
    ];
    const violations = stylesheets.flatMap((path) => {
      const source = readFileSync(path, "utf8");
      const explicit = [...source.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g)];
      const shorthand = [...source.matchAll(/font:\s*[^;{}]*?\b(\d+(?:\.\d+)?)px(?:\/[^\s;]+)?\s/g)];
      return [...explicit, ...shorthand]
        .filter((match) => Number(match[1]) < 12)
        .map((match) => `${path}:${match[0].trim()}`);
    });

    expect(violations).toEqual([]);
  });

  it("keeps chart annotation fonts at or above the 12px readability floor", () => {
    const chartFiles = [
      "src/features/stock-timeline/StockEventKline.tsx",
      "src/features/market-overview/OverviewMinuteChart.tsx",
      "src/features/quant-analysis/QuantAnalysisDashboard.tsx",
    ];
    const violations = chartFiles.flatMap((path) => {
      const source = readFileSync(path, "utf8");
      return [...source.matchAll(/fontSize:\s*([^,}\n]+)/g)].flatMap((declaration) => (
        [...declaration[1].matchAll(/\b(\d+)\b/g)]
          .filter((match) => Number(match[1]) < 12)
          .map((match) => `${path}:fontSize ${declaration[1].trim()}`)
      ));
    });

    expect(violations).toEqual([]);
  });

  it("animates every busy region without inventing a fake percentage", () => {
    expect(css).toContain('[aria-busy="true"]::after');
    expect(css).toContain(".lucide-loader-circle");
    expect(css).toContain("qibao-busy-track");
  });

  it("uses the shared terminal tokens on the company research page", () => {
    const companyCss = readFileSync("src/features/company-research/companyResearch.css", "utf8");
    expect(companyCss).toContain("var(--surface-canvas)");
    expect(companyCss).toContain("var(--font-body)");
    expect(companyCss).not.toMatch(/#[0-9a-f]{3,8}\b/i);
  });

  it("keeps the stock-to-company-research action prominent and on one line", () => {
    expect(cssRule(css, ".cockpit-quality")).toContain("minmax(220px");
    expect(cssRule(css, ".cockpit-quality > .company-research-jump")).toContain("var(--focus-warning)");
    expect(cssRule(css, ".company-research-jump small")).toContain("white-space: nowrap");
  });

  it("marks major data-loading placeholders as busy status regions", () => {
    const files = [
      "src/features/a-shares/AShareResearchView.tsx",
      "src/features/stock-cockpit/StockSelector.tsx",
      "src/features/first-limit-up/FirstLimitUpView.tsx",
      "src/features/market-sentiment/MarketSentimentDashboard.tsx",
      "src/features/market-sentiment/WatchlistMarketSentiment.tsx",
      "src/features/news-intelligence/NewsIntelligenceView.tsx",
      "src/features/operations/OperationsView.tsx",
      "src/features/governance/GovernanceViews.tsx",
    ];
    const missing = files.filter((path) => {
      const source = readFileSync(path, "utf8");
      return !source.includes('aria-busy="true"');
    });
    expect(missing).toEqual([]);
  });
});
