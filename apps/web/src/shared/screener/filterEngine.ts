import type { ScreenerFilters, ScreenerMember } from "./types";

function numericValue(value: ScreenerMember["value"]): number {
  if (typeof value === "number") return value;
  if (typeof value !== "string" || !value.trim()) return Number.NEGATIVE_INFINITY;
  const parsed = Number(value.replace(/[^\d.+-]/g, ""));
  return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;
}

export function filterMembers(rows: ScreenerMember[], filters: ScreenerFilters): ScreenerMember[] {
  const query = filters.query.trim().toLocaleLowerCase("zh-CN");
  return rows.filter((row) => !query || [row.symbol, row.name, row.reason].some((value) => value.toLocaleLowerCase("zh-CN").includes(query)))
    .filter((row) => !filters.excludeST || !/^\*?ST/i.test(row.name))
    .filter((row) => !filters.excludeSuspended || row.tradingStatus !== "suspended")
    .sort((left, right) => filters.sort === "value_desc"
      ? numericValue(right.value) - numericValue(left.value)
      : filters.sort === "name" ? left.name.localeCompare(right.name, "zh-CN") : left.symbol.localeCompare(right.symbol));
}
