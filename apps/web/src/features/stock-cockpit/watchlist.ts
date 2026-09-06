import { isAShareSymbol } from "../instrument-selection/SelectedInstrumentProvider";
import { apiClient } from "../../shared/apiClient";
import { updateTaskActivity } from "../../shared/taskActivity";

export const A_SHARE_WATCHLIST_KEY = "qibao.a_share.watchlist.v1";
export const A_SHARE_WATCHLIST_CHANGED_EVENT = "qibao:a-share-watchlist-change";

function cleanWatchlist(value: unknown): string[] {
  return Array.isArray(value)
    ? [...new Set(value.filter((item): item is string => (
      typeof item === "string" && isAShareSymbol(item)
    )))]
    : [];
}

type WatchlistResponse = { symbols: string[]; updated_at: string | null };

function publishLocal(symbols: string[]): string[] {
  const cleaned = cleanWatchlist(symbols);
  localStorage.setItem(A_SHARE_WATCHLIST_KEY, JSON.stringify(cleaned));
  window.dispatchEvent(new CustomEvent(A_SHARE_WATCHLIST_CHANGED_EVENT));
  return cleaned;
}

export function readAShareWatchlist(): string[] {
  try {
    const cleaned = cleanWatchlist(
      JSON.parse(localStorage.getItem(A_SHARE_WATCHLIST_KEY) ?? "[]"),
    );
    localStorage.setItem(A_SHARE_WATCHLIST_KEY, JSON.stringify(cleaned));
    return cleaned;
  } catch {
    localStorage.setItem(A_SHARE_WATCHLIST_KEY, "[]");
    return [];
  }
}

export function writeAShareWatchlist(symbols: string[]): string[] {
  const cleaned = publishLocal(symbols);
  updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage: "正在保存", state: "running", detail: `${cleaned.length} 只`, percent: 35 });
  void apiClient.request<WatchlistResponse>("/api/v1/a-shares/watchlist", {
    method: "PUT",
    context: "自选股保存",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols: cleaned }),
  }).then(({ data }) => {
    const saved = publishLocal(data.symbols);
    updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage: "已保存", state: "succeeded", detail: `${saved.length} 只`, percent: 100 });
  }).catch((reason) => {
    updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage: "保存失败", state: "failed", detail: "当前保留本地快照", error: reason instanceof Error ? reason.message : "自选股保存失败" });
  });
  return cleaned;
}

export async function hydrateAShareWatchlist(): Promise<string[]> {
  const fallback = readAShareWatchlist();
  updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage: "正在加载", state: "running", detail: fallback.length ? `先展示本地 ${fallback.length} 只` : "读取已保存列表", percent: 20 });
  try {
    const response = await apiClient.get<WatchlistResponse>("/api/v1/a-shares/watchlist", { context: "自选股加载" });
    const symbols = publishLocal(response.symbols);
    updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage: "已加载", state: "succeeded", detail: `${symbols.length} 只`, percent: 100 });
    return symbols;
  } catch (reason) {
    updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage: "加载失败", state: "failed", detail: fallback.length ? `保留本地 ${fallback.length} 只` : "没有可用缓存", error: reason instanceof Error ? reason.message : "自选股加载失败" });
    return fallback;
  }
}
