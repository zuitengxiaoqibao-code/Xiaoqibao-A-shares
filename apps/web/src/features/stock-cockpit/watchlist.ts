import { isAShareSymbol } from "../instrument-selection/SelectedInstrumentProvider";

export const A_SHARE_WATCHLIST_KEY = "qibao.a_share.watchlist.v1";
export const A_SHARE_WATCHLIST_CHANGED_EVENT = "qibao:a-share-watchlist-change";

function cleanWatchlist(value: unknown): string[] {
  return Array.isArray(value)
    ? [...new Set(value.filter((item): item is string => (
      typeof item === "string" && isAShareSymbol(item)
    )))]
    : [];
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
  const cleaned = cleanWatchlist(symbols);
  localStorage.setItem(A_SHARE_WATCHLIST_KEY, JSON.stringify(cleaned));
  window.dispatchEvent(new CustomEvent(A_SHARE_WATCHLIST_CHANGED_EVENT));
  return cleaned;
}
