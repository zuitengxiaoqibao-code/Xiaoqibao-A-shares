import { describe, expect, it, vi } from "vitest";

describe("global test lifecycle", () => {
  it("does not leak fake timers or stubbed globals into the next test", () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("starts with real timers and the original fetch implementation", () => {
    expect(vi.isFakeTimers()).toBe(false);
    expect(vi.isMockFunction(globalThis.fetch)).toBe(false);
  });
});
