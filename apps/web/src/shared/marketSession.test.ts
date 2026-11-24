import { afterEach, expect, it, vi } from "vitest";
import { loadMarketStage } from "./marketSession";
import { apiClient } from "./apiClient";

afterEach(() => vi.restoreAllMocks());

it.each([
  ["intraday", "正在更新"], ["lunch_break", "已暂停"], ["closed", "休市"],
  ["pre_open", "休市"], ["post_close", "休市"], ["unknown", "状态未知"],
])("uses the server's %s market phase", async (phase, expected) => {
  vi.spyOn(apiClient, "get").mockResolvedValue({ status: "ready", phase });
  expect(await loadMarketStage()).toBe(expected);
});

it("shows unknown when the API is unavailable", async () => {
  vi.spyOn(apiClient, "get").mockRejectedValue(new Error("offline"));
  expect(await loadMarketStage()).toBe("状态未知");
});
