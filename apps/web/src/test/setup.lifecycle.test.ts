import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";

describe("global test lifecycle", () => {
  it("does not leak fake timers or stubbed globals into the next test", () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("starts with real timers and the original fetch implementation", () => {
    expect(vi.isFakeTimers()).toBe(false);
    expect(vi.isMockFunction(globalThis.fetch)).toBe(false);
  });

  it("allows lazy route imports to settle under release-build contention", () => {
    const setup = readFileSync("src/test/setup.ts", "utf8");
    expect(setup).toContain("asyncUtilTimeout: 5_000");
  });
});
