import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FirstLimitUpView } from "./FirstLimitUpView";
import type { FirstLimitUpBoard } from "./types";


const board: FirstLimitUpBoard = {
  asset: "a_share",
  status: "ready",
  as_of: "2026-07-24",
  rule_version: "first-limit-up-v1",
  universe_count: 5980,
  history_eligible_count: 5980,
  scan_coverage_count: 5980,
  coverage_complete: true,
  scanned_count: 2,
  qualified_count: 1,
  pullback_window_count: 1,
  no_buy_count: 1,
  priority_symbol: "600001",
  missing_data: [],
  sources: ["local-daily-bars", "tencent-quote"],
  today: [{
    symbol: "600001", name: "底部样本", as_of: "2026-07-24", limit_up_date: "2026-07-24",
    limit_up_close: "11", current_close: "11", pe_ttm: "22", limit_rate: "0.1",
    weekly_distance_to_low: "0.1", monthly_distance_to_low: "0.1", weekly_bottom: true,
    monthly_bottom: true, pullback_pct: "0", consolidation_days: 0,
    selection_status: "qualified", stage: "limit_up_day", action: "no_buy", score: "68.4",
    reasons: [], risk_flags: ["limit_up_day_no_buy"], sources: ["local-daily-bars", "tencent-quote"],
    entry_reference: { buy_steps_pct: ["-0.02", "-0.05", "-0.08"], sell_steps_pct: ["0.03", "0.06", "0.1"], note: "仅观察" },
  }],
  pool: [{
    symbol: "600001", name: "底部样本", as_of: "2026-07-31", limit_up_date: "2026-07-24",
    limit_up_close: "11", current_close: "10.2", pe_ttm: "22", limit_rate: "0.1",
    weekly_distance_to_low: "0.1", monthly_distance_to_low: "0.1", weekly_bottom: true,
    monthly_bottom: true, pullback_pct: "0.0727", consolidation_days: 5,
    selection_status: "qualified", stage: "pullback_window", action: "staged_entry_reference", score: "76.4",
    reasons: [], risk_flags: [], sources: ["local-daily-bars", "tencent-quote"],
    entry_reference: { buy_steps_pct: ["-0.02", "-0.05", "-0.08"], sell_steps_pct: ["0.03", "0.06", "0.1"], note: "仅观察" },
  }],
};


describe("FirstLimitUpView", () => {
  it("uses the shared terminal page shell", async () => {
    render(<FirstLimitUpView load={() => Promise.resolve(board)} refresh={() => Promise.resolve(board)} />);

    expect(screen.getByRole("main", { name: "首次涨停研究域" }))
      .toHaveClass("terminal-page", "first-limit-up-page");
    expect(await screen.findByRole("heading", { name: "首次涨停" })).toBeInTheDocument();
  });

  it("shows evidence summary, blocks the limit-up day, and explains the pullback ladder", async () => {
    const refresh = vi.fn(() => Promise.resolve(board));
    render(<FirstLimitUpView load={() => Promise.resolve(board)} refresh={refresh} />);

    expect(await screen.findByRole("heading", { name: "首次涨停" })).toBeInTheDocument();
    expect(screen.getByText("禁止买入" )).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "首次涨停摘要" })).toHaveTextContent(/已识别涨停\s*2\s*只/);
    expect(screen.getByRole("tab", { name: "识别结果" })).toBeInTheDocument();
    expect(screen.queryByText("-2%")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "首次涨停标的详情" })).toHaveTextContent("涨停当日禁止买入，暂不启用分批观察阶梯");

    fireEvent.click(screen.getByRole("tab", { name: "回撤池" }));

    expect(screen.getByRole("region", { name: "首次涨停标的详情" })).toHaveTextContent("进入回撤窗口");
    expect(screen.getByText(/分批观察阶梯/)).toBeInTheDocument();
    expect(screen.getByText("-2%")).toBeInTheDocument();
    expect(screen.getByText("-5%")).toBeInTheDocument();
    expect(screen.getByText("-8%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "刷新首次涨停" }));
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  });

  it("turns summary counts into precise filters and opens the first matching detail", async () => {
    const filterBoard: FirstLimitUpBoard = {
      ...board,
      scanned_count: 3,
      qualified_count: 2,
      no_buy_count: 1,
      today: [
        board.today[0],
        {
          ...board.today[0],
          symbol: "600002",
          name: "合格观察样本",
          stage: "waiting_pullback",
          action: "observe",
          score: "64.2",
          risk_flags: [],
        },
        {
          ...board.today[0],
          symbol: "600003",
          name: "规则排除样本",
          selection_status: "excluded",
          stage: "limit_up_day",
          action: "avoid",
          score: "21.0",
          reasons: ["pe_above_50"],
          risk_flags: [],
        },
      ],
    };
    render(<FirstLimitUpView load={() => Promise.resolve(filterBoard)} refresh={() => Promise.resolve(filterBoard)} />);

    const list = await screen.findByRole("region", { name: "首次涨停候选列表" });
    expect(list).toHaveTextContent("底部样本");
    expect(list).toHaveTextContent("合格观察样本");
    expect(list).toHaveTextContent("规则排除样本");

    fireEvent.click(screen.getByRole("button", { name: /筛选规则合格股票，共 2 只/ }));
    expect(list).toHaveTextContent("规则合格 · 2 只");
    expect(list).toHaveTextContent("底部样本");
    expect(list).toHaveTextContent("合格观察样本");
    expect(list).not.toHaveTextContent("规则排除样本");

    fireEvent.click(screen.getByRole("button", { name: /筛选回撤窗口股票，共 1 只/ }));
    expect(screen.getByRole("tab", { name: "回撤池" })).toHaveAttribute("aria-selected", "true");
    expect(list).toHaveTextContent("回撤窗口 · 1 只");
    expect(list).toHaveTextContent("底部样本");
    expect(screen.getByRole("region", { name: "首次涨停标的详情" })).toHaveTextContent("进入回撤窗口");

    fireEvent.click(screen.getByRole("button", { name: /筛选涨停日禁买股票，共 1 只/ }));
    expect(screen.getByRole("tab", { name: "识别结果" })).toHaveAttribute("aria-selected", "true");
    expect(list).toHaveTextContent("涨停日禁买 · 1 只");
    expect(within(list).getByRole("button", { name: /600001.*底部样本/ })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "首次涨停标的详情" })).toHaveTextContent("涨停当日不能买入");

    fireEvent.click(screen.getByRole("button", { name: "查看当前分组全部股票" }));
    expect(list).toHaveTextContent("本次已识别涨停 · 3 只");
    expect(list).toHaveTextContent("规则排除样本");
  });

  it("shows source and priority context, readable bottom states, and neutral evidence for incomplete candidates", async () => {
    const incompleteBoard: FirstLimitUpBoard = {
      ...board,
      priority_symbol: "600002",
      sources: ["local-daily-bars", "tencent-quote"],
      today: [{
        ...board.today[0],
        symbol: "600002", name: "待验证样本", pe_ttm: "not-a-number",
        weekly_bottom: null, monthly_bottom: null,
        selection_status: "data_insufficient", stage: "data_insufficient", action: "data_insufficient",
        reasons: [], risk_flags: ["缺少市盈率和周/月线数据"],
      }],
    };
    render(<FirstLimitUpView load={() => Promise.resolve(incompleteBoard)} refresh={() => Promise.resolve(incompleteBoard)} />);

    expect(await screen.findByText("数据来源")).toBeInTheDocument();
    expect(screen.getByText("本地日线 / 腾讯行情")).toBeInTheDocument();
    expect(screen.getByText("优先观察项")).toBeInTheDocument();
    expect(screen.getByText("600002 · 待验证样本")).toBeInTheDocument();
    const row = screen.getByRole("button", { name: /600002.*待验证样本/ });
    expect(row).toHaveTextContent("周线底部：待验证");
    expect(row).toHaveTextContent("月线底部：待验证");
    expect(row.querySelector(".first-limit-up-number")).toHaveTextContent("待验证");
    const detail = screen.getByRole("region", { name: "首次涨停标的详情" });
    expect(detail).toHaveTextContent("待验证");
    expect(detail).toHaveTextContent("关键数据尚未完整，不适用分批观察阶梯");
    expect(screen.queryByText("-2%")).not.toBeInTheDocument();
    expect(detail).not.toHaveTextContent("估值与周/月线位置通过");
    expect(detail).not.toHaveTextContent("NaN");
  });

  it("distinguishes excluded candidates, translates rule codes, and hides inapplicable ladders", async () => {
    const excludedBoard: FirstLimitUpBoard = {
      ...board,
      qualified_count: 0,
      priority_symbol: "600003",
      today: [{
        ...board.today[0],
        symbol: "600003", name: "规则排除样本", pe_ttm: "68",
        weekly_distance_to_low: "0.994", monthly_distance_to_low: "0.925",
        weekly_bottom: false, monthly_bottom: false,
        selection_status: "excluded", stage: "limit_up_day", action: "avoid", score: "0",
        reasons: [
          "recent_limit_up_within_20_bars",
          "pe_above_50",
          "weekly_not_at_bottom",
          "monthly_not_at_bottom",
        ],
        risk_flags: ["limit_up_day_no_buy"],
      }],
    };
    render(<FirstLimitUpView load={() => Promise.resolve(excludedBoard)} refresh={() => Promise.resolve(excludedBoard)} />);

    const detail = await screen.findByRole("region", { name: "首次涨停标的详情" });
    expect(detail).toHaveTextContent("规则未通过，暂不进入观察池");
    expect(detail).not.toHaveTextContent("数据不足，暂不判定通过");
    expect(detail).not.toHaveTextContent("回撤超过 20%");
    expect(detail).toHaveTextContent("近 20 个交易日内已有涨停，不属于阶段首次涨停");
    expect(detail).toHaveTextContent("市盈率超过 50 倍");
    expect(detail).toHaveTextContent("周线位置不在底部区域");
    expect(detail).toHaveTextContent("月线位置不在底部区域");
    expect(detail).toHaveTextContent("涨停当日只记录，不买入");
    expect(detail).not.toHaveTextContent("recent_limit_up_within_20_bars");
    expect(detail).not.toHaveTextContent("limit_up_day_no_buy");
    expect(detail).toHaveTextContent("当前规则未通过，不适用分批观察阶梯");
    expect(screen.queryByText("-2%")).not.toBeInTheDocument();
    expect(screen.queryByText("-5%")).not.toBeInTheDocument();
    expect(screen.queryByText("-8%")).not.toBeInTheDocument();
    expect(screen.queryByText("+3%")).not.toBeInTheDocument();
  });

  it("explains that incomplete records may still be opened", async () => {
    const emptyBoard: FirstLimitUpBoard = {
      ...board,
      scanned_count: 0,
      qualified_count: 0,
      pullback_window_count: 0,
      no_buy_count: 0,
      priority_symbol: null,
      today: [],
      pool: [],
    };
    render(<FirstLimitUpView load={() => Promise.resolve(emptyBoard)} refresh={() => Promise.resolve(emptyBoard)} />);

    expect(await screen.findByText("列表记录可能包含待验证项，点击后查看证据。")).toBeInTheDocument();
  });

  it("warns clearly when the result covers only part of the A-share market", async () => {
    const partialBoard: FirstLimitUpBoard = {
      ...board,
      status: "partial",
      universe_count: 5980,
      history_eligible_count: 13,
      scan_coverage_count: 12,
      coverage_complete: false,
    };

    render(<FirstLimitUpView load={() => Promise.resolve(partialBoard)} refresh={() => Promise.resolve(partialBoard)} />);

    expect(await screen.findByText("当前仅为部分市场结果")).toBeInTheDocument();
    expect(screen.getByText("12 / 5,980")).toBeInTheDocument();
    expect(screen.getByText("具备 250 日历史：13 只")).toBeInTheDocument();
  });

  it("asks for a current full-market scan without exposing internal migrations", async () => {
    const pendingBoard: FirstLimitUpBoard = {
      ...board,
      status: "partial",
      coverage_complete: false,
      scanned_count: 0,
      qualified_count: 0,
      no_buy_count: 0,
      today: [],
      missing_data: ["full_market_scan_required"],
    };

    render(<FirstLimitUpView load={() => Promise.resolve(pendingBoard)} refresh={() => Promise.resolve(pendingBoard)} />);

    expect(await screen.findByText(/当前尚未完成全市场筛选/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/旧版|老版|旧数据/);
    expect(screen.getByRole("region", { name: "首次涨停摘要" })).toHaveTextContent(/已识别涨停\s*0\s*只/);
  });
});
