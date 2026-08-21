import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useQuantLiveResource } from "./useQuantLiveRefresh";
import { shanghaiDay } from "../../shared/tradingDayContext";

function setDocumentHidden(value: boolean) {
  Object.defineProperty(document, "hidden", {
    configurable: true,
    value,
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

async function flushPromises() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function Fixture({
  loader,
  intervalMs = 1000,
  external,
  cacheKey,
  cacheDay = shanghaiDay(new Date()),
  initialDelayMs = 0,
  polling = true,
}: {
  loader: (signal?: AbortSignal) => Promise<{ value: string }>;
  intervalMs?: number;
  external?: { value: string };
  cacheKey?: string;
  cacheDay?: string;
  initialDelayMs?: number;
  polling?: boolean;
}) {
  const state = useQuantLiveResource({
    loader,
    intervalMs,
    enabled: true,
    errorMessage: "加载失败",
    initialDelayMs,
    polling,
    cache: cacheKey ? {
      key: cacheKey,
      day: cacheDay,
      validate: (value: unknown): value is { value: string } => (
        typeof value === "object" && value !== null && typeof (value as { value?: unknown }).value === "string"
      ),
    } : undefined,
  });
  return <div>
    <span data-testid="value">{state.data?.value ?? "empty"}</span>
    <span data-testid="status">{state.status}</span>
    <span data-testid="error">{state.error}</span>
    {external && <button type="button" onClick={() => state.acceptExternal(external)}>外部快照</button>}
  </div>;
}

describe("useQuantLiveResource", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    setDocumentHidden(false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("loads immediately and refreshes on the configured interval", async () => {
    const loader = vi.fn()
      .mockResolvedValueOnce({ value: "first" })
      .mockResolvedValueOnce({ value: "second" });

    render(<Fixture loader={loader} />);

    await flushPromises();
    expect(screen.getByTestId("value")).toHaveTextContent("first");
    expect(loader).toHaveBeenCalledTimes(1);

    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });

    await flushPromises();
    expect(screen.getByTestId("value")).toHaveTextContent("second");
    expect(loader).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId("status")).toHaveTextContent("live");
  });

  it("can disable polling while retaining the first load and external snapshot path", async () => {
    const loader = vi.fn(async () => ({ value: "first" }));
    render(<Fixture loader={loader} intervalMs={1000} polling={false} external={{ value: "streamed" }} />);
    await flushPromises();
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(loader).toHaveBeenCalledTimes(1);
    await act(async () => { screen.getByRole("button", { name: "外部快照" }).click(); });
    expect(screen.getByTestId("value")).toHaveTextContent("streamed");
  });

  it("pauses while hidden and refreshes immediately when visible again", async () => {
    const loader = vi.fn(async () => ({ value: String(Date.now()) }));
    render(<Fixture loader={loader} />);
    await flushPromises();
    expect(loader).toHaveBeenCalledTimes(1);

    act(() => setDocumentHidden(true));
    expect(screen.getByTestId("status")).toHaveTextContent("paused");
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(loader).toHaveBeenCalledTimes(1);

    act(() => setDocumentHidden(false));
    await flushPromises();
    expect(loader).toHaveBeenCalledTimes(2);
  });

  it("keeps the last verified value when a later refresh fails", async () => {
    const loader = vi.fn()
      .mockResolvedValueOnce({ value: "verified" })
      .mockRejectedValueOnce(new Error("offline"));
    render(<Fixture loader={loader} />);
    await flushPromises();
    expect(screen.getByTestId("value")).toHaveTextContent("verified");

    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });

    await flushPromises();
    expect(screen.getByTestId("status")).toHaveTextContent("delayed");
    expect(screen.getByTestId("value")).toHaveTextContent("verified");
    expect(screen.getByTestId("error")).toHaveTextContent("加载失败");
  });

  it("accepts a verified external snapshot without waiting for polling", async () => {
    const loader = vi.fn(async () => ({ value: "initial" }));
    render(<Fixture loader={loader} external={{ value: "streamed" }} />);
    await flushPromises();
    await act(async () => { screen.getByRole("button", { name: "外部快照" }).click(); });
    expect(screen.getByTestId("value")).toHaveTextContent("streamed");
    expect(screen.getByTestId("status")).toHaveTextContent("live");
  });

  it("ignores a slow response from the previous loader after selection changes", async () => {
    let resolveFirst: ((value: { value: string }) => void) | undefined;
    const first = vi.fn(() => new Promise<{ value: string }>((resolve) => {
      resolveFirst = resolve;
    }));
    const second = vi.fn(async () => ({ value: "new-selection" }));
    const view = render(<Fixture loader={first} />);
    await flushPromises();
    expect(first).toHaveBeenCalledTimes(1);

    view.rerender(<Fixture loader={second} />);
    await flushPromises();
    expect(second).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("value")).toHaveTextContent("new-selection");

    resolveFirst?.({ value: "old-selection" });
    await flushPromises();
    expect(screen.getByTestId("value")).toHaveTextContent("new-selection");
  });

  it("aborts the previous request when the loader changes", async () => {
    let previousSignal: AbortSignal | undefined;
    const first = vi.fn((signal?: AbortSignal) => {
      previousSignal = signal;
      return new Promise<{ value: string }>(() => undefined);
    });
    const second = vi.fn(async () => ({ value: "new-selection" }));
    const view = render(<Fixture loader={first} />);
    await flushPromises();

    view.rerender(<Fixture loader={second} />);
    await flushPromises();

    expect(previousSignal).toBeInstanceOf(AbortSignal);
    expect(previousSignal?.aborted).toBe(true);
    expect(second).toHaveBeenCalledTimes(1);
  });

  it("cleans up timers after unmount", async () => {
    const loader = vi.fn(async () => ({ value: "verified" }));
    const view = render(<Fixture loader={loader} />);
    await flushPromises();
    expect(loader).toHaveBeenCalledTimes(1);

    view.unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });

    expect(loader).toHaveBeenCalledTimes(1);
  });

  it("restores a validated same-day last-good snapshot before the next request finishes", async () => {
    const first = render(<Fixture loader={vi.fn(async () => ({ value: "cached" }))} cacheKey="tick:600519" />);
    await flushPromises();
    expect(screen.getByTestId("value")).toHaveTextContent("cached");
    first.unmount();

    const pending = vi.fn(() => new Promise<{ value: string }>(() => undefined));
    render(<Fixture loader={pending} cacheKey="tick:600519" />);

    expect(screen.getByTestId("value")).toHaveTextContent("cached");
    expect(screen.getByTestId("status")).toHaveTextContent("delayed");
    await flushPromises();
    expect(pending).toHaveBeenCalledTimes(1);
  });

  it("delays low-priority initial work without delaying cached content", async () => {
    const loader = vi.fn(async () => ({ value: "fresh" }));
    render(<Fixture loader={loader} initialDelayMs={800} />);

    await flushPromises();
    expect(loader).not.toHaveBeenCalled();
    expect(screen.getByTestId("status")).toHaveTextContent("loading");

    await act(async () => { await vi.advanceTimersByTimeAsync(799); });
    expect(loader).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    await flushPromises();
    expect(loader).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("value")).toHaveTextContent("fresh");
  });

  it("clears yesterday's in-memory value at Shanghai day rollover", async () => {
    vi.setSystemTime(new Date("2026-08-20T15:59:59.500Z"));
    const loader = vi.fn()
      .mockResolvedValueOnce({ value: "previous-day" })
      .mockRejectedValueOnce(new Error("new day unavailable"));
    render(<Fixture loader={loader} cacheKey="tick:600519" cacheDay="2026-08-20" />);
    await flushPromises();
    expect(screen.getByTestId("value")).toHaveTextContent("previous-day");

    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    await flushPromises();

    expect(screen.getByTestId("value")).toHaveTextContent("empty");
    expect(screen.getByTestId("status")).toHaveTextContent("error");
  });
});
