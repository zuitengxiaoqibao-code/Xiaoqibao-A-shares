import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MonitorTtsAnnouncer } from "./MonitorTtsAnnouncer";

describe("MonitorTtsAnnouncer", () => {
  beforeEach(() => {
    vi.stubGlobal("Audio", vi.fn(() => ({
      play: vi.fn().mockResolvedValue(undefined),
      pause: vi.fn(),
      onended: null,
      onerror: null,
    })));
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:alert"), revokeObjectURL: vi.fn() });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("claims a fresh alert, synthesizes it and records playback", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [{ alert_id: "a1", symbol: "600519", rule_id: "r1", observed_at: "2026-08-21T02:00:00Z", snapshot: { change_pct: 5 } }] })
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);
    const synthesize = vi.fn().mockResolvedValue(new Blob(["audio"], { type: "audio/mpeg" }));

    render(<MonitorTtsAnnouncer synthesize={synthesize} pollMs={60_000} />);
    await waitFor(() => expect(synthesize).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/monitor-center/alerts/a1/delivery", expect.objectContaining({ method: "POST" }));
    expect(fetchMock).toHaveBeenLastCalledWith("/api/v1/monitor-center/alerts/a1/delivery", expect.objectContaining({ method: "POST" }));
  });

  it("records a Chinese failure reason when synthesis fails", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [{ alert_id: "a1", symbol: "600519", rule_id: "r1", observed_at: "2026-08-21T02:00:00Z" }] })
      .mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    render(<MonitorTtsAnnouncer synthesize={vi.fn().mockRejectedValue(new Error("语音云连接失败"))} />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const failedBody = JSON.parse(String(fetchMock.mock.calls[2][1]?.body));
    expect(failedBody).toEqual({ channel: "tts", status: "failed", reason: "语音云连接失败" });
  });
});
