import type { OverviewMinutePoint } from "./types";
import { shanghaiDay, shanghaiMinutes } from "../../shared/tradingDayContext";

export type MarketSessionStage =
  | "waiting_open"
  | "call_auction"
  | "awaiting_first_tick"
  | "live"
  | "postclose"
  | "closed";

export type MarketSessionDisplay = {
  stage: MarketSessionStage;
  title: string;
  detail: string;
  secondsToOpen: number;
};

type MarketPhase = "premarket" | "intraday" | "postclose" | "closed" | undefined;

export function isTimestampOnShanghaiDay(value: string, day: string): boolean {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) && shanghaiDay(new Date(parsed)) === day;
}

export function filterPointsForShanghaiDay(points: OverviewMinutePoint[], day: string): OverviewMinutePoint[] {
  return points.filter((point) => isTimestampOnShanghaiDay(point.observed_at, day));
}

export function formatOpeningCountdown(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remaining = safeSeconds % 60;
  return [hours, minutes, remaining].map((value) => String(value).padStart(2, "0")).join(":");
}

export function marketSessionDisplay({ now, phase, points }: {
  now: Date;
  phase: MarketPhase;
  points: OverviewMinutePoint[];
}): MarketSessionDisplay {
  if (phase === "closed") {
    return { stage: "closed", title: "今日休市", detail: "休市期间不展示历史分时作为今日行情", secondsToOpen: 0 };
  }

  const today = shanghaiDay(now);
  const currentPoints = filterPointsForShanghaiDay(points, today);
  if (phase === "postclose") {
    return { stage: "postclose", title: "今日交易已结束", detail: "保留今日最终分时与已核验事件", secondsToOpen: 0 };
  }

  const openingAt = Date.parse(`${today}T09:30:00+08:00`);
  const secondsToOpen = Math.max(0, Math.ceil((openingAt - now.getTime()) / 1000));
  const minutes = shanghaiMinutes(now);
  if (minutes < 9 * 60 + 15) {
    return { stage: "waiting_open", title: "等待开盘", detail: "09:30 开盘后自动接收今日行情", secondsToOpen };
  }
  if (minutes < 9 * 60 + 30) {
    return { stage: "call_auction", title: "集合竞价进行中", detail: "竞价结束后自动切换今日分时", secondsToOpen };
  }
  if (currentPoints.length === 0) {
    return { stage: "awaiting_first_tick", title: "正在接收今日首笔行情", detail: "已连接实时链路，等待数据源返回当日分钟点", secondsToOpen: 0 };
  }
  return { stage: "live", title: "今日分时实时更新", detail: "仅展示今日真实分钟点与已核验事件", secondsToOpen: 0 };
}
