import { Database, KeyRound, Play, Save, ShieldAlert, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { friendlyError } from "../../shared/friendlyError";
import type {
  AISettingsDeleter,
  AISettingsLoader,
  AISettingsSaver,
  AISettingsView,
  AShareUniverseSyncLoader,
  ComplianceAction,
  ComplianceLoader,
  HistoryCoverageLoader,
  HistorySyncController,
  HistorySyncLoader,
  HistorySyncStarter,
  LocalSourceSettingsLoader,
  LocalSourceSettingsWriter,
  PreparationLoader,
  SourceHealthLoader,
  SpeechSettingsLoader,
  SpeechSettingsSaver,
  SpeechSynthesizer,
  SpeechVoiceLoader,
  TdxImportController,
  TdxImportLoader,
  TdxImportScanner,
  TdxImportStarter,
} from "./types";
import type { StockPreparation } from "../stock-cockpit/types";
import { LocalSourceSettingsSection } from "./LocalSourceSettingsSection";
import { SourceHealthPanel } from "./SourceHealthPanel";
export { isAutoSyncEnabled } from "./syncPolicy";

type Props = {
  loadAI: AISettingsLoader;
  saveAI: AISettingsSaver;
  deleteAI: AISettingsDeleter;
  onAIChanged?: () => void;
  symbol?: string | null;
  prepare?: PreparationLoader;
  preparation?: StockPreparation | null;
  loadCompliance?: ComplianceLoader;
  complianceAction?: ComplianceAction;
  syncAShareUniverse?: AShareUniverseSyncLoader;
  loadSourceHealth?: SourceHealthLoader;
  loadHistorySync?: HistorySyncLoader;
  loadHistoryCoverage?: HistoryCoverageLoader;
  startHistoryBackfill?: HistorySyncStarter;
  pauseHistorySync?: HistorySyncController;
  resumeHistorySync?: HistorySyncController;
  loadSpeech?: SpeechSettingsLoader;
  loadSpeechVoices?: SpeechVoiceLoader;
  saveSpeech?: SpeechSettingsSaver;
  synthesizeSpeech?: SpeechSynthesizer;
  loadLocalSources?: LocalSourceSettingsLoader;
  detectLocalSources?: LocalSourceSettingsWriter;
  saveLocalSources?: LocalSourceSettingsWriter;
  loadTdxImport?: TdxImportLoader;
  scanTdxImport?: TdxImportScanner;
  startTdxImport?: TdxImportStarter;
  pauseTdxImport?: TdxImportController;
  resumeTdxImport?: TdxImportController;
};

export function DataSettingsView({
  loadAI,
  saveAI,
  deleteAI,
  onAIChanged,
  loadSpeech,
  loadSpeechVoices,
  saveSpeech,
  synthesizeSpeech,
  loadLocalSources,
  detectLocalSources,
  saveLocalSources,
  loadSourceHealth,
  loadTdxImport,
  scanTdxImport,
  startTdxImport,
  pauseTdxImport,
  resumeTdxImport,
}: Props) {
  const [settings, setSettings] = useState<AISettingsView | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [speechVoice, setSpeechVoice] = useState("zh-CN-XiaoxiaoNeural");
  const [speechRate, setSpeechRate] = useState(0);
  const [speechVoices, setSpeechVoices] = useState<Array<{ id: string; label: string }>>([]);
  const [speechBusy, setSpeechBusy] = useState(false);
  const [speechMessage, setSpeechMessage] = useState("");
  const [tdxImport, setTdxImport] = useState<import("./types").TdxImportJob | null>(null);
  const [tdxScan, setTdxScan] = useState<import("./types").TdxImportScan | null>(null);
  const [tdxMessage, setTdxMessage] = useState("");
  const [tdxBusy, setTdxBusy] = useState(false);
  const mounted = useRef(true);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const speechController = useRef<AbortController | null>(null);
  const previewAudio = useRef<HTMLAudioElement | null>(null);
  const previewUrl = useRef<string | null>(null);

  const applySettings = (value: AISettingsView) => {
    setSettings(value);
    setBaseUrl(value.base_url ?? "");
    setModel(value.model ?? "");
    setApiKey("");
  };

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      generation.current += 1;
      controller.current?.abort();
      speechController.current?.abort();
      previewAudio.current?.pause();
      if (previewUrl.current && typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(previewUrl.current);
    };
  }, []);

  useEffect(() => {
    const request = ++generation.current;
    controller.current?.abort();
    setBusy(false);
    const nextController = new AbortController();
    controller.current = nextController;
    loadAI(nextController.signal).then((value) => {
      if (mounted.current && request === generation.current && !nextController.signal.aborted) {
        applySettings(value);
      }
    }).catch((error) => {
      if (mounted.current && request === generation.current && !nextController.signal.aborted) {
        setMessage(friendlyError(error, "AI 设置"));
      }
    });
    return () => nextController.abort();
  }, [loadAI]);

  useEffect(() => {
    if (!loadSpeech || !loadSpeechVoices) return;
    const nextController = new AbortController();
    speechController.current = nextController;
    Promise.all([
      loadSpeech(nextController.signal),
      loadSpeechVoices(nextController.signal),
    ]).then(([value, catalog]) => {
      if (nextController.signal.aborted) return;
      setSpeechVoice(value.voice);
      setSpeechRate(value.rate);
      setSpeechVoices(catalog.voices);
    }).catch((error) => {
      if (!nextController.signal.aborted) setSpeechMessage(friendlyError(error, "语音设置"));
    });
    return () => nextController.abort();
  }, [loadSpeech, loadSpeechVoices]);

  useEffect(() => {
    if (!loadTdxImport) return;
    let active = true;
    const poll = async () => {
      try { const value = await loadTdxImport(); if (active) setTdxImport(value); } catch (error) { if (active) setTdxMessage(friendlyError(error, "通达信导入状态")); }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 1200);
    return () => { active = false; window.clearInterval(timer); };
  }, [loadTdxImport]);

  const scanLocalTdx = async () => {
    if (!scanTdxImport) return;
    setTdxBusy(true); setTdxMessage("");
    try { setTdxScan(await scanTdxImport()); } catch (error) { setTdxMessage(friendlyError(error, "本地通达信扫描")); } finally { setTdxBusy(false); }
  };
  const importLocalTdx = async () => {
    if (!startTdxImport) return;
    setTdxBusy(true); setTdxMessage("");
    try { setTdxImport(await startTdxImport()); } catch (error) { setTdxMessage(friendlyError(error, "本地通达信导入")); } finally { setTdxBusy(false); }
  };
  const controlTdxImport = async (action: "pause" | "resume") => {
    if (!tdxImport || !(action === "pause" ? pauseTdxImport : resumeTdxImport)) return;
    setTdxBusy(true); setTdxMessage("");
    try { setTdxImport(await (action === "pause" ? pauseTdxImport! : resumeTdxImport!)(tdxImport.job_id)); } catch (error) { setTdxMessage(friendlyError(error, "通达信导入任务")); } finally { setTdxBusy(false); }
  };

  const save = async () => {
    const request = ++generation.current;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    setBusy(true);
    setMessage("");
    try {
      const value = await saveAI({ base_url: baseUrl, model, api_key: apiKey }, nextController.signal);
      if (mounted.current && request === generation.current && !nextController.signal.aborted) {
        applySettings(value);
        onAIChanged?.();
      }
    } catch (error) {
      if (mounted.current && request === generation.current && !nextController.signal.aborted) {
        setMessage(friendlyError(error, "AI 设置"));
      }
    } finally {
      if (mounted.current && request === generation.current) setBusy(false);
    }
  };

  const clear = async () => {
    const request = ++generation.current;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    setBusy(true);
    setMessage("");
    try {
      const value = await deleteAI(nextController.signal);
      if (mounted.current && request === generation.current && !nextController.signal.aborted) {
        applySettings(value);
        onAIChanged?.();
      }
    } catch (error) {
      if (mounted.current && request === generation.current && !nextController.signal.aborted) {
        setMessage(friendlyError(error, "AI 设置"));
      }
    } finally {
      if (mounted.current && request === generation.current) setBusy(false);
    }
  };

  const saveVoice = async () => {
    if (!saveSpeech) return;
    speechController.current?.abort();
    const nextController = new AbortController();
    speechController.current = nextController;
    setSpeechBusy(true);
    setSpeechMessage("");
    try {
      const value = await saveSpeech(
        { voice: speechVoice, rate: speechRate },
        nextController.signal,
      );
      if (!nextController.signal.aborted) {
        setSpeechVoice(value.voice);
        setSpeechRate(value.rate);
        setSpeechMessage("播报设置已保存");
      }
    } catch (error) {
      if (!nextController.signal.aborted) setSpeechMessage(friendlyError(error, "语音设置"));
    } finally {
      if (!nextController.signal.aborted) setSpeechBusy(false);
    }
  };

  const previewVoice = async () => {
    if (!synthesizeSpeech) return;
    speechController.current?.abort();
    previewAudio.current?.pause();
    if (previewUrl.current && typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(previewUrl.current);
    const nextController = new AbortController();
    speechController.current = nextController;
    setSpeechBusy(true);
    setSpeechMessage("正在生成试听语音");
    try {
      const blob = await synthesizeSpeech({
        text: "一树-A股观测台异动语音播报已就绪。",
        voice: speechVoice,
        rate: speechRate,
      }, nextController.signal);
      if (nextController.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      previewUrl.current = url;
      previewAudio.current = audio;
      audio.onended = () => {
        setSpeechBusy(false);
        setSpeechMessage("试听完成");
        if (typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(url);
        if (previewUrl.current === url) previewUrl.current = null;
        if (previewAudio.current === audio) previewAudio.current = null;
      };
      await audio.play();
      setSpeechBusy(false);
      setSpeechMessage("正在播放试听语音");
    } catch (error) {
      if (!nextController.signal.aborted) {
        setSpeechBusy(false);
        setSpeechMessage(friendlyError(error, "语音试听"));
      }
    }
  };

  return <main className="terminal-page beginner-page data-settings-view">
    <header>
      <p className="eyebrow">数据设置</p>
      <h1>数据源、AI 与语音</h1>
      <p>管理本机行情目录、AI 接口和异动播报声音。</p>
    </header>
    {message && <div className="cockpit-error" role="alert"><ShieldAlert size={16} />{message}</div>}
    {loadLocalSources && detectLocalSources && saveLocalSources && <LocalSourceSettingsSection
      load={loadLocalSources}
      detect={detectLocalSources}
      save={saveLocalSources}
    />}
    {(loadTdxImport || scanTdxImport || startTdxImport) && <section className="settings-section tdx-import-section">
      <div className="settings-heading"><div><Database size={20} /><span><h2>通达信日线数据导入</h2><p>读取本机 vipdoc 或日线压缩包；只增量写入，不关闭通达信。</p></span></div></div>
      <div className="settings-actions"><button type="button" className="settings-action secondary" disabled={tdxBusy || !scanTdxImport} onClick={() => void scanLocalTdx()}>扫描本地数据</button><button type="button" className="settings-action" disabled={tdxBusy || !startTdxImport} onClick={() => void importLocalTdx()}>导入本地增量</button>{tdxImport?.state === "running" && <button type="button" className="settings-action danger" disabled={tdxBusy || !pauseTdxImport} onClick={() => void controlTdxImport("pause")}>暂停导入</button>}{tdxImport?.state === "paused" && <button type="button" className="settings-action" disabled={tdxBusy || !resumeTdxImport} onClick={() => void controlTdxImport("resume")}>继续导入</button>}</div>
      {tdxScan && <p className="speech-settings-message" role="status">发现日线文件 {tdxScan.day_files} 个 · 可读取 {tdxScan.readable_files} 个 · 最新日期 {tdxScan.latest_trade_date ?? "--"}</p>}
      {tdxImport && <div className="tdx-import-progress" role="status" aria-live="polite"><strong>{tdxImport.stage} · {tdxImport.percent.toFixed(2)}%</strong><progress max={100} value={tdxImport.percent} /><small>{tdxImport.processed_files}/{tdxImport.total_files} 文件 · 新增 {tdxImport.imported_rows} · 替换 {tdxImport.replaced_rows} · 跳过 {tdxImport.skipped_rows} · 失败 {tdxImport.failed_files}{tdxImport.latest_trade_date ? ` · 最新 ${tdxImport.latest_trade_date}` : ""}</small>{tdxImport.errors.slice(0, 3).map((item) => <small key={`${item.path}-${item.code}`} className="settings-error-line">{item.code}: {item.detail}</small>)}</div>}
      {tdxMessage && <p className="speech-settings-message" role="alert">{tdxMessage}</p>}
    </section>}
    {loadSourceHealth && <SourceHealthPanel load={loadSourceHealth} />}
    <section className="settings-section">
      <div className="settings-heading">
        <div><KeyRound size={20} /><span>
          <h2>OpenAI 兼容接口</h2>
          <p>{settings?.configured ? `密钥已保存 · ${settings.api_key_hint ?? "已脱敏"}` : "尚未配置 AI"}</p>
        </span></div>
      </div>
      <div className="settings-form">
        <label>API 地址<input aria-label="API 地址" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://api.example.com/v1" /></label>
        <label>模型<input aria-label="模型" value={model} onChange={(event) => setModel(event.target.value)} placeholder="模型名称" /></label>
        <label>API 密钥<input aria-label="API 密钥" type="password" autoComplete="new-password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={settings?.configured ? "留空不会显示旧密钥" : "仅保存在本机"} /></label>
      </div>
      <div className="settings-actions">
        <button type="button" className="settings-action" disabled={busy || !baseUrl || !model || !apiKey} onClick={() => void save()}>保存 AI 配置</button>
        <button type="button" className="settings-action danger" disabled={busy || !settings?.configured} onClick={() => void clear()}>清除 AI 配置</button>
      </div>
    </section>
    {loadSpeech && loadSpeechVoices && saveSpeech && synthesizeSpeech && <section className="settings-section speech-settings-section">
      <div className="settings-heading">
        <div><Volume2 size={20} /><span>
          <h2>异动语音播报</h2>
          <p>Microsoft Edge TTS 免费云端自然语音；只播报已验证的 A 股异动。</p>
        </span></div>
        <span className="speech-cloud-state">EDGE TTS / CLOUD</span>
      </div>
      <div className="speech-settings-grid">
        <label>播报音色<select aria-label="播报音色" value={speechVoice} onChange={(event) => setSpeechVoice(event.target.value)}>
          {speechVoices.map((voice) => <option key={voice.id} value={voice.id}>{voice.label}</option>)}
        </select></label>
        <label>播报语速<div className="speech-rate-control">
          <input aria-label="播报语速" type="range" min="-50" max="50" step="5" value={speechRate} onChange={(event) => setSpeechRate(Number(event.target.value))} />
          <output>{speechRate > 0 ? "+" : ""}{speechRate}%</output>
        </div></label>
      </div>
      {speechMessage && <p className="speech-settings-message" role="status">{speechMessage}</p>}
      <div className="settings-actions">
        <button type="button" className="settings-action" disabled={speechBusy || speechVoices.length === 0} onClick={() => void saveVoice()}><Save size={15} />保存播报设置</button>
        <button type="button" className="settings-action secondary" disabled={speechBusy || speechVoices.length === 0} onClick={() => void previewVoice()}><Play size={15} />试听语音</button>
      </div>
    </section>}
  </main>;
}
