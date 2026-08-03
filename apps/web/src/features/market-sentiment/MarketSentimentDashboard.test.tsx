import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MarketSentimentDashboard } from "./MarketSentimentDashboard";
import type {
  MarketSentimentResponse,
  MarketSentimentSnapshot,
  SentimentBand,
} from "./types";


const bandNames: Record<Exclude<SentimentBand, "unavailable">, string> = {
  panic: "恐慌",
  cold: "低迷",
  neutral: "中性",
  active: "活跃",
  overheated: "过热",
};

function snapshot(
  band: Exclude<SentimentBand, "unavailable"> = "active",
  overrides: Partial<MarketSentimentSnapshot> = {},
): MarketSentimentSnapshot {
  const scores = { panic: "12", cold: "31", neutral: "52", active: "68", overheated: "84" };
  return {
    snapshot_id: `sentiment-${band}`,
    previous_snapshot_id: null,
    trading_date: "2026-07-18",
    phase: "intraday",
    quality: "ready",
    freshness: "current",
    score: scores[band],
    band,
    coverage_percent: "100",
    components: [
      { name: "breadth", score: "72", weight: "35", coverage_percent: "100", metrics: { rising_count: 3200, falling_count: 1700, flat_count: 100 }, evidence_ids: ["breadth"] },
      { name: "limit_ecology", score: "66", weight: "25", coverage_percent: "100", metrics: { limit_up_count: 58, limit_down_count: 8, broken_limit_up_count: 12 }, evidence_ids: ["limits"] },
      { name: "liquidity", score: "61", weight: "20", coverage_percent: "100", metrics: { relative_amount: "1.12" }, evidence_ids: ["liquidity"] },
      { name: "hotspot", score: "74", weight: "20", coverage_percent: "100", metrics: { unique_theme_count: 8, persistent_theme_count: 3 }, evidence_ids: ["hotspot"] },
    ],
    drivers: ["上涨股票覆盖扩大", "已核验热点出现跨阶段延续"],
    risks: ["追高和炸板风险升高"],
    beginner_guidance: "等待量价确认后再行动。",
    observed_at: "2026-07-18T10:30:00+08:00",
    generated_at: "2026-07-18T10:30:05+08:00",
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
    phase: "intraday",
    display_mode: item ? "current" : "unavailable",
    current: item,
    previous_close: null,
    trajectory: item ? [item] : [],
    ...overrides,
  };
}

describe("MarketSentimentDashboard", () => {
  it.each(Object.entries(bandNames))(
    "renders the %s score band with an accessible gauge",
    async (band, label) => {
      const item = snapshot(band as Exclude<SentimentBand, "unavailable">);
      render(<MarketSentimentDashboard load={() => Promise.resolve(response(item))} />);

      expect(await screen.findByRole("img", {
        name: `A 股市场情绪 ${Math.round(Number(item.score))} 分，${label}`,
      })).toBeInTheDocument();
    },
  );

  it("puts overheated risk before drivers and explains that a high score is not safety", async () => {
    render(<MarketSentimentDashboard load={() => Promise.resolve(response(snapshot("overheated")))} />);

    const risk = await screen.findByRole("heading", { name: "主要风险" });
    const driver = screen.getByRole("heading", { name: "为什么是这个分数" });
    expect(risk.compareDocumentPosition(driver) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("追高和炸板风险升高")).toBeInTheDocument();
  });

  it("labels partial coverage and stale results without hiding the verified score", async () => {
    const item = snapshot("active", {
      quality: "partial",
      freshness: "stale",
      coverage_percent: "80",
    });
    render(<MarketSentimentDashboard load={() => Promise.resolve(response(item))} />);

    expect(await screen.findByText("覆盖率 80% · 部分可用")).toBeInTheDocument();
    expect(screen.getByText("历史参考 · 不是当前结果")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "A 股市场情绪 68 分，活跃" })).toBeInTheDocument();
  });

  it("shows the previous close baseline before market without inventing a live score", async () => {
    const previous = snapshot("neutral", { phase: "postclose", freshness: "stale" });
    render(<MarketSentimentDashboard load={() => Promise.resolve(response(null, {
      phase: "premarket",
      display_mode: "previous_close_baseline",
      previous_close: previous,
      trajectory: [previous],
    }))} />);

    expect((await screen.findAllByText("昨收基线")).length).toBeGreaterThan(0);
    expect(screen.getByText(/盘前不生成虚假实时分数/)).toBeInTheDocument();
  });

  it("does not render a number when core market breadth is unavailable", async () => {
    const unavailable = snapshot("neutral", {
      quality: "unavailable",
      score: null,
      band: "unavailable",
      coverage_percent: "35",
      risks: ["市场宽度不可用"],
    });
    render(<MarketSentimentDashboard load={() => Promise.resolve(response(unavailable))} />);

    expect(await screen.findByRole("img", { name: "A 股市场情绪暂不可用" })).toBeInTheDocument();
    expect(document.querySelector(".sentiment-score-value")).toBeNull();
    expect(screen.getByText("市场宽度不可用")).toBeInTheDocument();
  });

  it("keeps verified history visible when a manual refresh fails", async () => {
    const load = vi.fn().mockResolvedValue(response(snapshot("active")));
    const refresh = vi.fn().mockRejectedValue(new Error("network secret-url"));
    render(<MarketSentimentDashboard load={load} refresh={refresh} />);

    await screen.findByRole("img", { name: "A 股市场情绪 68 分，活跃" });
    fireEvent.click(screen.getByRole("button", { name: "刷新市场情绪" }));

    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("img", { name: "A 股市场情绪 68 分，活跃" })).toBeInTheDocument();
    expect(screen.getByText("刷新失败，已保留最近一次可验证结果。")).toBeInTheDocument();
  });

  it("stays isolated from convertible-bond language", async () => {
    const { container } = render(
      <MarketSentimentDashboard load={() => Promise.resolve(response())} />,
    );
    await screen.findByRole("region", { name: "A 股市场情绪" });
    expect(container.textContent).not.toMatch(/转债|可转债/);
  });

  it("shows the nine-factor formula and preserves each requested weight", async () => {
    const components = ([
      ["volatility", "15"], ["activity", "15"], ["price_strength", "10"],
      ["risk_appetite", "10"], ["breadth", "15"], ["limit_ecology", "15"],
      ["money_making", "10"], ["sector_diffusion", "5"], ["style_risk_preference", "5"],
    ] as const).map(([name, weight]) => ({
      name, score: "60", weight, coverage_percent: "100", metrics: {}, evidence_ids: [],
    }));
    render(<MarketSentimentDashboard load={() => Promise.resolve(response(snapshot("active", { components, formula_version: "a-share-sentiment-v2" })))} />);

    const dashboard = await screen.findByRole("region", { name: "A 股市场情绪" });
    expect(dashboard).toHaveTextContent("波动率情绪");
    expect(dashboard).toHaveTextContent("成交活跃度");
    expect(dashboard).toHaveTextContent("价格强度");
    expect(dashboard).toHaveTextContent("风险偏好");
    expect(dashboard).toHaveTextContent("市场广度");
    expect(dashboard).toHaveTextContent("涨跌停情绪");
    expect(dashboard).toHaveTextContent("赚钱效应");
    expect(dashboard).toHaveTextContent("板块扩散情绪");
    expect(dashboard).toHaveTextContent("风格风险偏好");
    expect(dashboard).toHaveTextContent("波动率情绪 权重 15%");
    expect(dashboard).toHaveTextContent("这个分数怎么来的");
    expect(dashboard).toHaveTextContent("九因子");
  });
});
