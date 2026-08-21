import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MonitorCenterView } from "./MonitorCenterView";

describe("MonitorCenterView", () => {
  it("shows persisted alerts and Chinese delivery states", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [{ alert_id: "a1", symbol: "600519", observed_at: "2026-08-21T02:00:00Z", delivery: { in_app: "sent", tts: "failed", feishu: "未配置" } }] }));
    render(<MonitorCenterView />);
    expect(await screen.findByText("600519")).toBeInTheDocument();
    expect(screen.getByText(/feishu: 未配置/)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
