import { describe, expect, it, vi } from "vitest";

import type { RealtimeStreamEvent } from "../realtimeStream";
import { RealtimeStore } from "./realtimeStore";

function event(kind: string, sequence: number): RealtimeStreamEvent<{ value: number }> {
  return {
    event_id: `${kind}-${sequence}`,
    kind,
    sequence,
    observed_at: "2026-08-21T01:30:00Z",
    source: "test",
    freshness: "live",
    payload: { value: sequence },
  };
}

describe("RealtimeStore", () => {
  it("delivers only matching topics to each subscriber", () => {
    const store = new RealtimeStore();
    const market = vi.fn();
    const news = vi.fn();
    store.subscribe("market_overview", market);
    store.subscribe("news_events", news);

    store.publish(event("market_overview", 1));

    expect(market).toHaveBeenCalledWith(expect.objectContaining({ sequence: 1 }));
    expect(news).not.toHaveBeenCalled();
  });

  it("suppresses refresh work while hidden and flushes only the latest event when visible", () => {
    const store = new RealtimeStore();
    const listener = vi.fn();
    store.subscribe("market_overview", listener);
    store.setVisible(false);

    store.publish(event("market_overview", 1));
    store.publish(event("market_overview", 2));
    expect(listener).not.toHaveBeenCalled();

    store.setVisible(true);
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith(expect.objectContaining({ sequence: 2 }));
  });

  it("keeps the stream alive until the last subscriber leaves", () => {
    const store = new RealtimeStore();
    const first = store.subscribe("quant_strategy", vi.fn());
    const second = store.subscribe("quant_strategy", vi.fn());
    expect(store.subscriberCount).toBe(2);
    first();
    expect(store.subscriberCount).toBe(1);
    second();
    expect(store.subscriberCount).toBe(0);
  });
});
