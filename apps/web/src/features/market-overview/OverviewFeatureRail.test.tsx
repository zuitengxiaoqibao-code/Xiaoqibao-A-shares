import { readFileSync } from "node:fs";

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OverviewFeatureRail } from "./OverviewFeatureRail";

describe("OverviewFeatureRail", () => {
  it("renders every feature in one continuous grid so wrapped rows share columns", () => {
    render(<OverviewFeatureRail active="盘中异动" onSelect={vi.fn()} />);

    const navigation = screen.getByRole("navigation", { name: "市场功能筛选" });
    expect(navigation.children).toHaveLength(50);
    expect([...navigation.children].every((item) => item.tagName === "BUTTON")).toBe(true);
    expect(screen.getByRole("button", { name: "主力大单监控" })).toHaveAttribute(
      "title",
      "主力大单监控",
    );
  });

  it("uses an equal-width responsive grid instead of content-width flex rows", () => {
    const css = readFileSync("src/features/market-overview/overview.css", "utf8");

    expect(css).toMatch(
      /\.overview-feature-rail\s*\{[^}]*display:\s*grid;[^}]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(/s,
    );
    expect(css).not.toMatch(/\.overview-feature-rail\s*>\s*div\s*\{/);
  });

  it("shows established flat menu names while keeping stable selection keys", () => {
    const onSelect = vi.fn();
    render(<OverviewFeatureRail active="开盘啦" onSelect={onSelect} />);

    expect(screen.getByRole("button", { name: "开盘啦" })).toHaveAttribute("title", "开盘啦");
    expect(screen.queryByRole("button", { name: "开盘检查" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开盘啦" })).toHaveAttribute("data-feature-key", "开盘啦");
    expect(screen.getByRole("button", { name: "隔夜单/抢筹" })).toHaveAttribute("title", expect.stringContaining("委托"));
  });
});
