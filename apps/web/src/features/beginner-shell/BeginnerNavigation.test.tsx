import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BeginnerNavigation, type BeginnerView } from "./BeginnerNavigation";

describe("BeginnerNavigation", () => {
  beforeEach(() => window.localStorage.clear());

  it("defaults to the daily beginner workflow", () => {
    render(<BeginnerNavigation active="dashboard" onNavigate={vi.fn()} />);

    expect(screen.getByRole("complementary")).toHaveClass("terminal-navigation", "beginner-sidebar");
    const navigation = screen.getByRole("navigation", { name: "主要功能" });
    expect(navigation).toHaveTextContent("信息总览今日研判个股观察公司研究首次涨停新闻热点风险提醒历史复盘");
    expect(navigation.querySelectorAll("button")).toHaveLength(8);
    expect(screen.queryByRole("button", { name: "量化分析" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "数据设置" })).not.toBeInTheDocument();
    const marketOverview = screen.getByRole("button", { name: "信息总览" });
    const todayDecision = screen.getByRole("button", { name: "今日研判" });
    const companyResearch = screen.getByRole("button", { name: "公司研究" });
    expect(marketOverview.nextElementSibling).toBe(todayDecision);
    expect(screen.getByRole("button", { name: "个股观察" }).nextElementSibling).toBe(companyResearch);
    expect(screen.getByRole("button", { name: "新手模式" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "可转债" })).toBeInTheDocument();
    expect(screen.getByText("一树-A股观测台")).toBeInTheDocument();
    const company = screen.getByText("上海一树电子商务有限公司");
    const disclaimer = screen.getByText(/只做观察与风险提示/);
    expect(company.nextElementSibling).toBe(disclaimer);
  });

  it("shows every route in expert mode and persists the selection", () => {
    const view = render(<BeginnerNavigation active="dashboard" onNavigate={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "专家模式" }));

    const navigation = screen.getByRole("navigation", { name: "主要功能" });
    expect(navigation.querySelectorAll("button")).toHaveLength(10);
    const firstLimitUp = screen.getByRole("button", { name: "首次涨停" });
    const quantAnalysis = screen.getByRole("button", { name: "量化分析" });
    expect(firstLimitUp.nextElementSibling).toBe(quantAnalysis);
    expect(quantAnalysis).not.toHaveClass("child-entry");
    expect(quantAnalysis.className).toBe(firstLimitUp.className);
    expect(window.localStorage.getItem("qibao-navigation-mode")).toBe("expert");
    view.unmount();
    render(<BeginnerNavigation active="dashboard" onNavigate={vi.fn()} />);
    expect(screen.getByRole("button", { name: "专家模式" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "数据设置" })).toBeInTheDocument();
    expect(screen.queryByText(/中书省|东厂|礼部|刑部|工部|部门/)).not.toBeInTheDocument();
  });

  it("gives only the two navigation mode buttons distinct beginner and expert color roles", () => {
    render(<BeginnerNavigation active="dashboard" onNavigate={vi.fn()} />);

    expect(screen.getByRole("button", { name: "新手模式" })).toHaveClass("navigation-mode-beginner");
    expect(screen.getByRole("button", { name: "专家模式" })).toHaveClass("navigation-mode-expert");
    expect(screen.getByRole("button", { name: "今日研判" })).not.toHaveClass(
      "navigation-mode-beginner",
      "navigation-mode-expert",
    );
  });

  it("reports the selected beginner route", () => {
    const onNavigate = vi.fn<(view: BeginnerView) => void>();
    render(<BeginnerNavigation active="dashboard" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole("button", { name: "风险提醒" }));
    expect(onNavigate).toHaveBeenCalledWith("risk");
  });

  it("reports and highlights the quant-analysis first-level route", () => {
    window.localStorage.setItem("qibao-navigation-mode", "expert");
    const onNavigate = vi.fn<(view: BeginnerView) => void>();
    render(<BeginnerNavigation active="quant_analysis" onNavigate={onNavigate} />);

    const quantAnalysis = screen.getByRole("button", { name: "量化分析" });
    expect(quantAnalysis).toHaveClass("active");
    expect(quantAnalysis).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "首次涨停" })).not.toHaveClass("active");
    fireEvent.click(quantAnalysis);
    expect(onNavigate).toHaveBeenCalledWith("quant_analysis");
  });
});
