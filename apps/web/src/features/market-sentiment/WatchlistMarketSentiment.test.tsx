import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WatchlistMarketSentiment } from "./WatchlistMarketSentiment";
import type { MarketSentimentResponse, MarketSentimentSnapshot } from "./types";

function snapshot(
  overrides: Partial<MarketSentimentSnapshot> = {},
): MarketSentimentSnapshot {
  return {
    snapshot_id: "sentiment-watchlist",
    previous_snapshot_id: null,
    trading_date: "2026-07-17",
    phase: "postclose",
    quality: "partial",
    freshness: "stale",
    score: "28.74",
    band: "cold",
    coverage_percent: "71.95",
    components: [],
    drivers: [],
    risks: ["市场承接偏弱"],
    beginner_guidance: "控制仓位，等待市场宽度改善后再提高进攻性。",
    observed_at: "2026-07-17T15:00:00+08:00",
    generated_at: "2026-07-17T15:00:05+08:00",
    source_snapshot_ids: ["source-1"],
    formula_version: "a-share-sentiment-v1",
    ...overrides,
  };
}

function response(
  item: MarketSentimentSnapshot | null = snapshot(),
  overrides: Partial<MarketSentimentResponse> = {},
): MarketSentimentResponse {
  return {
    trading_date: "2026-07-18",
    phase: "premarket",
    display_mode: "previous_close_baseline",
    current: null,
    previous_close: item,
    trajectory: [],
    ...overrides,
  };
}

describe("WatchlistMarketSentiment", () => {
  it("shows a partial stale market score without presenting it as a stock score", async () => {
    render(<WatchlistMarketSentiment load={() => Promise.resolve(response())} />);

    const region = await screen.findByRole("region", { name: "自选股市场环境" });
    expect(region).toHaveTextContent("A 股全市场环境");
    expect(region).toHaveTextContent("不是个股评分");
    expect(region).toHaveTextContent("29");
    expect(region).toHaveTextContent("低迷");
    expect(region).toHaveTextContent("覆盖率 72%");
    expect(region).toHaveTextContent("部分可用");
    expect(region).toHaveTextContent("历史参考");
    expect(region).toHaveTextContent("控制仓位，等待市场宽度改善后再提高进攻性。");
    expect(region.querySelector("time")).toHaveAttribute("datetime", "2026-07-17T15:00:00+08:00");
  });

  it("does not invent a numeric score when the snapshot is unavailable", async () => {
    const unavailable = snapshot({
      quality: "unavailable",
      freshness: "current",
      score: null,
      band: "unavailable",
      coverage_percent: "42",
      beginner_guidance: "等待核心行情来源恢复后再判断。",
    });
    render(<WatchlistMarketSentiment load={() => Promise.resolve(response(unavailable))} />);

    const region = await screen.findByRole("region", { name: "自选股市场环境" });
    expect(region).toHaveTextContent("暂不可用");
    expect(region).toHaveTextContent("等待核心行情来源恢复后再判断。");
    expect(region).not.toHaveTextContent("/ 100");
    expect(region.querySelector("[data-testid='watchlist-sentiment-score']")).toBeNull();
  });

  it("keeps the watchlist usable after a load failure and retries", async () => {
    const load = vi.fn()
      .mockRejectedValueOnce(new Error("network offline"))
      .mockResolvedValueOnce(response());
    render(<WatchlistMarketSentiment load={load} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("市场情绪暂不可用");
    fireEvent.click(screen.getByRole("button", { name: "重试市场情绪" }));

    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("低迷")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
