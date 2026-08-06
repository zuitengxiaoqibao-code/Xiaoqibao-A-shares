import type { IntradayTick, KronosForecastResponse, QuantStrategyDashboard, TdxFormulaResponse } from "./types";

export async function loadQuantTicks(
  symbol: string,
  tradingDate?: string,
): Promise<IntradayTick[]> {
  const query = tradingDate
    ? `?trading_date=${encodeURIComponent(tradingDate)}`
    : "";
  const response = await fetch(
    `/api/v1/a-shares/${encodeURIComponent(symbol)}/intraday-ticks${query}`,
  );
  if (!response.ok) {
    throw new Error(`盘中 TICK 请求失败 (${response.status})`);
  }
  return response.json() as Promise<IntradayTick[]>;
}

export async function loadKronosForecast(
  symbol: string,
  asOf?: string,
  horizon = 20,
): Promise<KronosForecastResponse> {
  const params = new URLSearchParams({ symbol, horizon: String(horizon) });
  if (asOf) params.set("as_of", asOf);
  const response = await fetch(
    `/api/v1/a-shares/first-limit-up/quant-forecast?${params.toString()}`,
  );
  if (!response.ok) {
    throw new Error(`Kronos 预测请求失败 (${response.status})`);
  }
  return response.json() as Promise<KronosForecastResponse>;
}

export async function loadQuantStrategy(limit = 12): Promise<QuantStrategyDashboard> {
  const response = await fetch(
    `/api/v1/a-shares/quant-strategy?limit=${encodeURIComponent(String(limit))}`,
  );
  if (!response.ok) {
    throw new Error(`短线策略请求失败 (${response.status})`);
  }
  return response.json() as Promise<QuantStrategyDashboard>;
}

export async function loadTdxFormula(
  formulaName: string,
  stockCodes: string[],
): Promise<TdxFormulaResponse> {
  const params = new URLSearchParams({ formula_name: formulaName });
  stockCodes.forEach((code) => params.append("stock_codes", code));
  const response = await fetch(`/api/v1/tdx/local/formula?${params.toString()}`);
  if (!response.ok) throw new Error(`通达信公式请求失败 (${response.status})`);
  return response.json() as Promise<TdxFormulaResponse>;
}
