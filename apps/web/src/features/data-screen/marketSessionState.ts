export type DataScreenSessionState = "live" | "waiting_open" | "postclose" | "closed";

function shanghaiClock(now: Date): { minutes: number; weekday: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Shanghai",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    weekday: "short",
  }).formatToParts(now);
  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? 0);
  const weekdayName = parts.find((part) => part.type === "weekday")?.value ?? "";
  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  return { minutes: hour * 60 + minute, weekday: weekdays.indexOf(weekdayName) };
}

/** Distinguishes the overnight retained snapshot from the 08:00 pre-open wait. */
export function dataScreenSessionState(phase: string, now = new Date()): DataScreenSessionState {
  const { minutes, weekday } = shanghaiClock(now);
  if (phase === "intraday") return "live";
  if (phase === "postclose") return "postclose";
  if (phase === "premarket" && weekday >= 1 && weekday <= 5 && minutes >= 8 * 60 && minutes < 9 * 60 + 30) {
    return "waiting_open";
  }
  return "closed";
}

export function dataScreenSessionLabel(state: DataScreenSessionState): string {
  return state === "live" ? "盘中实时" : state === "waiting_open" ? "等待开盘中" : state === "postclose" ? "盘后数据" : "最近收盘";
}
