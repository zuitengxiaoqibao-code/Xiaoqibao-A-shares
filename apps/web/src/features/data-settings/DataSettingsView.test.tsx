import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";

import { DataSettingsView, isAutoSyncEnabled } from "./DataSettingsView";
import type { AISettingsView } from "./types";

const emptySettings = {
  configured: false,
  base_url: null,
  model: null,
  api_key_hint: null,
} as const;

describe("DataSettingsView", () => {
  it("only exposes the OpenAI-compatible connection form", async () => {
    window.localStorage.setItem("qibao.autoSync", "false");
    const loadCompliance = vi.fn().mockResolvedValue({
      policy_state: "pending",
      sources: [{ source: "eastmoney", permission_state: "pending" }],
      features: [],
    });

    render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)}
      saveAI={vi.fn()}
      deleteAI={vi.fn()}
      loadCompliance={loadCompliance}
      complianceAction={vi.fn()}
    />);

    expect(await screen.findByRole("heading", { name: "OpenAI 兼容接口" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("terminal-page", "data-settings-view");
    expect(screen.getByLabelText("API 地址")).toBeInTheDocument();
    expect(screen.getByLabelText("模型")).toBeInTheDocument();
    expect(screen.getByLabelText("API 密钥")).toBeInTheDocument();
    expect(screen.queryByText("来源授权")).not.toBeInTheDocument();
    expect(screen.queryByText("公开数据同步")).not.toBeInTheDocument();
    expect(screen.queryByText("来源健康")).not.toBeInTheDocument();
    expect(screen.queryByText("全市场日线覆盖")).not.toBeInTheDocument();
    expect(loadCompliance).not.toHaveBeenCalled();
    expect(isAutoSyncEnabled()).toBe(true);
  });

  it("loads, saves and previews Edge TTS voice settings", async () => {
    const saveSpeech = vi.fn().mockResolvedValue({ voice: "zh-CN-YunxiNeural", rate: 15 });
    const synthesizeSpeech = vi.fn().mockResolvedValue(
      new Blob(["audio"], { type: "audio/mpeg" }),
    );
    const play = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("Audio", vi.fn(() => ({ play, pause: vi.fn(), onended: null, onerror: null })));
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:preview"), revokeObjectURL: vi.fn() });

    const view = render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)}
      saveAI={vi.fn()}
      deleteAI={vi.fn()}
      loadSpeech={() => Promise.resolve({ voice: "zh-CN-XiaoxiaoNeural", rate: 0 })}
      loadSpeechVoices={() => Promise.resolve({ voices: [
        { id: "zh-CN-XiaoxiaoNeural", label: "晓晓 - 温暖自然女声", gender: "female" },
        { id: "zh-CN-YunxiNeural", label: "云希 - 沉稳自然男声", gender: "male" },
      ] })}
      saveSpeech={saveSpeech}
      synthesizeSpeech={synthesizeSpeech}
    />);

    expect(await screen.findByRole("heading", { name: "异动语音播报" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("播报音色"), { target: { value: "zh-CN-YunxiNeural" } });
    fireEvent.change(screen.getByLabelText("播报语速"), { target: { value: "15" } });
    fireEvent.click(screen.getByRole("button", { name: "试听语音" }));
    await waitFor(() => expect(synthesizeSpeech).toHaveBeenCalledWith(
      { text: expect.stringContaining("异动语音播报"), voice: "zh-CN-YunxiNeural", rate: 15 },
      expect.any(AbortSignal),
    ));
    await waitFor(() => expect(play).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "保存播报设置" }));
    await waitFor(() => expect(saveSpeech).toHaveBeenCalledWith(
      { voice: "zh-CN-YunxiNeural", rate: 15 },
      expect.any(AbortSignal),
    ));
    view.unmount();
    vi.unstubAllGlobals();
  });

  it("loads settings and saves normally under React StrictMode", async () => {
    const saveAI = vi.fn().mockResolvedValue({
      configured: true,
      base_url: "https://strict.example/v1",
      model: "strict-model",
      api_key_hint: "****init",
    });
    const refresh = vi.fn();
    render(<StrictMode><DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)}
      saveAI={saveAI}
      deleteAI={vi.fn()}
      onAIChanged={refresh}
    /></StrictMode>);

    await screen.findByText("尚未配置 AI");
    fireEvent.change(screen.getByLabelText("API 地址"), { target: { value: "https://strict.example/v1" } });
    fireEvent.change(screen.getByLabelText("模型"), { target: { value: "strict-model" } });
    fireEvent.change(screen.getByLabelText("API 密钥"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "保存 AI 配置" }));
    await waitFor(() => expect(saveAI).toHaveBeenCalledTimes(1));
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("manages validated local terminal paths without enabling the RPC bridge", async () => {
    const localSources = {
      settings_state: "ready" as const,
      settings: {
        auto_discovery: true,
        tdx_install_paths: ["D:\\new_tdx_mock"],
        ths_install_paths: ["C:\\THS"],
        tdx_rpc_enabled: false,
        tdx_rpc_url: null,
      },
      scanned_at: "2026-07-30T02:00:00Z",
      terminals: [
        { vendor: "tdx" as const, install_path: "D:\\new_tdx_mock", data_path: "D:\\new_tdx_mock\\vipdoc", origin: "manual" as const, status: "ready" as const, sh_daily_count: 2210, sz_daily_count: 2890, latest_modified_at: "2026-07-30T01:30:00Z" },
        { vendor: "ths" as const, install_path: "C:\\THS", data_path: null, origin: "manual" as const, status: "detected_only" as const, sh_daily_count: 0, sz_daily_count: 0, latest_modified_at: null },
      ],
      active_tdx_vipdoc: "D:\\new_tdx_mock\\vipdoc",
      tdx_rpc: {
        status: "disabled" as const,
        reachable: false,
        endpoint: null,
        observed_at: "2026-07-30T02:00:00Z",
        capabilities: [
          { key: "snapshot", label: "实时行情", method: "get_market_snapshot", status: "disabled" as const, detail: "本地通达信桥接未启用" },
        ],
      },
      restart_required: false,
    };
    const detectLocalSources = vi.fn().mockResolvedValue(localSources);
    const saveLocalSources = vi.fn().mockResolvedValue({ ...localSources, restart_required: true });

    render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)}
      saveAI={vi.fn()}
      deleteAI={vi.fn()}
      loadLocalSources={() => Promise.resolve(localSources)}
      detectLocalSources={detectLocalSources}
      saveLocalSources={saveLocalSources}
    />);

    expect(await screen.findByRole("heading", { name: "本地行情软件" })).toBeInTheDocument();
    expect(screen.getByText("D:\\new_tdx_mock\\vipdoc")).toBeInTheDocument();
    expect(screen.getByText(/沪市 2210.*深市 2890/)).toBeInTheDocument();
    expect(screen.getByText("已发现，暂未读取本地行情")).toBeInTheDocument();
    expect(screen.getByLabelText("自动发现本机行情软件")).toBeChecked();
    expect(screen.getByLabelText("启用本地实时桥接")).not.toBeChecked();
    expect(screen.getByText("只读能力探测")).toBeInTheDocument();
    expect(screen.getByText("实时行情")).toBeInTheDocument();
    expect(screen.getAllByText("桥接未启用")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "重新检测" }));
    await waitFor(() => expect(detectLocalSources).toHaveBeenCalledWith(
      localSources.settings,
      expect.any(AbortSignal),
    ));
    fireEvent.click(screen.getByRole("button", { name: "验证并保存" }));
    await waitFor(() => expect(saveLocalSources).toHaveBeenCalled());
    expect(await screen.findByText("设置已保存，重新打开软件后生效")).toBeInTheDocument();
  });

  it("shows masked AI state without rendering the secret", async () => {
    render(<DataSettingsView
      loadAI={() => Promise.resolve({ configured: true, base_url: "http://localhost:11434/v1", model: "local-model", api_key_hint: "****alue" })}
      saveAI={vi.fn()}
      deleteAI={vi.fn()}
    />);

    expect(await screen.findByText("密钥已保存 · ****alue")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("secret-value")).not.toBeInTheDocument();
    expect(screen.getByLabelText("API 密钥")).toHaveValue("");
  });

  it("saves and clears explicitly, then requests a cockpit refresh", async () => {
    const saveAI = vi.fn().mockResolvedValue({ configured: true, base_url: "https://ai.example/v1", model: "model", api_key_hint: "****1234" });
    const deleteAI = vi.fn().mockResolvedValue(emptySettings);
    const refresh = vi.fn();
    render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)}
      saveAI={saveAI}
      deleteAI={deleteAI}
      onAIChanged={refresh}
    />);

    await screen.findByText("尚未配置 AI");
    fireEvent.change(screen.getByLabelText("API 地址"), { target: { value: "https://ai.example/v1" } });
    fireEvent.change(screen.getByLabelText("模型"), { target: { value: "model" } });
    fireEvent.change(screen.getByLabelText("API 密钥"), { target: { value: "secret-value" } });
    fireEvent.click(screen.getByRole("button", { name: "保存 AI 配置" }));
    await waitFor(() => expect(saveAI).toHaveBeenCalledWith(
      { base_url: "https://ai.example/v1", model: "model", api_key: "secret-value" },
      expect.any(AbortSignal),
    ));
    fireEvent.click(screen.getByRole("button", { name: "清除 AI 配置" }));
    await waitFor(() => expect(deleteAI).toHaveBeenCalledTimes(1));
    expect(refresh).toHaveBeenCalledTimes(2);
  });

  it("uses the effective state returned after deleting local settings", async () => {
    const deleteAI = vi.fn().mockResolvedValue({ configured: true, base_url: "https://env.example/v1", model: "env-model", api_key_hint: "****env1" });
    render(<DataSettingsView
      loadAI={() => Promise.resolve({ configured: true, base_url: "https://local.example/v1", model: "local", api_key_hint: "****ocal" })}
      saveAI={vi.fn()}
      deleteAI={deleteAI}
    />);

    await screen.findByText("密钥已保存 · ****ocal");
    fireEvent.click(screen.getByRole("button", { name: "清除 AI 配置" }));
    expect(await screen.findByText("密钥已保存 · ****env1")).toBeInTheDocument();
    expect(screen.getByLabelText("API 地址")).toHaveValue("https://env.example/v1");
  });

  it("does not refresh the cockpit when a save finishes after unmount", async () => {
    let finish!: (value: AISettingsView) => void;
    const saveAI = vi.fn(() => new Promise<AISettingsView>((resolve) => { finish = resolve; }));
    const refresh = vi.fn();
    const view = render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)}
      saveAI={saveAI}
      deleteAI={vi.fn()}
      onAIChanged={refresh}
    />);

    await screen.findByText("尚未配置 AI");
    fireEvent.change(screen.getByLabelText("API 地址"), { target: { value: "https://ai.example/v1" } });
    fireEvent.change(screen.getByLabelText("模型"), { target: { value: "model" } });
    fireEvent.change(screen.getByLabelText("API 密钥"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "保存 AI 配置" }));
    view.unmount();
    await act(async () => finish({ configured: true, base_url: "https://ai.example/v1", model: "model", api_key_hint: "****cret" }));
    expect(refresh).not.toHaveBeenCalled();
  });
});
