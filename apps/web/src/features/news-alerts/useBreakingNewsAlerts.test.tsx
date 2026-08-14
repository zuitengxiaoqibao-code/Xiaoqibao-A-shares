import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useBreakingNewsAlerts } from "./useBreakingNewsAlerts";


describe("useBreakingNewsAlerts", () => {
  afterEach(() => vi.useRealTimers());

  it("refreshes news on its own minute cadence instead of the five-second market loop", async () => {
    vi.useFakeTimers();
    const load = vi.fn(async () => ({
      status: "empty" as const,
      observed_at: "2026-08-10T10:00:00+08:00",
      alerts: [], sources: ["fixture"], warnings: [],
    }));

    renderHook(() => useBreakingNewsAlerts(load, null, 6));
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(load).toHaveBeenCalledTimes(1);

    await act(async () => { await vi.advanceTimersByTimeAsync(59_000); });
    expect(load).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(load).toHaveBeenCalledTimes(2);
  });
});
