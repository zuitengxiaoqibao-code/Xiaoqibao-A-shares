import type { CorrectionInput, EventImpactReport, NewsIntelligenceBundle } from "./types";
import { apiClient } from "../../shared/apiClient";

async function read<T>(url: string, init?: RequestInit): Promise<T> {
  return (await apiClient.request<T>(url, { ...init, context: "新闻热点" })).data;
}

export async function loadNewsIntelligence(): Promise<NewsIntelligenceBundle> {
  const [events, interpretations, unifiedEvents, quality, corrections, briefings] = await Promise.all([
    read<NewsIntelligenceBundle["events"]>("/api/v1/news/events"),
    read<NewsIntelligenceBundle["interpretations"]>("/api/v1/news/interpretations"),
    read<NonNullable<NewsIntelligenceBundle["unifiedEvents"]>>("/api/v1/news/unified-events"),
    read<NewsIntelligenceBundle["quality"]>("/api/v1/news/quality"),
    read<NewsIntelligenceBundle["corrections"]>("/api/v1/news/corrections"),
    read<NewsIntelligenceBundle["briefings"]>("/api/v1/briefings"),
  ]);
  return { events, interpretations, unifiedEvents, quality, corrections, briefings };
}

export const syncNews = (symbol?: string | null) => read<Record<string, number>>(
  symbol ? `/api/v1/news/sync/${encodeURIComponent(symbol)}` : "/api/v1/news/sync",
  { method: "POST" },
);
export const syncHotspots = () => read<Record<string, number>>(
  "/api/v1/news/hotspots/sync",
  { method: "POST" },
);
export const createNewsCorrection = (input: CorrectionInput) => read("/api/v1/news/corrections", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
});

export const loadEventImpact = (eventId: string) => read<EventImpactReport>(
  `/api/v1/news/events/${encodeURIComponent(eventId)}/impact`,
);
