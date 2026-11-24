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
  it("rejects old and duplicate events even while hidden", () => {
    const store = new RealtimeStore();
    const listener = vi.fn();
    store.subscribe("market_overview", listener);
    store.setVisible(false);
    store.publish(event("market_overview", 2));
    store.publish(event("market_overview", 1));
    store.publish(event("market_overview", 2));
    store.setVisible(true);
    expect(store.getLatest("market_overview")?.sequence).toBe(2);
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("accepts reset sequences after a server restart and rejects the previous stream", () => {
    const store = new RealtimeStore();
    const old = { ...event("market_overview", 100), stream_id: "old", stream_started_at: "2026-11-19T00:00:00Z" };
    const fresh = { ...event("market_overview", 1), stream_id: "new", stream_started_at: "2026-11-19T01:00:00Z" };
    store.publish(old);
    store.publish(fresh);
    store.publish({ ...old, sequence: 101 });
    expect(store.getLatest("market_overview")?.sequence).toBe(1);
    expect(store.getLatest("market_overview")?.stream_id).toBe("new");
  });

  it("isolates snapshot mutations across producers and listeners", () => {
    const store = new RealtimeStore();
    store.subscribe("market_overview", (snapshot) => { (snapshot.payload as { value: number }).value = 90; });
    const snapshot = event("market_overview", 1);
    store.publish(snapshot);
    snapshot.payload.value = 80;
    store.getLatest<{ value: number }>("market_overview")!.payload.value = 70;
    expect(store.getLatest<{ value: number }>("market_overview")?.payload.value).toBe(1);
  });

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
