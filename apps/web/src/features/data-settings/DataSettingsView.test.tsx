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

    await screen.findByText("尚未配置 AI 接口");
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
        { vendor: "tdx" as const, install_path: "D:\\new_tdx_mock", data_path: "D:\\new_tdx_mock\\vipdoc", origin: "manual" as const, status: "ready" as const, sh_daily_count: 2210, sz_daily_count: 2890, latest_modified_at: "2026-07-30T01:30:00Z", professional_data_status: "detected_only" as const, professional_data_files: ["base.dbf", "shs.tnf"] },
        { vendor: "tdx" as const, install_path: "D:\\tdx_fixture", data_path: "D:\\tdx_fixture\\vipdoc", origin: "registry" as const, status: "ready" as const, sh_daily_count: 100, sz_daily_count: 100, latest_modified_at: "2026-07-30T01:30:00Z", selection_eligible: false, selection_note: "自动发现已排除疑似测试/示例数据目录；如需使用请手工添加此目录" },
        { vendor: "ths" as const, install_path: "C:\\THS", data_path: null, origin: "manual" as const, status: "detected_only" as const, sh_daily_count: 0, sz_daily_count: 0, latest_modified_at: null },
      ],
      active_tdx_vipdoc: "D:\\new_tdx_mock\\vipdoc",
         tdx_rpc: {
           status: "disabled" as const,
           reachable: false,
           endpoint: null,
           observed_at: "2026-07-30T02:00:00Z",
           client: { status: "not_running" as const, executable_path: null, detail: "未检测到通达信客户端进程" },
            capabilities: [
           { key: "snapshot", label: "实时行情", method: "get_market_snapshot", status: "disabled" as const, detail: "本地通达信桥接未启用" },
         ],
          direct_python: { status: "detected_only" as const, detail: "已发现官方模块；等待通达信进程返回可验证专业字段", module_path: "D:\\new_tdx64\\PYPlugins\\user\\tqcenter.py" },
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
    expect(screen.getByText("专业缓存已发现 2 项，等待只读桥接读取")).toBeInTheDocument();
    expect(screen.getByText("已发现，暂未读取本地行情")).toBeInTheDocument();
    expect(screen.getByText(/自动发现已排除疑似测试/)).toBeInTheDocument();
    expect(screen.getByLabelText("自动发现本机行情软件")).toBeChecked();
    expect(screen.getByLabelText("启用本地实时桥接")).not.toBeChecked();
    expect(screen.getByText("只读能力探测")).toBeInTheDocument();
    expect(screen.getByText("官方 TdxQuant Python 回退")).toBeInTheDocument();
    expect(screen.getByText(/等待通达信进程返回可验证专业字段/)).toBeInTheDocument();
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

  it("rechecks an enabled unavailable TDX bridge while the settings page is visible", async () => {
    vi.useFakeTimers();
    try {
      const unavailable = {
        settings_state: "ready" as const,
        settings: {
          auto_discovery: true,
          tdx_install_paths: [],
          ths_install_paths: [],
          tdx_rpc_enabled: true,
          tdx_rpc_url: "http://127.0.0.1:17709/",
        },
        scanned_at: "2026-07-30T02:00:00Z",
        terminals: [],
        active_tdx_vipdoc: null,
         tdx_rpc: {
           status: "unavailable" as const,
           reachable: false,
           endpoint: "http://127.0.0.1:17709/",
           observed_at: "2026-07-30T02:00:00Z",
           client: { status: "not_running" as const, executable_path: null, detail: "未检测到通达信客户端进程" },
           capabilities: [],
           direct_python: { status: "unavailable" as const, detail: "未发现官方 TdxQuant Python 模块和配套 DLL", module_path: null },
         },
        restart_required: false,
      };
      const detect = vi.fn().mockResolvedValue({
        ...unavailable,
        tdx_rpc: { ...unavailable.tdx_rpc, status: "ready", reachable: true },
      });
      render(<DataSettingsView
        loadAI={() => Promise.resolve(emptySettings)}
        saveAI={vi.fn()}
        deleteAI={vi.fn()}
        loadLocalSources={() => Promise.resolve(unavailable)}
        detectLocalSources={detect}
        saveLocalSources={vi.fn()}
      />);
      await act(async () => { await Promise.resolve(); await Promise.resolve(); });
      expect(detect).not.toHaveBeenCalled();
      await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
      expect(detect).toHaveBeenCalledWith(unavailable.settings, expect.any(AbortSignal));
    } finally {
      vi.useRealTimers();
    }
  });

  it("separates the running TDX client from the unavailable JSON-RPC bridge", async () => {
    const localSources = {
      settings_state: "ready" as const,
      settings: { auto_discovery: true, tdx_install_paths: [], ths_install_paths: [], tdx_rpc_enabled: true, tdx_rpc_url: "http://127.0.0.1:17709/" },
      scanned_at: "2026-07-30T02:00:00Z",
      terminals: [],
      active_tdx_vipdoc: null,
      tdx_rpc: {
        status: "unavailable" as const,
        reachable: false,
        endpoint: "http://127.0.0.1:17709/",
        observed_at: "2026-07-30T02:00:00Z",
        client: { status: "running" as const, executable_path: "D:\\\\new_tdx64\\\\TdxW.exe", detail: "检测到通达信客户端进程；这不代表 17709 JSON-RPC 桥已经监听" },
        capabilities: [],
        direct_python: { status: "detected_only" as const, detail: "已发现官方模块；等待通达信进程返回可验证专业字段", module_path: "D:\\\\new_tdx64\\\\PYPlugins\\\\user\\\\tqcenter.py" },
      },
      restart_required: false,
    };

    render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)}
      saveAI={vi.fn()}
      deleteAI={vi.fn()}
      loadLocalSources={() => Promise.resolve(localSources)}
      detectLocalSources={vi.fn()}
      saveLocalSources={vi.fn()}
    />);

    expect(await screen.findByText("通达信客户端")).toBeInTheDocument();
    expect(screen.getByText("已运行")).toBeInTheDocument();
    expect(screen.getByText("17709 未监听")).toBeInTheDocument();
    expect(screen.getByText(/这不代表 17709 JSON-RPC 桥已经监听/)).toBeInTheDocument();
  });

  it("uses the configured bridge port in the runtime status", async () => {
    const localSources = {
      settings_state: "ready" as const,
      settings: { auto_discovery: true, tdx_install_paths: [], ths_install_paths: [], tdx_rpc_enabled: true, tdx_rpc_url: "http://127.0.0.1:19001/" },
      scanned_at: "2026-07-30T02:00:00Z",
      terminals: [],
      active_tdx_vipdoc: null,
      tdx_rpc: {
        status: "unavailable" as const,
        reachable: false,
        endpoint: "http://127.0.0.1:19001/",
        observed_at: "2026-07-30T02:00:00Z",
        client: { status: "running" as const, executable_path: "D:\\\\new_tdx64\\\\TdxW.exe", detail: "检测到通达信客户端进程；这不代表 19001 JSON-RPC 桥已经监听" },
        capabilities: [],
        direct_python: { status: "detected_only" as const, detail: "已发现官方模块；等待通达信进程返回可验证专业字段", module_path: "D:\\\\new_tdx64\\\\PYPlugins\\\\user\\\\tqcenter.py" },
      },
      restart_required: false,
    };

    render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)}
      saveAI={vi.fn()}
      deleteAI={vi.fn()}
      loadLocalSources={() => Promise.resolve(localSources)}
      detectLocalSources={vi.fn()}
      saveLocalSources={vi.fn()}
    />);

    expect(await screen.findByText("19001 未监听")).toBeInTheDocument();
  });

  it("shows masked AI state without rendering the secret", async () => {
    render(<DataSettingsView
      loadAI={() => Promise.resolve({ configured: true, base_url: "http://localhost:11434/v1", model: "local-model", api_key_hint: "****alue" })}
      saveAI={vi.fn()}
      deleteAI={vi.fn()}
    />);

    expect(await screen.findByText("AI 接口已配置 · 密钥已保存 ****alue")).toBeInTheDocument();
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

    await screen.findByText("尚未配置 AI 接口");
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

    await screen.findByText("AI 接口已配置 · 密钥已保存 ****ocal");
    fireEvent.click(screen.getByRole("button", { name: "清除 AI 配置" }));
    expect(await screen.findByText("AI 接口已配置 · 密钥已保存 ****env1")).toBeInTheDocument();
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

    await screen.findByText("尚未配置 AI 接口");
    fireEvent.change(screen.getByLabelText("API 地址"), { target: { value: "https://ai.example/v1" } });
    fireEvent.change(screen.getByLabelText("模型"), { target: { value: "model" } });
    fireEvent.change(screen.getByLabelText("API 密钥"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "保存 AI 配置" }));
    view.unmount();
    await act(async () => finish({ configured: true, base_url: "https://ai.example/v1", model: "model", api_key_hint: "****cret" }));
    expect(refresh).not.toHaveBeenCalled();
  });

  it("keeps history repair controls out of data settings after migration to operations", async () => {
    const scanLocal = vi.fn().mockResolvedValue({
      scanned_paths: [], day_files: 5545, archive_files: 0, readable_files: 5545,
      latest_trade_date: "2026-07-17", errors: [],
    });
    const startOfficial = vi.fn().mockResolvedValue({
      job_id: "supplement-1", state: "pending", stage: "queued", percent: 0,
      source_url: "https://data.tdx.com.cn/vipdoc/hsjday.zip", downloaded_bytes: 0,
      day_file_count: 0, supported_file_count: 0, imported_rows: 0,
      replaced_rows: 0, skipped_rows: 0, failed_files: 0,
      created_at: "2026-08-19T02:00:00Z", updated_at: "2026-08-19T02:00:00Z",
    });
    const retryFailed = vi.fn().mockResolvedValue({
      job_id: "history-old", mode: "backfill", target_date: "2026-07-29",
      state: "pending", pause_requested: false, total_count: 5981,
      ready_count: 5256, failed_count: 0, skipped_count: 0, pending_count: 725,
      tdx_ready_count: 0, baidu_ready_count: 5256,
      created_at: "2026-07-29T02:00:00Z", updated_at: "2026-08-19T02:00:00Z",
    });
    const restartCurrent = vi.fn().mockResolvedValue({ ...await retryFailed(), target_date: "2026-08-19" });

    render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)} saveAI={vi.fn()} deleteAI={vi.fn()}
      loadHistoryCoverage={() => Promise.resolve({
        target_date: "2026-08-19", universe_count: 5584, backfill_complete_count: 5118,
        eligible_count: 5118, target_date_count: 1, target_date_coverage_percent: 0.02,
        dominant_trade_date: "2026-07-29", dominant_date_count: 5118,
        dominant_date_coverage_percent: 91.65, coverage_percent: 91.65,
        fragmented_latest_count: 1, missing_history_count: 466, quality: "partial", blockers: [],
      })}
      loadHistorySync={() => Promise.resolve({
        job_id: "history-old", mode: "backfill", target_date: "2026-07-29",
        state: "paused", pause_requested: true, total_count: 5981,
        ready_count: 5256, failed_count: 391, skipped_count: 0, pending_count: 334,
        tdx_ready_count: 0, baidu_ready_count: 5256,
        created_at: "2026-07-29T02:00:00Z", updated_at: "2026-08-17T02:00:00Z",
      })}
      loadOfficialTdxInfo={() => Promise.resolve({ size_label: "520.67MB", modified_at: "2026-08-18T15:58:48+08:00" })}
      loadHistorySupplement={() => Promise.resolve(null)}
      loadTdxImport={() => Promise.resolve({
        job_id: "tdx-old", state: "paused", stage: "restart_paused", paths: [],
        total_files: 5544, processed_files: 62, imported_rows: 0, replaced_rows: 0,
        skipped_rows: 29091, failed_files: 0, latest_trade_date: "2026-07-17",
        current_file: null,
        percent: 1.12, errors: [], created_at: "2026-08-19T01:00:00Z",
        updated_at: "2026-08-19T02:00:00Z", finished_at: "2026-08-19T02:00:00Z",
      })}
      startOfficialTdxSupplement={startOfficial}
      retryFailedHistory={retryFailed}
      restartCurrentHistory={restartCurrent}
      scanTdxImport={scanLocal}
    />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "数据源、AI 与语音" })).toBeInTheDocument());
    expect(screen.queryByRole("heading", { name: "历史数据补齐中心" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "通达信日线数据导入" })).not.toBeInTheDocument();
    expect(scanLocal).not.toHaveBeenCalled();
    expect(startOfficial).not.toHaveBeenCalled();
    expect(restartCurrent).not.toHaveBeenCalled();
  });

  it("does not poll repair state from data settings after migration", async () => {
    vi.useFakeTimers();
    const loadOfficial = vi.fn().mockResolvedValue({
      size_label: "520.67MB", modified_at: "2026-08-18T15:58:48+08:00",
    });
    const loadCoverage = vi.fn().mockResolvedValue({
      target_date: "2026-08-18", universe_count: 5585, backfill_complete_count: 5119,
      eligible_count: 5119, target_date_count: 1, target_date_coverage_percent: 0.02,
      dominant_trade_date: "2026-07-29", dominant_date_count: 5119,
      dominant_date_coverage_percent: 91.66, coverage_percent: 97.44,
      fragmented_latest_count: 466, missing_history_count: 143, quality: "partial", blockers: [],
    });
    const loadSupplement = vi.fn().mockResolvedValue({
      job_id: "supplement-running", state: "running", stage: "downloading", percent: 30,
      source_url: "https://data.tdx.com.cn/vipdoc/hsjday.zip", downloaded_bytes: 100,
      total_bytes: 1000, day_file_count: 0, supported_file_count: 0,
      imported_rows: 0, replaced_rows: 0, skipped_rows: 0, failed_files: 0,
      created_at: "2026-08-19T02:00:00Z", updated_at: "2026-08-19T02:00:01Z",
    });

    render(<DataSettingsView
      loadAI={() => Promise.resolve(emptySettings)} saveAI={vi.fn()} deleteAI={vi.fn()}
      loadOfficialTdxInfo={loadOfficial}
      loadHistoryCoverage={loadCoverage}
      loadHistorySupplement={loadSupplement}
    />);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(loadOfficial).not.toHaveBeenCalled();
    expect(loadCoverage).not.toHaveBeenCalled();

    await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
    expect(loadSupplement).not.toHaveBeenCalled();
    expect(loadOfficial).not.toHaveBeenCalled();
    expect(loadCoverage).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
