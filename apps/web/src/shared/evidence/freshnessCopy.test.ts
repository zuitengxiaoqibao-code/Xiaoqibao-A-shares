import { describe, expect, it } from "vitest";

import { blockerLabel, freshnessLabel, freshnessDetail } from "./freshnessCopy";

describe("freshness copy", () => {
  it("uses one visible label for every evidence state", () => {
    expect(freshnessLabel("ready")).toBe("数据已就绪");
    expect(freshnessLabel("partial")).toBe("数据部分可用");
    expect(freshnessLabel("stale")).toBe("使用历史数据");
    expect(freshnessLabel("unavailable")).toBe("数据不可用");
    expect(freshnessLabel("error")).toBe("数据加载失败");
    expect(freshnessDetail("stale")).toContain("不代表实时");
  });

  it("translates known internal blockers and hides unknown implementation codes", () => {
    expect(blockerLabel("history_coverage_below_98_percent")).toBe("历史覆盖率低于 98% 就绪门槛");
    expect(blockerLabel("incomplete_daily_history")).toBe("历史覆盖不完整");
    expect(blockerLabel("some_internal_code")).toBe("数据完整性待检查");
    expect(blockerLabel("some_internal_code")).not.toContain("some_internal_code");
  });
});
