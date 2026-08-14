import { describe, expect, it, vi } from "vitest";

import { scheduleRoutePreload } from "./routePreload";


describe("scheduleRoutePreload", () => {
  it("waits for an idle callback and preloads every primary route once", async () => {
    const callbacks: Array<() => void> = [];
    const cancelIdleCallback = vi.fn();
    const first = vi.fn(async () => undefined);
    const second = vi.fn(async () => undefined);
    const cancel = scheduleRoutePreload([first, second], {
      requestIdleCallback: (callback) => { callbacks.push(callback); return 7; },
      cancelIdleCallback,
    });

    expect(first).not.toHaveBeenCalled();
    callbacks[0]();
    await Promise.resolve();
    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(1);
    cancel();
    expect(cancelIdleCallback).toHaveBeenCalledWith(7);
  });
});
