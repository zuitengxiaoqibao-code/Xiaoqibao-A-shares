import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MonitorCenterView } from "./MonitorCenterView";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const themeCss = readFileSync(resolve(process.cwd(), "src/app/theme.css"), "utf8");

describe("MonitorCenterView", () => {
  it("shows beginner templates with readable Chinese explanations", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 0, enabled: 0 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    }));

    render(<MonitorCenterView />);

    expect(await screen.findByText("常用监控规则")).toBeInTheDocument();
    expect(screen.getByText("市场风险升高提醒")).toBeInTheDocument();
    expect(screen.getByText("量化策略风险升高提醒")).toBeInTheDocument();
    expect(screen.getByText("新闻热点出现提醒")).toBeInTheDocument();
    expect(screen.getByText("尾盘候选出现提醒")).toBeInTheDocument();
    expect(screen.getByText("市场风险分达到 65 以上时提醒，优先检查风险闸门和仓位。")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("enables the market risk template with the real nested field path", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.endsWith("/rules") && init?.method === "POST") return Promise.resolve({ ok: true, json: async () => JSON.parse(String(init.body)) });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 0, enabled: 0 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MonitorCenterView />);
    const template = (await screen.findAllByText("市场风险升高提醒"))[0].closest("article");
    expect(template).not.toBeNull();
    fireEvent.click(within(template as HTMLElement).getByRole("button", { name: "启用此规则" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/rules", expect.objectContaining({ method: "POST" })));
    const request = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/rules") && init?.method === "POST");
    const body = JSON.parse(String(request?.[1]?.body));
    expect(body.id).toBe("monitor-market-risk");
    expect(body.topics).toEqual(["market_overview"]);
    expect(body.conditions).toEqual({ "regime.risk_score": { gte: 65 } });
    vi.unstubAllGlobals();
  });

  it("shows an enabled template as monitoring when no alert has fired yet", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/alerts")) return Promise.resolve({ ok: true, json: async () => [] });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [{ id: "monitor-market-risk", name: "市场风险升高提醒", topics: ["market_overview"], conditions: [{ field: "regime.risk_score", op: "gte", value: 65 }], enabled: true }] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 1, enabled: 1 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    }));

    render(<MonitorCenterView />);

    const template = (await screen.findAllByText("市场风险升高提醒"))[0].closest("article");
    expect(template).not.toBeNull();
    expect(await within(template as HTMLElement).findByText("监控中")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

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
    expect(body.conditions).toEqual({ "regime.risk_score": { gte: 65 } });
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

  it("shows readable Chinese metric names instead of technical field paths", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/alerts")) return Promise.resolve({ ok: true, json: async () => [] });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [{ id: "r1", name: "风险提醒", topics: ["quant_strategy"], conditions: [{ field: "risk_score", op: "gte", value: 65 }], channels: { in_app: true, tts: true, feishu: false } }] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 1, enabled: 1 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MonitorCenterView />);

    await screen.findByText("规则配置");
    expect(await screen.findByText(/风险分 大于等于 65/)).toBeInTheDocument();
    const metricSelectors = screen.getAllByLabelText("监控指标");
    expect(metricSelectors.length).toBeGreaterThan(0);
    expect((metricSelectors[0] as HTMLSelectElement).selectedOptions[0]?.textContent).toBe("风险分（实时快照）");
    expect(screen.queryByText("字段路径")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("pauses and resumes a saved rule through the lifecycle status endpoint", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/alerts")) return Promise.resolve({ ok: true, json: async () => [] });
      if (path.includes("/rules/r1/status") && init?.method === "PATCH") return Promise.resolve({ ok: true, json: async () => ({ id: "r1", name: "风险提醒", enabled: false }) });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [{ id: "r1", name: "风险提醒", topics: ["quant_strategy"], conditions: [{ field: "risk_score", op: "gte", value: 65 }], enabled: true }] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 1, enabled: 1 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<MonitorCenterView />);

    expect(await screen.findByText("风险提醒")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "暂停监控" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/rules/r1/status", expect.objectContaining({ method: "PATCH" })));
    expect(JSON.parse(String(fetchMock.mock.calls.find(([url, init]) => String(url).includes("/rules/r1/status") && init?.method === "PATCH")?.[1]?.body))).toEqual({ enabled: false });
    vi.unstubAllGlobals();
  });

  it("offers restore and delete actions for a paused rule", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/alerts")) return Promise.resolve({ ok: true, json: async () => [] });
      if (path.includes("/rules/r1/status") && init?.method === "PATCH") return Promise.resolve({ ok: true, json: async () => ({ id: "r1", name: "风险提醒", enabled: true }) });
      if (path.includes("/rules/r1") && init?.method === "DELETE") return Promise.resolve({ ok: true, json: async () => ({ status: "deleted", rule_id: "r1" }) });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [{ id: "r1", name: "风险提醒", topics: ["quant_strategy"], conditions: [{ field: "risk_score", op: "gte", value: 65 }], enabled: false }] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 1, enabled: 0 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<MonitorCenterView />);

    expect(await screen.findByText("已暂停")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "恢复监控" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/rules/r1/status", expect.objectContaining({ method: "PATCH" })));
    fireEvent.click(screen.getByRole("button", { name: "停止并删除" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/rules/r1", expect.objectContaining({ method: "DELETE" })));
    vi.unstubAllGlobals();
  });

  it("keeps the rule selector CSS from affecting lifecycle action buttons", () => {
    expect(themeCss).not.toContain(".monitor-rule-list button {");
    expect(themeCss).toContain(".monitor-rule-list .monitor-rule-select {");
    expect(themeCss).toContain(".monitor-rule-actions > button");
  });

  it("deletes added conditions but keeps the final condition as a protected row", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/alerts")) return Promise.resolve({ ok: true, json: async () => [] });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 0, enabled: 0 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    }));
    render(<MonitorCenterView />);

    expect(await screen.findByText("高级规则构建器")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除条件 1" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "增加条件" }));
    expect(screen.getByRole("button", { name: "删除条件 1" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "删除条件 2" })).not.toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "删除条件 2" }));
    expect(screen.getByRole("button", { name: "删除条件 1" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "删除条件 2" })).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("tests the real voice synthesis channel and reports playback completion", async () => {
    class FakeAudio {
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      play = vi.fn(async () => { this.onended?.(); });
      pause = vi.fn();
    }
    vi.stubGlobal("Audio", FakeAudio);
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:test") });
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/speech/synthesize")) return Promise.resolve(new Response(new Blob(["audio"]), { status: 200 }));
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: false, feishu_enabled: false, webhook_hint: null }) });
      if (path.includes("/alerts")) return Promise.resolve({ ok: true, json: async () => [] });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 0, enabled: 0 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MonitorCenterView />);
    fireEvent.click(await screen.findByRole("button", { name: "测试语音提醒" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/speech/synthesize", expect.objectContaining({ method: "POST" })));
    expect(await screen.findByText("语音测试已完成")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("tests the configured Feishu channel and shows the server result", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/notification-settings/test")) return Promise.resolve({ ok: true, json: async () => ({ status: "sent", message: "飞书消息已送达" }) });
      if (path.includes("notification-settings")) return Promise.resolve({ ok: true, json: async () => ({ feishu_configured: true, feishu_enabled: true, webhook_hint: "****abcd" }) });
      if (path.includes("/alerts")) return Promise.resolve({ ok: true, json: async () => [] });
      if (path.endsWith("/rules")) return Promise.resolve({ ok: true, json: async () => [] });
      return Promise.resolve({ ok: true, json: async () => ({ service: { status: "healthy" }, rules: { total: 0, enabled: 0 }, alerts: { total: 0, active: 0, critical: 0, unconfirmed: 0, recovered: 0 }, delivery: { pending: 0, failed: 0 }, topics: [], recent_alerts: [] }) });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MonitorCenterView />);
    fireEvent.click(await screen.findByRole("button", { name: "测试飞书消息" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/notification-settings/test", expect.objectContaining({ method: "POST" })));
    expect(await screen.findByText("飞书消息已送达")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
