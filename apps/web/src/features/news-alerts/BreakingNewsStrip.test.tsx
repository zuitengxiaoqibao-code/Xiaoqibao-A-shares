import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BreakingNewsStrip } from "./BreakingNewsStrip";
import type { BreakingNewsAlert } from "./types";


const alert: BreakingNewsAlert = {
  event_id: "event-alert-1",
  headline: "公司发布经核验的重要公告",
  occurred_at: "2026-07-29T10:12:00+08:00",
  verification_state: "multi_source_confirmed",
  urgency: "breaking",
  association_kind: "direct",
  association_reasons: ["company_alias:贵州茅台"],
  affected_symbols: ["600519"],
  themes: ["白酒"],
  publishers: ["上交所", "证券时报"],
  source_urls: ["https://news.example/official", "https://news.example/media"],
  source_count: 2,
  impact_direction: "uncertain",
  impact_confidence: null,
  ai_degraded: true,
};


describe("BreakingNewsStrip", () => {
  it("shows urgency, verification, association, source count and original link", () => {
    render(<BreakingNewsStrip alerts={[alert]} loading={false} error={null} />);

    const region = screen.getByRole("region", { name: "突发事件" });
    expect(region).toHaveTextContent("突发");
    expect(region).toHaveTextContent("多源确认");
    expect(region).toHaveTextContent("直接关联");
    expect(region).toHaveTextContent("2 个来源");
    expect(region).toHaveTextContent("AI 方向待核验");
    expect(screen.getByRole("link", { name: "查看原始来源" })).toHaveAttribute(
      "href",
      alert.source_urls[0],
    );
  });

  it("opens an affected A-share through the supplied navigation callback", () => {
    const onOpenAShare = vi.fn();
    render(
      <BreakingNewsStrip
        alerts={[alert]}
        loading={false}
        error={null}
        onOpenAShare={onOpenAShare}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "查看股票 600519" }));

    expect(onOpenAShare).toHaveBeenCalledWith("600519");
  });

  it("keeps the last snapshot visible while reporting a refresh failure", () => {
    render(<BreakingNewsStrip alerts={[alert]} loading={false} error="刷新失败，保留上次结果" />);

    expect(screen.getByText("公司发布经核验的重要公告")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("刷新失败，保留上次结果");
  });
});
