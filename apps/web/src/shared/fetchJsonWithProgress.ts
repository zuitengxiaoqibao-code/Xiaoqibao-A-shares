export type LoadStage = "connecting" | "receiving" | "parsing" | "complete";

export type LoadProgress = {
  percent: number;
  stage: LoadStage;
  detail: string;
  receivedBytes?: number;
  totalBytes?: number;
};

export type LoadProgressCallback = (progress: LoadProgress) => void;

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
): Promise<string> {
  if (!response.body) {
    const text = await response.text();
    onProgress?.({
      percent: 92,
      stage: "receiving",
      detail: `已接收 ${new TextEncoder().encode(text).byteLength} 字节`,
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
      ? 5 + Math.min(87, Math.floor((received / total) * 87))
      : Math.min(88, 12 + Math.floor(Math.log2(received + 1) * 5));
    onProgress?.({
      percent,
      stage: "receiving",
      detail: total ? `已接收 ${received} / ${total} 字节` : `已接收 ${received} 字节`,
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
  onProgress?.({ percent: 1, stage: "connecting", detail: "正在连接本地数据服务" });
  const response = await fetch(input, init);
  onProgress?.({ percent: 5, stage: "receiving", detail: "连接成功，正在接收数据" });
  const text = await readBody(response, onProgress);
  if (!response.ok) throw new Error(apiMessage(text, fallbackError(response.status)));
  onProgress?.({ percent: 96, stage: "parsing", detail: "数据接收完成，正在校验并解析" });
  const value = JSON.parse(text) as T;
  onProgress?.({ percent: 100, stage: "complete", detail: "最新数据已载入" });
  return value;
}
