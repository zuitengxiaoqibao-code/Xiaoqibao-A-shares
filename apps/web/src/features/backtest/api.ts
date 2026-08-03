import type { BacktestRequest, BacktestResult } from "./types";

const defaultRequest: BacktestRequest = { strategy: "sma_cross", fast_window: 5, slow_window: 20, initial_cash: 1_000_000 };

function isAbortSignal(value: BacktestRequest | AbortSignal | undefined): value is AbortSignal {
  return Boolean(value && "aborted" in value && "addEventListener" in value);
}

export async function runBacktest(symbol: string, requestOrSignal?: BacktestRequest | AbortSignal, explicitSignal?: AbortSignal): Promise<BacktestResult> {
  const request = isAbortSignal(requestOrSignal) || !requestOrSignal ? defaultRequest : requestOrSignal;
  const signal = isAbortSignal(requestOrSignal) ? requestOrSignal : explicitSignal;
  const response = await fetch(`/api/v1/a-shares/${symbol}/backtests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `回测请求失败 (${response.status})`);
  }
  return response.json() as Promise<BacktestResult>;
}
