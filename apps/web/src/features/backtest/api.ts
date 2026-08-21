import type { BacktestRequest, BacktestResult } from "./types";
import { apiClient } from "../../shared/apiClient";

const defaultRequest: BacktestRequest = { strategy: "sma_cross", fast_window: 5, slow_window: 20, initial_cash: 1_000_000 };

function isAbortSignal(value: BacktestRequest | AbortSignal | undefined): value is AbortSignal {
  return Boolean(value && "aborted" in value && "addEventListener" in value);
}

export async function runBacktest(symbol: string, requestOrSignal?: BacktestRequest | AbortSignal, explicitSignal?: AbortSignal): Promise<BacktestResult> {
  const request = isAbortSignal(requestOrSignal) || !requestOrSignal ? defaultRequest : requestOrSignal;
  const signal = isAbortSignal(requestOrSignal) ? requestOrSignal : explicitSignal;
  return apiClient.post<BacktestResult>(
    `/api/v1/a-shares/${symbol}/backtests`,
    request,
    { context: "回测", signal },
  );
}
