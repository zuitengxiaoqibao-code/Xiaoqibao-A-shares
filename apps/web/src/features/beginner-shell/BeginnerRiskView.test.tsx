import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BeginnerRiskView } from "./BeginnerRiskView";

describe("BeginnerRiskView", () => {
  it("loads a plain-language risk status without internal rules or order concepts", async () => {
    render(<BeginnerRiskView load={() => Promise.resolve({
      rule_version: "internal-v9", limits: { max_position: "0.2" }, overall_level: "medium", generated_at: "2026-07-30T02:00:00Z",
      dimensions: [
        { id: "market", label: "市场环境", level: "medium", value: "情绪偏冷", evidence: "市场情绪 38 分", action: "降低追高频率" },
        { id: "freshness", label: "数据时效", level: "low", value: "当前", evidence: "行情快照有效", action: "按计划复核" },
      ],
      alerts: [{ id: "news-1", title: "公司被立案调查", level: "high", category: "新闻事件", evidence: "已核验公告", action: "核对公告并回避未确认交易", affected_instruments: ["600000"], affected_sectors: ["银行"], observed_at: "2026-07-30T01:55:00Z", source: "巨潮资讯" }],
    })} />);
    expect(await screen.findByText("当前风险：中等")).toBeInTheDocument();
    expect(screen.getByText("市场环境")).toBeInTheDocument();
    expect(screen.getByText("公司被立案调查")).toBeInTheDocument();
    expect(screen.getByText("600000")).toBeInTheDocument();
    expect(screen.queryByText(/internal-v9|max_position|仓位|委托|订单|刑部/)).not.toBeInTheDocument();
  });
  it("retries a failed request", async () => {
    const load = vi.fn().mockRejectedValueOnce(new Error("风险数据暂不可用")).mockResolvedValueOnce({ rule_version: "v1", limits: {} });
    render(<BeginnerRiskView load={load} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("风险数据暂不可用");
    fireEvent.click(screen.getByRole("button", { name: "重试" }));
    expect(await screen.findByText("当前风险：待核验")).toBeInTheDocument();
  });
  it("ignores an older response after the loader changes", async () => {
    let resolveOld!: (value: { rule_version: string; limits: Record<string, string> }) => void;
    const old = new Promise<{ rule_version: string; limits: Record<string, string> }>((resolve) => { resolveOld = resolve; });
    const view = render(<BeginnerRiskView load={() => old} />);
    view.rerender(<BeginnerRiskView load={() => Promise.reject(new Error("最新风险请求失败"))} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("风险数据暂不可用，请稍后重试。");
    expect(screen.queryByText("最新风险请求失败")).not.toBeInTheDocument();
    resolveOld({ rule_version: "old", limits: {} });
    expect(screen.queryByText("风险检查正常运行")).not.toBeInTheDocument();
  });
});
