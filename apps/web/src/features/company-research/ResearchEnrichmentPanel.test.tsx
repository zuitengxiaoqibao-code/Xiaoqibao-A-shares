import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ResearchEnrichmentPanel } from "./ResearchEnrichmentPanel";

describe("ResearchEnrichmentPanel", () => {
  it("shows verified reports, EPS, unlock, margin and holder evidence without proxy values", () => {
    render(<ResearchEnrichmentPanel value={{
      status: "ready", observed_at: "2026-08-10T10:00:00+08:00",
      stock_reports: [{ report_id: "r1", title: "盈利预测更新", publish_date: "2026-08-08", organization: "测试机构", rating: "增持", industry: "软件开发", eps_this_year: "1.2", eps_next_year: "1.5", eps_next_two_year: "1.8", pdf_url: "https://example.com/r1.pdf" }],
      industry_reports: [{ report_id: "i1", title: "软件行业周报", publish_date: "2026-08-07", organization: "行业机构", rating: "中性", industry: "软件开发", eps_this_year: null, eps_next_year: null, eps_next_two_year: null, pdf_url: null }],
      industry_name: "软件开发", industry_code: "1238", industry_board_code: "BK0737",
      peer_candidates: [],
      unlocks: [{ free_date: "2099-09-01", stock_type: "首发限售", shares: "100000000", ratio_percent: "2.5" }],
      margin: [{ trade_date: "2026-08-08", financing_balance: "200000000", financing_buy: "10000000", securities_lending_balance: "1000000", total_balance: "201000000" }],
      holders: [{ period: "2026-06-30", holder_count: "50000", change_ratio_percent: "-3.2", average_free_shares: "1200" }],
      sources: ["eastmoney-reportapi", "eastmoney-datacenter"], reasons: [],
    }} />);

    const panel = screen.getByRole("region", { name: "机构研究与筹码证据" });
    expect(panel).toHaveTextContent("明年 EPS 中位1.50");
    expect(panel).toHaveTextContent("未来解禁1");
    expect(panel).toHaveTextContent("融资余额2.00亿");
    expect(panel).toHaveTextContent("股东户数变化-3.20%");
    expect(screen.getByRole("link", { name: "查看研报：盈利预测更新" })).toHaveAttribute("href", "https://example.com/r1.pdf");
  });

  it("keeps first-time background collection explicit", () => {
    render(<ResearchEnrichmentPanel />);
    expect(screen.getByText("后台采集中")).toBeInTheDocument();
    expect(screen.getByText(/页面不等待远程接口/)).toBeInTheDocument();
  });

  it("shows automatically selected same-industry peers and adds one to comparison", () => {
    const onAddPeer = vi.fn();
    render(<ResearchEnrichmentPanel currentSymbol="600001" onAddPeer={onAddPeer} value={{
      status: "ready", observed_at: "2026-08-10T10:00:00+08:00",
      stock_reports: [], industry_reports: [],
      industry_name: "软件开发", industry_code: "1238", industry_board_code: "BK0737",
      peer_candidates: [
        { symbol: "600001", name: "当前公司", industry: "软件开发", price: "20", change_percent: "1.2", pe_ttm: "25", pb: "3.2", market_cap_yi: "120" },
        { symbol: "600002", name: "同行甲", industry: "软件开发", price: "18", change_percent: "-0.5", pe_ttm: "30", pb: "2.8", market_cap_yi: "90" },
      ],
      unlocks: [], margin: [], holders: [], sources: ["eastmoney-push2"], reasons: [],
    }} />);

    const peers = screen.getByRole("region", { name: "系统自动筛选同行" });
    expect(peers).toHaveTextContent("软件开发");
    expect(peers).toHaveTextContent("BK0737");
    expect(peers).toHaveTextContent("同行甲");
    expect(peers).not.toHaveTextContent("当前公司");
    screen.getByRole("button", { name: "将同行甲加入同行比较" }).click();
    expect(onAddPeer).toHaveBeenCalledWith("600002", "同行甲");
  });
});
