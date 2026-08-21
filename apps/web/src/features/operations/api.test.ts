import { afterEach, describe, expect, it, vi } from "vitest";

import { cleanupCache } from "./api";

describe("operations api", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requests guarded cache cleanup with the selected retention window", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(
      JSON.stringify({ removed_count: 3, removed_bytes: 2048 }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));

    await expect(cleanupCache(72)).resolves.toEqual({ removed_count: 3, removed_bytes: 2048 });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/operations/cache/cleanup?older_than_hours=72");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST" });
  });
});
