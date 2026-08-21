import { beforeEach, describe, expect, it } from "vitest";

import {
  listDailySnapshots,
  readDailySnapshot,
  readDailySnapshotMetadata,
  shanghaiDay,
  writeDailySnapshot,
} from "./dailySnapshotCache";

type Snapshot = { symbol: string; value: number };

describe("dailySnapshotCache", () => {
  beforeEach(() => localStorage.clear());

  it("returns a complete snapshot cached on the same local day", () => {
    const cachedAt = new Date("2026-08-03T09:31:25+08:00");
    writeDailySnapshot("stock-cockpit", "600519", { symbol: "600519", value: 71 }, cachedAt);

    const cached = readDailySnapshot<Snapshot>(
      "stock-cockpit",
      "600519",
      new Date("2026-08-03T14:02:00+08:00"),
    );

    expect(cached).toEqual({
      value: { symbol: "600519", value: 71 },
      cachedAt: cachedAt.toISOString(),
    });
  });

  it("exposes source cutoff and completeness without changing snapshot shape", () => {
    const now = new Date("2026-08-03T09:31:25+08:00");
    writeDailySnapshot("evidence", "600519", { symbol: "600519", value: 71 }, now, {
      sourceCutoff: "2026-08-03T09:30:00+08:00",
      completeness: "complete",
    });
    expect(readDailySnapshotMetadata("evidence", "600519", now)).toEqual({
      sourceCutoff: "2026-08-03T09:30:00+08:00",
      completeness: "complete",
      day: "2026-08-03",
    });
  });

  it("ignores and removes a snapshot from a previous local day", () => {
    writeDailySnapshot(
      "company-research",
      "600519",
      { symbol: "600519", value: 65 },
      new Date("2026-08-02T15:01:00+08:00"),
    );

    expect(readDailySnapshot(
      "company-research",
      "600519",
      new Date("2026-08-03T09:15:00+08:00"),
    )).toBeNull();
    expect(localStorage.length).toBe(0);
  });

  it("uses the Shanghai trading date at the midnight boundary", () => {
    expect(shanghaiDay(new Date("2026-08-03T15:59:59.000Z"))).toBe("2026-08-03");
    expect(shanghaiDay(new Date("2026-08-03T16:00:00.000Z"))).toBe("2026-08-04");
    writeDailySnapshot(
      "stock-cockpit",
      "600519",
      { symbol: "600519", value: 71 },
      new Date("2026-08-03T15:59:59.000Z"),
    );

    expect(readDailySnapshot(
      "stock-cockpit",
      "600519",
      new Date("2026-08-03T16:00:00.000Z"),
    )).toBeNull();
  });

  it("removes malformed or mismatched stock snapshots", () => {
    localStorage.setItem(
      "qibao.daily-snapshot.v1.stock-cockpit.2026-08-03.600519",
      "not-json",
    );
    expect(readDailySnapshot(
      "stock-cockpit",
      "600519",
      new Date("2026-08-03T10:00:00+08:00"),
    )).toBeNull();

    writeDailySnapshot(
      "stock-cockpit",
      "600519",
      { symbol: "000001", value: 10 },
      new Date("2026-08-03T10:01:00+08:00"),
    );
    expect(readDailySnapshot(
      "stock-cockpit",
      "600519",
      new Date("2026-08-03T10:02:00+08:00"),
    )).toBeNull();
  });

  it("keeps only the twelve newest snapshots in one feature scope", () => {
    for (let index = 0; index < 13; index += 1) {
      const symbol = String(600000 + index);
      writeDailySnapshot(
        "company-research",
        symbol,
        { symbol, value: index },
        new Date(Date.parse("2026-08-03T01:00:00.000Z") + index * 1000),
      );
    }

    expect(localStorage.length).toBe(12);
    expect(readDailySnapshot(
      "company-research",
      "600000",
      new Date("2026-08-03T12:00:00+08:00"),
    )).toBeNull();
    expect(readDailySnapshot(
      "company-research",
      "600012",
      new Date("2026-08-03T12:00:00+08:00"),
    )).not.toBeNull();
  });

  it("lists today's valid snapshots newest first", () => {
    writeDailySnapshot(
      "company-research",
      "600519",
      { symbol: "600519", value: 65 },
      new Date("2026-08-03T09:31:00+08:00"),
    );
    writeDailySnapshot(
      "company-research",
      "000001",
      { symbol: "000001", value: 72 },
      new Date("2026-08-03T10:15:00+08:00"),
    );

    expect(listDailySnapshots<Snapshot>(
      "company-research",
      new Date("2026-08-03T14:00:00+08:00"),
    )).toEqual([
      {
        symbol: "000001",
        cachedAt: new Date("2026-08-03T10:15:00+08:00").toISOString(),
        value: { symbol: "000001", value: 72 },
      },
      {
        symbol: "600519",
        cachedAt: new Date("2026-08-03T09:31:00+08:00").toISOString(),
        value: { symbol: "600519", value: 65 },
      },
    ]);
  });

  it("cleans previous-day, malformed, and mismatched entries while listing", () => {
    writeDailySnapshot(
      "stock-cockpit",
      "600519",
      { symbol: "600519", value: 65 },
      new Date("2026-08-02T15:00:00+08:00"),
    );
    localStorage.setItem(
      "qibao.daily-snapshot.v1.stock-cockpit.2026-08-03.000001",
      "not-json",
    );
    writeDailySnapshot(
      "stock-cockpit",
      "600000",
      { symbol: "000001", value: 40 },
      new Date("2026-08-03T10:00:00+08:00"),
    );

    expect(listDailySnapshots(
      "stock-cockpit",
      new Date("2026-08-03T11:00:00+08:00"),
    )).toEqual([]);
    expect(localStorage.length).toBe(0);
  });

  it("does not let a partial refresh replace today's complete snapshot", () => {
    const now = new Date("2026-08-03T10:00:00+08:00");
    writeDailySnapshot("company-research", "600519", { symbol: "600519", value: 80 }, now);
    writeDailySnapshot(
      "company-research",
      "600519",
      { symbol: "600519", value: 20 },
      new Date("2026-08-03T10:01:00+08:00"),
      { completeness: "partial" },
    );

    expect(readDailySnapshot<Snapshot>("company-research", "600519", now)?.value.value).toBe(80);
  });

  it("reads and lists a partial snapshot only when the caller explicitly validates it", () => {
    const now = new Date("2026-08-03T10:00:00+08:00");
    writeDailySnapshot(
      "company-research",
      "600519",
      { symbol: "600519", value: 65 },
      now,
      { completeness: "partial" },
    );

    expect(readDailySnapshot<Snapshot>("company-research", "600519", now)).toBeNull();

    writeDailySnapshot(
      "company-research",
      "600519",
      { symbol: "600519", value: 65 },
      now,
      { completeness: "partial" },
    );
    const options = {
      allowPartial: true,
      validate: (value: unknown): value is Snapshot => (
        typeof value === "object" && value !== null && (value as Snapshot).value > 0
      ),
    };
    expect(readDailySnapshot<Snapshot>("company-research", "600519", now, options)?.value.value).toBe(65);
    expect(listDailySnapshots<Snapshot>("company-research", now, options)).toHaveLength(1);
    expect(readDailySnapshotMetadata("company-research", "600519", now, options)?.completeness).toBe("partial");
  });

  it("removes a partial snapshot that fails the caller's structural validation", () => {
    const now = new Date("2026-08-03T10:00:00+08:00");
    writeDailySnapshot(
      "company-research",
      "600519",
      { symbol: "600519", value: 0 },
      now,
      { completeness: "partial" },
    );

    expect(readDailySnapshot<Snapshot>("company-research", "600519", now, {
      allowPartial: true,
      validate: (value): value is Snapshot => (value as Snapshot).value > 0,
    })).toBeNull();
    expect(localStorage.length).toBe(0);
  });

  it("stores version and source cutoff while preserving the public cache hit shape", () => {
    const now = new Date("2026-08-03T10:00:00+08:00");
    writeDailySnapshot(
      "company-research",
      "600519",
      { symbol: "600519", value: 80 },
      now,
      { sourceCutoff: "2026-08-03T09:59:00+08:00" },
    );

    const raw = JSON.parse(localStorage.getItem(
      "qibao.daily-snapshot.v1.company-research.2026-08-03.600519",
    ) ?? "null");
    expect(raw.schemaVersion).toBe(2);
    expect(raw.completeness).toBe("complete");
    expect(raw.sourceCutoff).toBe("2026-08-03T09:59:00+08:00");
    expect(readDailySnapshot<Snapshot>("company-research", "600519", now)).toEqual({
      value: { symbol: "600519", value: 80 },
      cachedAt: now.toISOString(),
    });
  });
});
