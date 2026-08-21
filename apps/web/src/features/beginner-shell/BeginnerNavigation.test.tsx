import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BeginnerNavigation, type BeginnerView } from "./BeginnerNavigation";

describe("BeginnerNavigation", () => {
  it("shows one complete navigation without beginner or expert mode switches", () => {
    render(<BeginnerNavigation active="dashboard" onNavigate={vi.fn()} />);

    expect(screen.queryByRole("group", { name: "导航模式" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新手模式" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "专家模式" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "量化分析" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "数据设置" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "本地运维" })).toBeInTheDocument();
  });

  it("shows the complete daily workflow", () => {
    render(<BeginnerNavigation active="dashboard" onNavigate={vi.fn()} />);

    expect(screen.getByRole("complementary")).toHaveClass("terminal-navigation", "beginner-sidebar");
    const navigation = screen.getByRole("navigation", { name: "主要功能" });
    expect(navigation).toHaveTextContent("信息总览今日研判个股观察公司研究首次涨停尾盘选股量化分析监控中心新闻热点风险提醒历史复盘数据设置本地运维");
    expect(navigation.querySelectorAll("button")).toHaveLength(13);
    expect(screen.getByRole("button", { name: "量化分析" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "数据设置" })).toBeInTheDocument();
    const marketOverview = screen.getByRole("button", { name: "信息总览" });
    const todayDecision = screen.getByRole("button", { name: "今日研判" });
    const companyResearch = screen.getByRole("button", { name: "公司研究" });
    expect(marketOverview.nextElementSibling).toBe(todayDecision);
    expect(screen.getByRole("button", { name: "个股观察" }).nextElementSibling).toBe(companyResearch);
    expect(screen.queryByRole("button", { name: "新手模式" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "可转债" })).toBeInTheDocument();
    expect(screen.getByText("一树-A股观测台")).toBeInTheDocument();
    const company = screen.getByText("上海一树电子商务有限公司");
    const disclaimer = screen.getByText(/只做观察与风险提示/);
    expect(company.nextElementSibling).toBe(disclaimer);
  });

  it("keeps all routes at the same navigation level", () => {
    render(<BeginnerNavigation active="dashboard" onNavigate={vi.fn()} />);
    const navigation = screen.getByRole("navigation", { name: "主要功能" });
    expect(navigation.querySelectorAll("button")).toHaveLength(13);
    const firstLimitUp = screen.getByRole("button", { name: "首次涨停" });
    const lateSession = screen.getByRole("button", { name: "尾盘选股" });
    const quantAnalysis = screen.getByRole("button", { name: "量化分析" });
    expect(firstLimitUp.nextElementSibling).toBe(lateSession);
    expect(lateSession.nextElementSibling).toBe(quantAnalysis);
    expect(quantAnalysis).not.toHaveClass("child-entry");
    expect(quantAnalysis.className).toBe(firstLimitUp.className);
    expect(screen.getByRole("button", { name: "数据设置" })).toBeInTheDocument();
    expect(screen.queryByText(/中书省|东厂|礼部|刑部|工部|部门/)).not.toBeInTheDocument();
  });

  it("reports the selected beginner route", () => {
    const onNavigate = vi.fn<(view: BeginnerView) => void>();
    render(<BeginnerNavigation active="dashboard" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole("button", { name: "风险提醒" }));
    expect(onNavigate).toHaveBeenCalledWith("risk");
  });

  it("reports and highlights the local operations route", () => {
    const onNavigate = vi.fn<(view: BeginnerView) => void>();
    render(<BeginnerNavigation active="operations" onNavigate={onNavigate} />);

    const operations = screen.getByRole("button", { name: "本地运维" });
    expect(operations).toHaveClass("active");
    fireEvent.click(operations);
    expect(onNavigate).toHaveBeenCalledWith("operations");
  });

  it("reports and highlights the quant-analysis first-level route", () => {
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
