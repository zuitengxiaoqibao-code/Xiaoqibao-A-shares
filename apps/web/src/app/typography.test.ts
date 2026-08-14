import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("site typography", () => {
  it("defines Orbitron and JetBrains Mono roles with Chinese fallbacks", () => {
    const css = readFileSync("src/app/tokens.css", "utf8");

    expect(css).toContain('--font-display: "Orbitron", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif');
    expect(css).toContain('--font-body: "JetBrains Mono", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif');
  });

  it("defines one semantic palette for every page family", () => {
    const css = readFileSync("src/app/tokens.css", "utf8");

    expect(css).toContain("--surface-canvas: #070b10");
    expect(css).toContain("--surface-raised: #101923");
    expect(css).toContain("--market-up: #f04f5f");
    expect(css).toContain("--market-down: #2fcf91");
    expect(css).toContain("--status-warning: #e5b84b");
    expect(css).toContain("--status-live: #39c8dd");
    expect(css).toContain("--risk-low: #e5b84b");
    expect(css).toContain("--risk-medium: #f08c46");
    expect(css).toContain("--risk-high: #f04f5f");
    expect(css).toContain("--event-policy: #a78bfa");
    expect(css).toContain("--event-capital: #e879f9");
    expect(css).toContain("--event-rumor: #94a3b8");
  });

  it("raises the readable body and dense-label baselines", () => {
    const tokens = readFileSync("src/app/tokens.css", "utf8");
    const theme = readFileSync("src/app/theme.css", "utf8");

    expect(tokens).toContain("--font-xs: 13px");
    expect(tokens).toContain("--font-sm: 13px");
    expect(tokens).toContain("--font-md: 14px");
    expect(theme).toContain("body { font-size: 14px; }");
    expect(theme).toContain(".terminal-page small");
  });
});
