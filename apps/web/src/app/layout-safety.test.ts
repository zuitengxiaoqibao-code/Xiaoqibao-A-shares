import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
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

  it("keeps the first-limit-up list independently scrollable and its detail visible", () => {
    expect(cssRule(css, ".first-limit-up-list")).toContain("overflow: hidden");
    expect(cssRule(css, ".first-limit-up-rows")).toContain("overflow: auto");
    expect(cssRule(css, ".first-limit-up-detail")).toContain("position: sticky");
    expect(css).toMatch(
      /@media\s*\(max-width:\s*900px\)[\s\S]*?\.first-limit-up-detail\s*\{[^}]*position:\s*static[^}]*max-height:\s*none/,
    );
  });

  it("does not force the legacy primary workspace to a fixed empty height", () => {
    expect(cssRule(css, ".primary-workspace")).not.toMatch(/min-height\s*:/);
  });

  it("preserves explicit chart canvases", () => {
    expect(cssRule(css, ".quant-chart")).toMatch(/height:\s*300px/);
    expect(cssRule(css, ".stock-event-chart .quant-chart")).toMatch(/height:\s*560px/);
  });

  it("uses the selector card width for responsive target layout", () => {
    expect(cssRule(css, ".quant-instrument-control")).toContain("container-type: inline-size");
    expect(cssRule(css, ".quant-instrument-state > span")).toContain("text-overflow: ellipsis");
    expect(css).toMatch(/@container\s*\(max-width:\s*420px\)[\s\S]*?\.quant-instrument-layout/);
    expect(css).toMatch(/@container\s*\(max-width:\s*420px\)[\s\S]*?\.quant-instrument-state/);
  });

  it("places the quant instrument bar below the title and keeps it full width", () => {
    expect(cssRule(css, ".quant-hero")).toContain("align-items: start");
    expect(cssRule(css, ".quant-hero")).toContain("grid-template-columns: minmax(0, 1fr)");
    expect(cssRule(css, ".quant-hero")).toContain("width: 100%");
    expect(cssRule(css, ".quant-hero")).toContain("max-width: none");
    expect(cssRule(css, ".quant-instrument-layout")).toContain("display: flex");
    expect(cssRule(css, ".quant-instrument-layout")).toContain("align-items: center");
  });

  it("does not use user-visible font sizes below the 12px readability floor", () => {
    function collectStylesheets(directory: string): string[] {
      return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
        const path = join(directory, entry.name).replaceAll("\\", "/");
        if (entry.isDirectory()) return collectStylesheets(path);
        return entry.isFile() && path.endsWith(".css") ? [path] : [];
      });
    }
    const violations = collectStylesheets("src").flatMap((path) => {
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
    function sourceFiles(directory: string): string[] {
      return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
        const path = join(directory, entry.name).replaceAll("\\", "/");
        if (entry.isDirectory()) return sourceFiles(path);
        return entry.isFile() && /\.(?:ts|tsx)$/.test(path) ? [path] : [];
      });
    }
    const chartFiles = sourceFiles("src").filter((path) => {
      const source = readFileSync(path, "utf8");
      return source.includes("EChartsOption") || source.includes("<QuantChart");
    });
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

  it("collapses new risk and evidence dashboards on narrow windows", () => {
    expect(css).toMatch(/@media\s*\(max-width:\s*800px\)[\s\S]*?\.portfolio-risk-kpis\s*\{[^}]*grid-template-columns:\s*repeat\(2,/);
    expect(css).toMatch(/@media\s*\(max-width:\s*800px\)[\s\S]*?\.portfolio-stress-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    expect(css).toMatch(/@media\s*\(max-width:\s*800px\)[\s\S]*?\.quant-shadow-kpis\s*\{[^}]*grid-template-columns:\s*repeat\(2,/);
    expect(css).toMatch(/@media\s*\(max-width:\s*800px\)[\s\S]*?\.quant-shadow-regimes\s*>\s*div\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    expect(css).toMatch(/@media\s*\(max-width:\s*800px\)[\s\S]*?\.quant-decision-journal-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
  });

  it("collapses unavailable evidence panels instead of reserving a tall blank area", () => {
    const overviewCss = readFileSync("src/features/market-overview/overview.css", "utf8");
    expect(overviewCss).toMatch(/\.block-evidence-map \.distinct-empty\s*\{[^}]*min-height:\s*112px/);
    expect(overviewCss).toMatch(/\.layout-stock-dossier \.block-evidence-map[^}]*align-self:\s*start/);
    expect(cssRule(overviewCss, ".capital-audit")).not.toMatch(/min-height\s*:/);
    expect(overviewCss).not.toMatch(/\.layout-large-order-audit \.block-capital-audit\s*\{[^}]*grid-column:\s*span 8/);
    expect(cssRule(overviewCss, ".layout-large-order-audit .block-capital-audit")).toContain("grid-column: span 12");
  });

  it("stretches paired market-overview blocks to equal desktop row height", () => {
    const overviewCss = readFileSync("src/features/market-overview/overview.css", "utf8");
    expect(cssRule(overviewCss, ".distinct-block-grid")).toContain("align-items: stretch");
    expect(cssRule(overviewCss, ".distinct-block")).toContain("height: 100%");
    expect(overviewCss).toMatch(
      /@media\s*\(max-width:\s*650px\)[\s\S]*?\.distinct-block\.size-wide[^}]*align-self:\s*start[^}]*height:\s*auto/,
    );
  });

  it("fills the industry map without fixed branch spans that leave empty grid cells", () => {
    const overviewCss = readFileSync("src/features/market-overview/overview.css", "utf8");
    expect(cssRule(overviewCss, ".industry-map")).toContain("grid-template-columns: repeat(3");
    expect(cssRule(overviewCss, ".industry-map article.branch-0")).not.toContain("grid-column: span 2");
    expect(cssRule(overviewCss, ".industry-map article.branch-1")).not.toContain("grid-column: span 2");
  });

  it("uses a compact horizontal layout for the four review summary metrics", () => {
    const overviewCss = readFileSync("src/features/market-overview/overview.css", "utf8");
    expect(cssRule(overviewCss, ".review-summary-grid")).not.toContain("min-height: 260px");
    expect(cssRule(overviewCss, ".review-summary-grid article")).not.toContain("grid-template-columns: 42px minmax(0, 1fr) auto");
    expect(cssRule(overviewCss, ".review-summary-grid article")).toContain("min-height: 82px");
    expect(cssRule(overviewCss, ".review-summary-metric")).toContain("grid-template-columns: 42px minmax(64px, 1fr) auto");
  });

  it("keeps the market overview flat menu readable and content panels height-driven", () => {
    const overviewCss = readFileSync("src/features/market-overview/overview.css", "utf8");
    expect(overviewCss).toMatch(
      /\.market-overview-page \.overview-feature-rail\s*\{[^}]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(112px,\s*1fr\)\)/,
    );
    expect(cssRule(overviewCss, ".market-overview-page .overview-feature-rail button")).toContain("font-size: 13px");
    expect(cssRule(overviewCss, ".market-overview-page .distinct-metric-deck")).toContain("min-height: 0");
    expect(cssRule(overviewCss, ".market-overview-page .sector-ranked-bars")).toContain("min-height: 0");
    expect(cssRule(overviewCss, ".market-overview-page .distinct-table-scroll")).toContain("clamp(220px, 42vh, 420px)");
    expect(overviewCss).toMatch(
      /@media\s*\(max-width:\s*650px\)[\s\S]*?\.market-overview-page \.overview-feature-rail\s*\{[^}]*grid-template-columns:\s*repeat\(2,/,
    );
  });

  it("lets the overview minute chart consume the full height of the adjacent anomaly list", () => {
    const overviewCss = readFileSync("src/features/market-overview/overview.css", "utf8");
    expect(cssRule(overviewCss, ".overview-chart-panel")).toContain("display: flex");
    expect(cssRule(overviewCss, ".overview-chart-panel")).toContain("flex-direction: column");
    expect(cssRule(overviewCss, ".overview-chart-shell")).toContain("flex: 1 1 330px");
    expect(cssRule(overviewCss, ".overview-chart-shell")).toContain("min-height: 330px");
    expect(cssRule(overviewCss, ".overview-chart-shell")).not.toMatch(/(^|;)\s*height:\s*330px/);
  });

  it("animates every busy region without inventing a fake percentage", () => {
    expect(css).toContain('[aria-busy="true"]::after');
    expect(css).toContain(".lucide-loader-circle");
    expect(css).toContain("qibao-busy-track");
  });

  it("splits workbench routes and preloads them while the browser is idle", () => {
    const dashboard = readFileSync("src/features/dashboard/Dashboard.tsx", "utf8");
    expect(dashboard).toContain('const loadQuantAnalysisModule = () => import("../quant-analysis/QuantAnalysisDashboard");');
    expect(dashboard).toContain('const loadCompanyResearchModule = () => import("../company-research/CompanyResearchView");');
    expect(dashboard).toContain('const loadBeginnerRiskModule = () => import("../beginner-shell/BeginnerRiskView");');
    expect(dashboard).toContain('const loadHistoryReviewModule = () => import("../beginner-shell/HistoryReview");');
    expect(dashboard).toContain('const loadDataSettingsModule = () => import("../data-settings/DataSettingsView");');
    expect(dashboard).toMatch(/const QuantAnalysisDashboard = lazy\(/);
    expect(dashboard).toMatch(/const CompanyResearchView = lazy\(/);
    expect(dashboard).toMatch(/const BeginnerRiskView = lazy\(/);
    expect(dashboard).toMatch(/const HistoryReview = lazy\(/);
    expect(dashboard).toMatch(/const DataSettingsView = lazy\(/);
    expect(dashboard).toMatch(/useEffect\(\(\) => \{[\s\S]*scheduleRoutePreload\(primaryRoutePreloaders\)/);
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
