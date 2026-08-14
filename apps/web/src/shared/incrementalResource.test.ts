import { describe, expect, it } from "vitest";

import { mergeEntitySnapshot, resolveIncrementalResponse } from "./incrementalResource";

type Row = { id: string; value: number };
type Snapshot = { tradeDate: string; observedAt: string; rows: Row[] };

describe("incremental resource", () => {
  it("ignores an older response that arrives after a newer snapshot", () => {
    const current: Snapshot = { tradeDate: "2026-08-13", observedAt: "2026-08-13T10:31:00+08:00", rows: [{ id: "a", value: 2 }] };
    const incoming: Snapshot = { tradeDate: "2026-08-13", observedAt: "2026-08-13T10:30:00+08:00", rows: [{ id: "a", value: 1 }] };
    expect(resolveIncrementalResponse(current, incoming, { tradeDate: (value) => value.tradeDate, observedAt: (value) => value.observedAt })).toBe(current);
  });

  it("deduplicates entities and lets new values update existing rows", () => {
    expect(mergeEntitySnapshot(
      [{ id: "a", value: 1 }, { id: "b", value: 2 }],
      [{ id: "b", value: 3 }, { id: "c", value: 4 }],
      (row) => row.id,
    )).toEqual([{ id: "a", value: 1 }, { id: "b", value: 3 }, { id: "c", value: 4 }]);
  });

  it("switches cleanly when the trade date changes", () => {
    const current: Snapshot = { tradeDate: "2026-08-12", observedAt: "2026-08-12T15:00:00+08:00", rows: [{ id: "a", value: 1 }] };
    const incoming: Snapshot = { tradeDate: "2026-08-13", observedAt: "2026-08-13T09:30:00+08:00", rows: [{ id: "b", value: 2 }] };
    expect(resolveIncrementalResponse(current, incoming, { tradeDate: (value) => value.tradeDate, observedAt: (value) => value.observedAt })).toBe(incoming);
  });

  it("does not let a late response from an older trade date replace the current snapshot", () => {
    const current: Snapshot = { tradeDate: "2026-08-13", observedAt: "2026-08-13T09:30:00+08:00", rows: [{ id: "a", value: 2 }] };
    const incoming: Snapshot = { tradeDate: "2026-08-12", observedAt: "2026-08-13T10:30:00+08:00", rows: [{ id: "a", value: 1 }] };
    expect(resolveIncrementalResponse(current, incoming, { tradeDate: (value) => value.tradeDate, observedAt: (value) => value.observedAt })).toBe(current);
  });

  it("keeps a nonempty current snapshot when a transient empty response arrives", () => {
    const current: Snapshot = { tradeDate: "2026-08-13", observedAt: "2026-08-13T10:30:00+08:00", rows: [{ id: "a", value: 1 }] };
    const incoming: Snapshot = { tradeDate: "2026-08-13", observedAt: "2026-08-13T10:31:00+08:00", rows: [] };
    expect(resolveIncrementalResponse(current, incoming, {
      tradeDate: (value) => value.tradeDate,
      observedAt: (value) => value.observedAt,
      isEmpty: (value) => value.rows.length === 0,
    })).toBe(current);
  });
});
