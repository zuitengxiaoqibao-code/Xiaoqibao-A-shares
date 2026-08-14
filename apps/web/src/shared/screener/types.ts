import type { ReactNode } from "react";

export type ScreenerSort = "symbol" | "name" | "value_desc";
export type ScreenerFilters = {
  query: string;
  excludeST: boolean;
  excludeSuspended: boolean;
  sort: ScreenerSort;
};

export type ScreenerMember = {
  symbol: string;
  name: string;
  reason: string;
  value?: ReactNode;
  tradingStatus?: "active" | "suspended" | "delisted" | "unknown";
};
