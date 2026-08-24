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

  it("shows summary KPIs, topic health and filters lifecycle alerts", async () => {
    const summary = {
      generated_at: "2026-08-24T02:00:00Z",
      service: { status: "healthy", last_heartbeat_at: "2026-08-24T02:00:00Z", latency_ms: 120 },
      rules: { total: 2, enabled: 2 },
      alerts: { total: 2, active: 2, critical: 1, unconfirmed: 2, recovered: 0 },
      delivery: { pending: 1, failed: 0 },
      topics: [{ topic: "quant_strategy", status: "critical", alert_count: 2, active_count: 2, last_alert_at: "2026-08-24T02:00:00Z" }],
      recent_alerts: [
        { alert_id: "a-critical", rule_id: "risk", topic: "quant_strategy", symbol: "600519", observed_at: "2026-08-24T02:00:00Z", severity: "critical", state: "active", confirmed: false, delivery: { in_app: "sent" } },
        { alert_id: "a-warning", rule_id: "heat", topic: "quant_strategy", symbol: "000001", observed_at: "2026-08-24T01:59:00Z", severity: "warning", state: "active", confirmed: false, delivery: { in_app: "pending" } },
      ],
    };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/summary")) return Promise.resolve({ ok: true, json: async () => summary });
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => [] });
    }));

    render(<MonitorCenterView />);

    expect(await screen.findByText("严重告警")).toBeInTheDocument();
    expect(screen.getByText("主题健康")).toBeInTheDocument();
    expect(screen.getAllByText("量化策略").length).toBeGreaterThan(0);
    expect(screen.getByText("600519")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("严重级别筛选"), { target: { value: "critical" } });
    expect(screen.getByText("600519")).toBeInTheDocument();
    expect(screen.queryByText("000001")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("confirms an alert without losing the dashboard data", async () => {
    const summary = {
      generated_at: "2026-08-24T02:00:00Z",
      service: { status: "healthy", last_heartbeat_at: null, latency_ms: null },
      rules: { total: 1, enabled: 1 },
      alerts: { total: 1, active: 1, critical: 0, unconfirmed: 1, recovered: 0 },
      delivery: { pending: 0, failed: 0 },
      topics: [],
      recent_alerts: [{ alert_id: "a1", rule_id: "risk", symbol: "600519", observed_at: "2026-08-24T02:00:00Z", severity: "warning", state: "active", confirmed: false, delivery: { in_app: "sent" } }],
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.includes("/summary")) return Promise.resolve({ ok: true, json: async () => summary });
      if (path.includes("/confirm")) return Promise.resolve({ ok: true, json: async () => ({ ...summary.recent_alerts[0], confirmed: true }) });
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MonitorCenterView />);
    expect(await screen.findByText("600519")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认告警" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/alerts/a1/confirm", expect.objectContaining({ method: "POST" })));
    vi.unstubAllGlobals();
  });

  it("keeps the last valid summary visible when a later refresh fails", async () => {
    const summary = {
      generated_at: "2026-08-24T02:00:00Z",
      service: { status: "healthy", last_heartbeat_at: null, latency_ms: null },
      rules: { total: 1, enabled: 1 },
      alerts: { total: 1, active: 1, critical: 0, unconfirmed: 1, recovered: 0 },
      delivery: { pending: 0, failed: 0 },
      topics: [],
      recent_alerts: [{ alert_id: "a1", rule_id: "risk", symbol: "600519", observed_at: "2026-08-24T02:00:00Z", severity: "warning", state: "active", confirmed: false, delivery: { in_app: "sent" } }],
    };
    let summaryCalls = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/summary")) {
        summaryCalls += 1;
        return summaryCalls === 1
          ? Promise.resolve({ ok: true, json: async () => summary })
          : Promise.reject(new Error("监控中心网络连接失败"));
      }
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MonitorCenterView />);
    expect(await screen.findByText("600519")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "刷新监控状态" }));
    await waitFor(() => expect(screen.getByText("最新监控摘要刷新失败，当前保留上次有效数据。")).toBeInTheDocument());
    expect(screen.getByText("600519")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("builds a multi-condition realtime rule with confirmation and freshness gates", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/rules") && init?.method === "POST") return Promise.resolve({ ok: true, json: async () => JSON.parse(String(init.body)) });
      if (path.includes("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      if (path.includes("/summary")) return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 0, enabled: 0 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
      return Promise.resolve({ ok: true, json: async () => [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MonitorCenterView />);
    await screen.findByText("高级规则构建器");
    fireEvent.change(screen.getByLabelText("条件逻辑"), { target: { value: "any" } });
    fireEvent.click(screen.getByRole("button", { name: "增加条件" }));
    fireEvent.change(screen.getByLabelText("连续确认次数"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("数据新鲜度秒数"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "保存高级规则" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/rules", expect.objectContaining({ method: "POST" })));
    const request = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/rules") && init?.method === "POST");
    const body = JSON.parse(String(request?.[1]?.body));
    expect(body.logic).toBe("any");
    expect(body.conditions).toHaveLength(2);
    expect(body.confirm_count).toBe(3);
    expect(body.freshness_seconds).toBe(5);
    vi.unstubAllGlobals();
  });
});
