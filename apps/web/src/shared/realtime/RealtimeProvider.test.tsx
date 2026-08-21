import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { RealtimeStreamEvent } from "../realtimeStream";
import {
  RealtimeProvider,
  type RealtimeConsumer,
  useRealtimeFallback,
  useRealtimeFallbackTick,
  useRealtimeState,
  useRealtimeTopic,
} from "./RealtimeProvider";

const topics = ["market_overview", "news_events"] as const;

function Probe({ topic }: { topic: string }) {
  const latest = useRealtimeTopic<{ value: number }>(topic);
  const state = useRealtimeState();
  const fallback = useRealtimeFallback();
  const fallbackTick = useRealtimeFallbackTick();
  return <output>{`${state}:${latest?.payload.value ?? 0}:${fallback}:${fallbackTick}`}</output>;
}

describe("RealtimeProvider", () => {
  it("opens one network stream for all mounted topic subscribers", async () => {
    let emit: ((event: RealtimeStreamEvent) => void) | undefined;
    const consume: RealtimeConsumer = vi.fn(async (receivedTopics, onEvent, signal, onState) => {
      expect(receivedTopics).toEqual(topics);
      emit = onEvent;
      onState?.("connected");
      await new Promise<void>((resolve) => signal.addEventListener("abort", () => resolve(), { once: true }));
    });
    render(
      <RealtimeProvider topics={topics} consume={consume}>
        <Probe topic="market_overview" />
        <Probe topic="news_events" />
      </RealtimeProvider>,
    );
    await act(async () => undefined);
    expect(consume).toHaveBeenCalledTimes(1);

    act(() => emit?.({
      event_id: "market-1", kind: "market_overview", sequence: 1,
      observed_at: "2026-08-21T01:30:00Z", source: "test", freshness: "live",
      payload: { value: 7 },
    }));
    expect(screen.getByText("connected:7:0:0")).toBeInTheDocument();
    expect(screen.getByText("connected:0:0:0")).toBeInTheDocument();
  });

  it("uses one exponential-backoff fallback schedule and stops it after reconnecting", async () => {
    vi.useFakeTimers();
    let attempt = 0;
    const consume: RealtimeConsumer = vi.fn(async (_topics, _onEvent, signal, onState) => {
      attempt += 1;
      if (attempt === 1) {
        onState?.("error");
        throw new Error("offline");
      }
      onState?.("connected");
      await new Promise<void>((resolve) => signal.addEventListener("abort", () => resolve(), { once: true }));
    });
    render(
      <RealtimeProvider topics={topics} consume={consume} reconnectDelaysMs={[100, 200]}>
        <Probe topic="market_overview" />
        <Probe topic="news_events" />
      </RealtimeProvider>,
    );
    await act(async () => undefined);
    expect(screen.getAllByText("error:0:1:0")).toHaveLength(2);

    await act(async () => { vi.advanceTimersByTime(100); });
    expect(consume).toHaveBeenCalledTimes(2);
    expect(screen.getAllByText("connected:0:0:0")).toHaveLength(2);
    await act(async () => { vi.advanceTimersByTime(500); });
    expect(consume).toHaveBeenCalledTimes(2);
  });

  it("emits one shared fallback tick for all subscribers while disconnected", async () => {
    vi.useFakeTimers();
    const consume: RealtimeConsumer = vi.fn(async (_topics, _onEvent, _signal, onState) => {
      onState?.("error");
      throw new Error("offline");
    });
    render(
      <RealtimeProvider topics={topics} consume={consume} reconnectDelaysMs={[60_000]} fallbackIntervalMs={100}>
        <Probe topic="market_overview" />
        <Probe topic="news_events" />
      </RealtimeProvider>,
    );
    await act(async () => undefined);
    await act(async () => { vi.advanceTimersByTime(100); });
    expect(screen.getAllByText("error:0:1:1")).toHaveLength(2);
    await act(async () => { vi.advanceTimersByTime(100); });
    expect(screen.getAllByText("error:0:1:2")).toHaveLength(2);
    expect(consume).toHaveBeenCalledTimes(1);
  });
});
