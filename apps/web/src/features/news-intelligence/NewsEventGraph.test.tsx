import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NewsEventGraph } from "./NewsEventGraph";
import type { Interpretation, NewsEvent } from "./types";

const citation = (publisher: string, id: string) => ({ citation_id: id, article_id: id, canonical_url: `https://example.com/${id}`, publisher, published_at: "2026-08-11T09:00:00+08:00", quoted_text: "已核验原文", content_hash: "a".repeat(64) });
const event: NewsEvent = {
  event_id: "event-1", event_type: "announcement", headline: "公司披露产能建设进展",
  occurred_at: "2026-08-11T09:00:00+08:00", normalized_at: "2026-08-11T09:01:00+08:00",
  affected_instruments: [["a_share", "600000"]], industries: ["银行"], themes: ["资本开支"],
  citations: [citation("上交所", "c1"), citation("证券时报", "c2"), citation("上交所", "c3")],
  association_confidence: "1", association_kind: "direct", association_reasons: ["正文明确提及股票代码"], review_state: "verified",
};
const interpretation: Interpretation = {
  interpretation_id: "i1", event_id: "event-1", generated_at: "2026-08-11T09:02:00+08:00",
  provider: "openai-compatible", model: "configured", prompt_version: "v1", latency_ms: 20,
  degraded: false, impact_direction: "positive", confidence: "0.82", contrary_citation_ids: [],
  provider_attempts: 1, invalid_output_count: 0, provider_error_count: 0, statements: [], citations: [],
};

describe("NewsEventGraph", () => {
  const unifiedEvent = {
    event_id: "event-1", source_event_type: "announcement", category: "company_announcement" as const,
    category_reason: "event_type:announcement", headline: event.headline, occurred_at: event.occurred_at,
    affected_symbols: ["600000"], industries: ["银行"], themes: ["资本开支"], direction: "positive" as const,
    direction_confidence: "0.82", strength: "medium" as const, credibility: "multi_source_verified" as const,
    source_count: 2, duration: "unknown" as const, price_reflection: "unknown" as const,
    follow_up_indicators: ["核对公告执行进度、后续公告和交易所问询"], interpretation_id: "i1", evidence_ids: ["c1", "c2"],
  };

  it("shows the unified category legend and follow-up without replacing the original event id", () => {
    render(<NewsEventGraph events={[event]} interpretations={[interpretation]} unifiedEvents={[unifiedEvent]} onSelect={vi.fn()} />);

    const graph = screen.getByRole("region", { name: "新闻事件关系图" });
    expect(graph.querySelector('[data-event-id="event-1"]')).toHaveAttribute("data-category", "company_announcement");
    expect(graph).toHaveTextContent("公司公告");
    expect(graph).toHaveTextContent("颜色表示事件归属，不表示涨跌");
    expect(graph).toHaveTextContent("核对公告执行进度、后续公告和交易所问询");
  });
  it("deduplicates events and shows verified stock-sector-theme relationships", () => {
    const onSelect = vi.fn();
    render(<NewsEventGraph events={[event, { ...event, headline: "重复记录" }]} interpretations={[interpretation]} onSelect={onSelect} />);

    const graph = screen.getByRole("region", { name: "新闻事件关系图" });
    expect(graph.querySelectorAll("[data-event-id]")).toHaveLength(1);
    expect(graph).toHaveTextContent("2 个来源");
    expect(graph).toHaveTextContent("600000");
    expect(graph).toHaveTextContent("银行");
    expect(graph).toHaveTextContent("资本开支");
    expect(graph).toHaveTextContent("正向证据");
    fireEvent.click(screen.getByRole("button", { name: /公司披露产能建设进展/ }));
    expect(onSelect).toHaveBeenCalledWith(event);
  });

  it("keeps impact neutral when review or interpretation evidence is insufficient", () => {
    render(<NewsEventGraph
      events={[{ ...event, review_state: "pending" }]}
      interpretations={[interpretation]}
      onSelect={vi.fn()}
    />);

    const graph = screen.getByRole("region", { name: "新闻事件关系图" });
    expect(graph).toHaveTextContent("方向待核验");
    expect(graph).not.toHaveTextContent("正向证据");
  });

  it("does not infer full-market scope from an empty direct association", () => {
    render(<NewsEventGraph
      events={[{ ...event, affected_instruments: [], industries: [], themes: [] }]}
      interpretations={[interpretation]}
      onSelect={vi.fn()}
    />);

    const graph = screen.getByRole("region", { name: "新闻事件关系图" });
    expect(graph).toHaveTextContent("关联待核验");
    expect(graph).not.toHaveTextContent("全市场");
  });

  it("shows verified macro events as full-market scope", () => {
    render(<NewsEventGraph
      events={[{ ...event, affected_instruments: [], industries: [], themes: [], association_kind: "macro", association_reasons: [] }]}
      interpretations={[interpretation]}
      onSelect={vi.fn()}
    />);

    const graph = screen.getByRole("region", { name: "新闻事件关系图" });
    expect(graph).toHaveTextContent("全市场");
    expect(graph).not.toHaveTextContent("关联待核验");
  });
});
