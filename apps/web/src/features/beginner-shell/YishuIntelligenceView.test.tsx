import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MarketCloudView, YishuIntelligenceView } from "./YishuIntelligenceView";

afterEach(() => {
  delete (window as Window & { pywebview?: unknown }).pywebview;
  vi.useRealTimers();
});

describe("YishuIntelligenceView", () => {
  it("embeds the native desktop browser and hides it when leaving the route", async () => {
    const setPanel = vi.fn().mockResolvedValue({ available: true });
    Object.assign(window, { pywebview: { api: { set_review_panel: setPanel } } });
    const view = render(<YishuIntelligenceView />);
    await waitFor(() => expect(setPanel).toHaveBeenCalledWith(expect.objectContaining({ left: 0, top: 0 }), false, "intelligence"));
    expect(screen.queryByTitle("易数智算发现专区")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "刷新网页" }));
    await waitFor(() => expect(setPanel).toHaveBeenCalledWith(expect.any(Object), true, "intelligence"));
    view.unmount();
    await waitFor(() => expect(setPanel).toHaveBeenLastCalledWith(null, false, "intelligence"));
  });

  it("shows a truthful browser limitation with an in-panel iframe and no popup", async () => {
    vi.useFakeTimers();
    render(<YishuIntelligenceView />);
    await act(() => vi.advanceTimersByTimeAsync(1200));
    expect(screen.getByTitle("易数智算发现专区")).toHaveAttribute("src", "https://ysclaw.hk/discover/");
    expect(screen.getByRole("status")).toHaveTextContent("该站点当前禁止 iframe 内嵌");
  });

  it("reports native container failure instead of claiming the site loaded", async () => {
    Object.assign(window, { pywebview: { api: { set_review_panel: vi.fn().mockResolvedValue({ available: false, error: "网页容器不可用" }) } } });
    render(<YishuIntelligenceView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("网页容器不可用");
  });

  it("embeds the cloud website in a browser without the intelligence site's restriction notice", async () => {
    vi.useFakeTimers();
    render(<MarketCloudView />);
    await act(() => vi.advanceTimersByTimeAsync(1200));
    expect(screen.getByTitle("大盘云图网页")).toHaveAttribute("src", "https://a.9009009.com/");
    expect(screen.queryByText(/禁止 iframe/)).not.toBeInTheDocument();
  });

  it("hides the previous native site before switching to the cloud site and back", async () => {
    const setPanel = vi.fn().mockResolvedValue({ available: true });
    Object.assign(window, { pywebview: { api: { set_review_panel: setPanel } } });
    const view = render(<YishuIntelligenceView />);
    await waitFor(() => expect(setPanel).toHaveBeenLastCalledWith(expect.any(Object), false, "intelligence"));
    view.rerender(<MarketCloudView />);
    await waitFor(() => expect(setPanel).toHaveBeenLastCalledWith(expect.any(Object), false, "market_cloud"));
    expect(setPanel.mock.calls.slice(-2)).toEqual([[null, false, "intelligence"], [expect.any(Object), false, "market_cloud"]]);
    fireEvent.click(screen.getByRole("button", { name: "刷新网页" }));
    await waitFor(() => expect(setPanel).toHaveBeenLastCalledWith(expect.any(Object), true, "market_cloud"));
    view.rerender(<YishuIntelligenceView />);
    await waitFor(() => expect(setPanel).toHaveBeenLastCalledWith(expect.any(Object), false, "intelligence"));
    expect(setPanel.mock.calls.slice(-2)).toEqual([[null, false, "market_cloud"], [expect.any(Object), false, "intelligence"]]);
    view.unmount();
    await waitFor(() => expect(setPanel).toHaveBeenLastCalledWith(null, false, "intelligence"));
  });
});
