import { beforeEach, describe, expect, it } from "vitest";

import {
  listDailySnapshots,
  readDailySnapshot,
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
});
