import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AnomalyVoiceAnnouncer } from "./AnomalyVoiceAnnouncer";
import type { OverviewAnomaly } from "../market-overview/types";


const anomaly = (id: string, minute: string): OverviewAnomaly => ({
  anomaly_id: id,
  occurred_at: `2026-07-29T10:${minute}:00+08:00`,
  label: `异动 ${id}`,
  headline: `已验证事件 ${id}`,
  direction: "positive",
  themes: ["算力"],
  symbols: ["603629"],
  credibility: "verified",
  strength: "high",
});


class FakeAudio {
  onended: (() => void) | null = null;
  onerror: (() => void) | null = null;
  play = vi.fn().mockResolvedValue(undefined);
  pause = vi.fn();
}


describe("AnomalyVoiceAnnouncer", () => {
  const created: FakeAudio[] = [];

  beforeEach(() => {
    created.length = 0;
    vi.stubGlobal("Audio", vi.fn(() => {
      const audio = new FakeAudio();
      created.push(audio);
      return audio;
    }));
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => `blob:speech-${created.length}`),
      revokeObjectURL: vi.fn(),
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("announces only the latest verified anomaly when activated", async () => {
    const synthesize = vi.fn().mockResolvedValue(new Blob(["audio"], { type: "audio/mpeg" }));

    render(<AnomalyVoiceAnnouncer
      anomalies={[anomaly("a1", "01"), anomaly("a2", "02")]}
      synthesize={synthesize}
    />);

    await waitFor(() => expect(synthesize).toHaveBeenCalledTimes(1));
    expect(synthesize.mock.calls[0][0].text).toContain("异动 a2");
    expect(screen.getByRole("region", { name: "异动语音播报" })).toHaveTextContent("正在播报");
    expect(created[0].play).toHaveBeenCalledTimes(1);
  });

  it("queues new anomalies oldest first and never repeats an anomaly id", async () => {
    const synthesize = vi.fn().mockResolvedValue(new Blob(["audio"], { type: "audio/mpeg" }));
    const view = render(<AnomalyVoiceAnnouncer
      anomalies={[anomaly("a1", "01")]}
      synthesize={synthesize}
    />);
    await waitFor(() => expect(synthesize).toHaveBeenCalledTimes(1));

    await act(async () => created[0].onended?.());
    view.rerender(<AnomalyVoiceAnnouncer
      anomalies={[anomaly("a3", "03"), anomaly("a2", "02"), anomaly("a1", "01")]}
      synthesize={synthesize}
    />);
    await waitFor(() => expect(synthesize).toHaveBeenCalledTimes(2));
    expect(synthesize.mock.calls[1][0].text).toContain("异动 a2");

    await act(async () => created[1].onended?.());
    await waitFor(() => expect(synthesize).toHaveBeenCalledTimes(3));
    expect(synthesize.mock.calls[2][0].text).toContain("异动 a3");

    await act(async () => created[2].onended?.());
    view.rerender(<AnomalyVoiceAnnouncer
      anomalies={[anomaly("a3", "03"), anomaly("a2", "02"), anomaly("a1", "01")]}
      synthesize={synthesize}
    />);
    expect(synthesize).toHaveBeenCalledTimes(3);
  });

  it("stops playback, clears the queue and revokes audio on deactivation", async () => {
    const synthesize = vi.fn().mockResolvedValue(new Blob(["audio"], { type: "audio/mpeg" }));
    const view = render(<AnomalyVoiceAnnouncer
      anomalies={[anomaly("a1", "01")]}
      synthesize={synthesize}
    />);
    await waitFor(() => expect(created).toHaveLength(1));

    view.unmount();

    expect(created[0].pause).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(1);
  });

  it("does not speak pending or uncertain anomalies", async () => {
    const synthesize = vi.fn().mockResolvedValue(new Blob(["audio"], { type: "audio/mpeg" }));
    render(<AnomalyVoiceAnnouncer
      anomalies={[{ ...anomaly("a1", "01"), credibility: "pending", direction: "uncertain" }]}
      synthesize={synthesize}
    />);

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(synthesize).not.toHaveBeenCalled();
  });

  it("keeps market information visible when cloud synthesis fails", async () => {
    const synthesize = vi.fn().mockRejectedValue(new Error("cloud offline"));

    render(<AnomalyVoiceAnnouncer
      anomalies={[anomaly("a1", "01")]}
      synthesize={synthesize}
    />);

    expect(await screen.findByRole("alert")).toHaveTextContent("语音合成暂不可用");
    expect(screen.getByText("已验证事件 a1")).toBeInTheDocument();
  });
});
