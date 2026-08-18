import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useQuantLiveResource } from "./useQuantLiveRefresh";

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
}: {
  loader: () => Promise<{ value: string }>;
  intervalMs?: number;
  external?: { value: string };
}) {
  const state = useQuantLiveResource({
    loader,
    intervalMs,
    enabled: true,
    errorMessage: "加载失败",
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

  it("cleans up timers after unmount", async () => {
    const loader = vi.fn(async () => ({ value: "verified" }));
    const view = render(<Fixture loader={loader} />);
    await flushPromises();
    expect(loader).toHaveBeenCalledTimes(1);

    view.unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });

    expect(loader).toHaveBeenCalledTimes(1);
  });
});
