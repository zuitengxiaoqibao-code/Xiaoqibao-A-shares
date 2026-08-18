import type { MarketIntervalReviewLoader, MarketIntervalReviewSnapshot, MarketOverviewLoader, MarketOverviewResponse } from "./types";
import { coalescedFetch } from "../../shared/coalescedFetch";
import { requestLedger } from "../../shared/performance/requestLedger";

export type MarketOverviewStreamListener = (snapshot: MarketOverviewResponse) => void;
export type MarketOverviewStreamState = "connected" | "closed" | "error";

export function parseMarketOverviewSseBuffer(buffer: string): { events: MarketOverviewResponse[]; rest: string } {
  const events: MarketOverviewResponse[] = [];
  const frames = buffer.split("\n\n");
  const rest = frames.pop() ?? "";
  for (const frame of frames) {
    const data = frame.split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) continue;
    try {
      const parsed = JSON.parse(data) as { kind?: string; payload?: MarketOverviewResponse };
      if (parsed.kind === "market_overview" && parsed.payload) events.push(parsed.payload);
    } catch {
      // A partial or keep-alive frame is ignored; the next complete frame is retained.
    }
  }
  return { events, rest };
}

export async function consumeMarketOverviewStream(
  onSnapshot: MarketOverviewStreamListener,
  signal: AbortSignal,
  onState?: (state: MarketOverviewStreamState) => void,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/api/v1/a-shares/market-overview/stream", {
      signal,
      headers: { Accept: "text/event-stream" },
    });
  } catch (error) {
    if (!(error instanceof DOMException && error.name === "AbortError")) onState?.("error");
    throw error;
  }
  if (!response.ok || !response.body) {
    onState?.("error");
    throw new Error(`实时推送不可用 (${response.status})`);
  }
  onState?.("connected");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (!signal.aborted) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      const parsed = parseMarketOverviewSseBuffer(buffer);
      buffer = parsed.rest;
      parsed.events.forEach(onSnapshot);
    }
  } finally {
    reader.releaseLock();
    if (!signal.aborted) onState?.("closed");
  }
}

export const loadMarketOverview: MarketOverviewLoader = (signal) => requestLedger.run("overview:latest", async () => {
  let response: Response;
  try {
    response = await coalescedFetch("/api/v1/a-shares/market-overview", { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("信息总览数据暂不可用，请检查本地 API 后重试。");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      body.detail?.message
      ?? body.detail?.code
      ?? body.detail
      ?? `信息总览请求失败 (${response.status})`,
    );
  }
  return response.json() as Promise<MarketOverviewResponse>;
}, { domain: "overview" });

export const loadMarketIntervalReview: MarketIntervalReviewLoader = async (startDate, endDate, signal) => {
  let response: Response;
  try {
    response = await coalescedFetch(`/api/v1/a-shares/market-overview/interval?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`, { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("区间统计数据暂不可用，请检查本地日线数据源。");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? body.detail?.code ?? body.detail ?? `区间统计请求失败 (${response.status})`);
  }
  return response.json() as Promise<MarketIntervalReviewSnapshot>;
};
