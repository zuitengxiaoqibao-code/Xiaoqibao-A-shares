import { act, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const registerWatchlistFocus = vi.hoisted(() => vi.fn(async () => undefined));
const loadAShareInstrumentDirectory = vi.hoisted(() => vi.fn(async () => ({ items: [] })));

vi.mock("../features/dashboard/Dashboard", () => ({
  Dashboard: () => <div>dashboard</div>,
}));

vi.mock("../features/quant-analysis/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("../features/quant-analysis/api")>(),
  registerWatchlistFocus,
}));

vi.mock("../features/stock-cockpit/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("../features/stock-cockpit/api")>(),
  loadAShareInstrumentDirectory,
}));

describe("App watchlist sampling registration", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    localStorage.clear();
    registerWatchlistFocus.mockClear();
    loadAShareInstrumentDirectory.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("restores valid A-share watchlist symbols and renews them while other pages are shown", async () => {
    localStorage.setItem(
      "qibao.a_share.watchlist.v1",
      JSON.stringify(["600000", "113065", "not-code"]),
    );

    render(<App />);

    await waitFor(() => expect(registerWatchlistFocus).toHaveBeenCalledTimes(1));
    expect(registerWatchlistFocus).toHaveBeenLastCalledWith("600000");

    await act(async () => { vi.advanceTimersByTime(5 * 60 * 1000); });

    await waitFor(() => expect(registerWatchlistFocus).toHaveBeenCalledTimes(2));
    expect(registerWatchlistFocus).toHaveBeenLastCalledWith("600000");
  });

  it("registers a newly persisted watchlist symbol immediately in the same window", async () => {
    render(<App />);
    await act(async () => undefined);

    localStorage.setItem("qibao.a_share.watchlist.v1", JSON.stringify(["000001"]));
    window.dispatchEvent(new CustomEvent("qibao:a-share-watchlist-change"));

    await waitFor(() => expect(registerWatchlistFocus).toHaveBeenCalledWith("000001"));
  });
});
