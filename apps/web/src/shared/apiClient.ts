import { coalescedFetch } from "./coalescedFetch";

export type ApiCacheState = "live" | "cache" | "stale";

export type ApiResultMeta = {
  cacheState: ApiCacheState;
  observedAt: string;
  source: string | null;
  state: string | null;
  statusCode: number;
  error?: string;
};

export type ApiResult<T> = {
  data: T;
  meta: ApiResultMeta;
};

export type ApiRequestOptions = RequestInit & {
  context?: string;
  timeoutMs?: number;
};

export type ApiCachedOptions = ApiRequestOptions & {
  cacheKey: string;
  maxAgeMs?: number;
  refresh?: boolean;
};

type CacheEntry = ApiResult<unknown> & { cachedAtMs: number };

const DEFAULT_TIMEOUT_MS = 10_000;
const responseCache = new Map<string, CacheEntry>();

function containsChinese(value: string): boolean {
  return /[\u3400-\u9fff]/.test(value);
}

function contextualStatusError(context: string, status: number): string {
  if (status === 401 || status === 403) return `${context}尚未配置或没有访问权限。`;
  if (status === 404) return `${context}没有找到可用数据。`;
  if (status === 409) return `${context}当前状态冲突，请刷新后重试。`;
  if (status === 422) return `${context}请求参数不正确。`;
  if (status === 429) return `${context}请求过于频繁，请稍后重试。`;
  if (status >= 500) return `${context}服务暂不可用，请稍后重试。`;
  return `${context}请求失败（状态码 ${status}）。`;
}

async function errorDetail(response: Response): Promise<string | null> {
  if (typeof response.text !== "function" && typeof response.json === "function") {
    try {
      const payload = await response.json() as { detail?: unknown; message?: unknown };
      const detail = typeof payload.detail === "string"
        ? payload.detail
        : typeof (payload.detail as { message?: unknown } | null)?.message === "string"
          ? String((payload.detail as { message: string }).message)
          : typeof payload.message === "string"
            ? payload.message
            : null;
      return detail && containsChinese(detail) ? detail : null;
    } catch {
      return null;
    }
  }
  if (typeof response.text !== "function") return null;
  const text = await response.text().catch(() => "");
  if (!text) return null;
  try {
    const payload = JSON.parse(text) as { detail?: unknown; message?: unknown };
    const detail = typeof payload.detail === "string"
      ? payload.detail
      : typeof (payload.detail as { message?: unknown } | null)?.message === "string"
        ? String((payload.detail as { message: string }).message)
        : typeof payload.message === "string"
          ? payload.message
          : null;
    return detail && containsChinese(detail) ? detail : null;
  } catch {
    return containsChinese(text) ? text : null;
  }
}

function timedSignal(signal: AbortSignal | null | undefined, timeoutMs: number) {
  const controller = new AbortController();
  let timedOut = false;
  const abortFromCaller = () => controller.abort(signal?.reason);
  if (signal?.aborted) abortFromCaller();
  else signal?.addEventListener("abort", abortFromCaller, { once: true });
  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort(new DOMException("Timed out", "TimeoutError"));
  }, Math.max(1, timeoutMs));
  return {
    signal: controller.signal,
    didTimeout: () => timedOut,
    cleanup: () => {
      window.clearTimeout(timer);
      signal?.removeEventListener("abort", abortFromCaller);
    },
  };
}

async function parseJson<T>(response: Response): Promise<T> {
  if (typeof response.text !== "function" && typeof response.json === "function") {
    return response.json() as Promise<T>;
  }
  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

class ApiClient {
  async request<T>(input: RequestInfo | URL, options: ApiRequestOptions = {}): Promise<ApiResult<T>> {
    const {
      context = "数据",
      timeoutMs = DEFAULT_TIMEOUT_MS,
      signal: callerSignal,
      ...init
    } = options;
    const timed = timedSignal(callerSignal, timeoutMs);
    const method = (init.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
    try {
      const response = method === "GET"
        ? await coalescedFetch(input, { ...init, method, signal: timed.signal })
        : await fetch(input, { ...init, method, signal: timed.signal });
      if (!response.ok) {
        const detail = await errorDetail(response);
        throw new Error(detail ?? contextualStatusError(context, response.status));
      }
      return {
        data: await parseJson<T>(response),
        meta: {
          cacheState: "live",
          observedAt: new Date().toISOString(),
          source: response.headers?.get?.("X-Qibao-Source") ?? null,
          state: response.headers?.get?.("X-Qibao-State") ?? null,
          statusCode: response.status ?? 200,
        },
      };
    } catch (caught) {
      if (timed.didTimeout()) throw new Error(`${context}请求超时，请稍后重试。`);
      if (caught instanceof DOMException && caught.name === "AbortError") throw caught;
      if (caught instanceof Error && containsChinese(caught.message)) throw caught;
      throw new Error(`${context}网络连接失败，请检查本地服务或网络后重试。`);
    } finally {
      timed.cleanup();
    }
  }

  async getResult<T>(input: RequestInfo | URL, options: ApiRequestOptions = {}): Promise<ApiResult<T>> {
    return this.request<T>(input, { ...options, method: "GET" });
  }

  async get<T>(input: RequestInfo | URL, options: ApiRequestOptions = {}): Promise<T> {
    return (await this.getResult<T>(input, options)).data;
  }

  async getOptional<T>(input: RequestInfo | URL, options: ApiRequestOptions = {}): Promise<T | null> {
    const {
      context = "数据",
      timeoutMs = DEFAULT_TIMEOUT_MS,
      signal: callerSignal,
      ...init
    } = options;
    const timed = timedSignal(callerSignal, timeoutMs);
    try {
      const response = await coalescedFetch(input, { ...init, method: "GET", signal: timed.signal });
      if (response.status === 404) return null;
      if (!response.ok) {
        const detail = await errorDetail(response);
        throw new Error(detail ?? contextualStatusError(context, response.status));
      }
      return parseJson<T>(response);
    } catch (caught) {
      if (timed.didTimeout()) throw new Error(`${context}请求超时，请稍后重试。`);
      if (caught instanceof DOMException && caught.name === "AbortError") throw caught;
      if (caught instanceof Error && containsChinese(caught.message)) throw caught;
      throw new Error(`${context}网络连接失败，请检查本地服务或网络后重试。`);
    } finally {
      timed.cleanup();
    }
  }

  async getCached<T>(input: RequestInfo | URL, options: ApiCachedOptions): Promise<ApiResult<T>> {
    const { cacheKey, maxAgeMs = 60_000, refresh = false, ...requestOptions } = options;
    const current = responseCache.get(cacheKey) as CacheEntry | undefined;
    if (!refresh && current && Date.now() - current.cachedAtMs <= maxAgeMs) {
      return {
        data: current.data as T,
        meta: { ...current.meta, cacheState: "cache" },
      };
    }
    try {
      const result = await this.getResult<T>(input, requestOptions);
      responseCache.set(cacheKey, { ...result, cachedAtMs: Date.now() });
      return result;
    } catch (caught) {
      if (!current) throw caught;
      return {
        data: current.data as T,
        meta: {
          ...current.meta,
          cacheState: "stale",
          error: caught instanceof Error ? caught.message : "最新数据刷新失败。",
        },
      };
    }
  }

  async post<T>(input: RequestInfo | URL, body?: unknown, options: ApiRequestOptions = {}): Promise<T> {
    const headers = new Headers(options.headers);
    let requestBody = options.body;
    if (body !== undefined) {
      headers.set("Content-Type", "application/json");
      requestBody = JSON.stringify(body);
    }
    return (await this.request<T>(input, {
      ...options,
      method: "POST",
      headers,
      body: requestBody,
    })).data;
  }
}

export const apiClient = new ApiClient();

export function resetApiClientForTests(): void {
  responseCache.clear();
}
