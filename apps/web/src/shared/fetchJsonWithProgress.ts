export type LoadStage = "connecting" | "receiving" | "parsing" | "complete";
export type LoadProgressMode = "estimated" | "measured" | "verified";

export type LoadProgress = {
  percent: number;
  stage: LoadStage;
  detail: string;
  mode?: LoadProgressMode;
  elapsedMs?: number;
  receivedBytes?: number;
  totalBytes?: number;
};

export type LoadProgressCallback = (progress: LoadProgress) => void;

// Ten seconds is a performance target only. Keep a long final guard for a
// genuinely dead connection without truncating slow but valid data sources.
export const DEFAULT_FETCH_TIMEOUT_MS = 120_000;

function apiMessage(text: string, fallback: string): string {
  try {
    const body = JSON.parse(text) as { detail?: string | { message?: string } };
    if (typeof body.detail === "string") return body.detail;
    if (body.detail?.message) return body.detail.message;
  } catch {
    // Non-JSON error bodies use the caller-provided status message.
  }
  return fallback;
}

async function readBody(
  response: Response,
  onProgress?: LoadProgressCallback,
  startedAt = performance.now(),
): Promise<string> {
  if (!response.body) {
    const text = await response.text();
    onProgress?.({
      percent: 92,
      stage: "receiving",
      detail: `已接收 ${new TextEncoder().encode(text).byteLength} 字节`,
      mode: "measured",
      elapsedMs: performance.now() - startedAt,
    });
    return text;
  }

  const totalHeader = Number(response.headers.get("Content-Length"));
  const total = Number.isFinite(totalHeader) && totalHeader > 0 ? totalHeader : null;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let received = 0;
  let text = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    received += value.byteLength;
    text += decoder.decode(value, { stream: true });
    const percent = total
      ? 46 + Math.min(46, Math.floor((received / total) * 46))
      : Math.min(88, 46 + Math.floor(Math.log2(received + 1) * 3));
    onProgress?.({
      percent,
      stage: "receiving",
      detail: total ? `已接收 ${received} / ${total} 字节` : `已接收 ${received} 字节`,
      mode: "measured",
      elapsedMs: performance.now() - startedAt,
      receivedBytes: received,
      totalBytes: total ?? undefined,
    });
  }
  text += decoder.decode();
  return text;
}

export async function fetchJsonWithProgress<T>(
  input: RequestInfo | URL,
  init?: RequestInit,
  onProgress?: LoadProgressCallback,
  fallbackError: (status: number) => string = (status) => `请求失败 (${status})`,
): Promise<T> {
  const startedAt = performance.now();
  let lastPercent = 0;
  const emit: LoadProgressCallback = (progress) => {
    const percent = Math.max(lastPercent, Math.min(100, Math.round(progress.percent)));
    lastPercent = percent;
    onProgress?.({ ...progress, percent });
  };
  emit({
    percent: 1,
    stage: "connecting",
    mode: "estimated",
    elapsedMs: 0,
    detail: "正在连接本地数据服务 · 阶段估算",
  });
  const estimateTimer = window.setInterval(() => {
    const elapsedMs = performance.now() - startedAt;
    const estimated = Math.min(45, 1 + Math.floor(44 * (1 - Math.exp(-elapsedMs / 6_000))));
    emit({
      percent: estimated,
      stage: "connecting",
      mode: "estimated",
      elapsedMs,
      detail: `本地服务正在准备数据 · 已等待 ${(elapsedMs / 1_000).toFixed(1)} 秒 · 阶段估算`,
    });
  }, 250);
  const callerSignal = init?.signal;
  const requestController = new AbortController();
  let timedOut = false;
  const abortFromCaller = () => requestController.abort(callerSignal?.reason);
  if (callerSignal?.aborted) abortFromCaller();
  else callerSignal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeout = window.setTimeout(() => {
    timedOut = true;
    requestController.abort(new DOMException("Timed out", "TimeoutError"));
  }, DEFAULT_FETCH_TIMEOUT_MS);
  let response: Response;
  try {
    response = await coalescedFetch(input, { ...init, signal: requestController.signal });
  } catch (error) {
    if (timedOut) throw new Error("请求超时，请稍后重试。");
    throw error;
  } finally {
    window.clearTimeout(timeout);
    callerSignal?.removeEventListener("abort", abortFromCaller);
    window.clearInterval(estimateTimer);
  }
  emit({
    percent: 46,
    stage: "receiving",
    mode: "measured",
    elapsedMs: performance.now() - startedAt,
    detail: "连接成功，正在接收真实响应字节",
  });
  const text = await readBody(response, emit, startedAt);
  if (!response.ok) throw new Error(apiMessage(text, fallbackError(response.status)));
  emit({
    percent: 96,
    stage: "parsing",
    mode: "verified",
    elapsedMs: performance.now() - startedAt,
    detail: "数据接收完成，正在校验并解析",
  });
  const value = JSON.parse(text) as T;
  emit({
    percent: 100,
    stage: "complete",
    mode: "verified",
    elapsedMs: performance.now() - startedAt,
    detail: "最新数据已载入",
  });
  return value;
}
import { coalescedFetch } from "./coalescedFetch";
