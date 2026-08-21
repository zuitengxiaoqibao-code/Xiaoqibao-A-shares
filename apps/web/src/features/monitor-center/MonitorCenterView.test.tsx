import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MonitorCenterView } from "./MonitorCenterView";

describe("MonitorCenterView", () => {
  it("shows persisted alerts and Chinese delivery states", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => [{ alert_id: "a1", rule_id: "risk", symbol: "600519", observed_at: "2026-08-21T02:00:00Z", delivery: { in_app: "sent", tts: "failed", feishu: "未配置" } }] });
    }));
    render(<MonitorCenterView />);
    expect(await screen.findByText("600519")).toBeInTheDocument();
    expect(screen.getByText("语音失败")).toBeInTheDocument();
    expect(screen.getByText("飞书未配置")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("saves a topic-aware rule with independent channels", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.endsWith("/rules") && init?.method === "POST") return Promise.resolve({ ok: true, json: async () => JSON.parse(String(init.body)) });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<MonitorCenterView />);
    await screen.findByText("规则配置");

    fireEvent.change(screen.getByLabelText("规则名称"), { target: { value: "风险升高" } });
    fireEvent.click(screen.getByRole("button", { name: "保存监控规则" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/rules", expect.objectContaining({ method: "POST" })));
    const request = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/rules") && init?.method === "POST");
    const body = JSON.parse(String(request?.[1]?.body));
    expect(body.topics).toEqual(["quant_strategy"]);
    expect(body.conditions).toEqual({ risk_score: { gte: 65 } });
    expect(body.channels).toEqual({ in_app: true, tts: true, feishu: false });
  });
});
