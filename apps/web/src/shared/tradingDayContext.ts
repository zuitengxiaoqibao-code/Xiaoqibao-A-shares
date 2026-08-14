export type MarketPhase = "premarket" | "intraday" | "postclose" | "overnight";

const shanghaiDateFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Shanghai",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const shanghaiTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Shanghai",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function parts(formatter: Intl.DateTimeFormat, value: Date): Record<string, string> {
  return Object.fromEntries(formatter.formatToParts(value).map((part) => [part.type, part.value]));
}

export function shanghaiDay(value: Date): string {
  const fields = parts(shanghaiDateFormatter, value);
  return `${fields.year}-${fields.month}-${fields.day}`;
}

export function shanghaiMinutes(value: Date): number {
  const fields = parts(shanghaiTimeFormatter, value);
  return Number(fields.hour ?? 0) * 60 + Number(fields.minute ?? 0);
}

export function marketPhase(value: Date): MarketPhase {
  const minutes = shanghaiMinutes(value);
  if (minutes < 9 * 60 + 25) return "premarket";
  if (minutes <= 15 * 60 + 5) return "intraday";
  if (minutes <= 18 * 60) return "postclose";
  return "overnight";
}

function dayDistance(fromDay: string, toDay: string): number {
  const from = Date.parse(`${fromDay}T00:00:00Z`);
  const to = Date.parse(`${toDay}T00:00:00Z`);
  if (!Number.isFinite(from) || !Number.isFinite(to)) return Number.NaN;
  return Math.round((to - from) / 86_400_000);
}

export function isUsableSnapshotDay(snapshotDay: string, now = new Date()): boolean {
  const today = shanghaiDay(now);
  if (snapshotDay === today) return true;
  const distance = dayDistance(snapshotDay, today);
  return marketPhase(now) === "premarket" && Number.isFinite(distance) && distance >= 1 && distance <= 3;
}

export function isSameShanghaiDay(left: string | null | undefined, right: Date): boolean {
  return Boolean(left) && left === shanghaiDay(right);
}
