import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DailyRefreshStatus } from "./DailyRefreshStatus";

describe("DailyRefreshStatus", () => {
  it("keeps a visible live-monitoring state after the latest data finishes loading", () => {
    render(<DailyRefreshStatus
      label="个股观察"
      cachedAt="2026-08-03T13:20:00+08:00"
      updatedAt="2026-08-03T13:30:00+08:00"
      loading={false}
      progress={{ percent: 100, stage: "complete", detail: "最新数据已载入" }}
    />);

    const status = screen.getByRole("status", { name: "个股观察数据刷新状态" });
    expect(status).toHaveTextContent("已加载实时最新数据");
    expect(status).toHaveTextContent("当前状态：实时监控中");
    expect(status).toHaveTextContent("最新数据时间：");
    expect(status).toHaveAttribute("data-monitoring", "live");
  });

  it("distinguishes latest available data from fully completed live monitoring", () => {
    render(<DailyRefreshStatus
      label="个股观察"
      cachedAt="2026-08-03T13:20:00+08:00"
      updatedAt="2026-08-03T13:30:00+08:00"
      loading={false}
      completion="partial"
      progress={{ percent: 100, stage: "complete", detail: "核心行情已载入" }}
    />);

    const status = screen.getByRole("status", { name: "个股观察数据刷新状态" });
    expect(status).toHaveTextContent("已加载最新可用数据");
    expect(status).toHaveTextContent("核心行情已更新，扩展数据仍待补齐");
    expect(status).not.toHaveTextContent("已加载实时最新数据");
    expect(status).toHaveAttribute("data-monitoring", "partial");
  });

  it("explains the failed stage, target and original reason", () => {
    render(<DailyRefreshStatus
      label="公司研究"
      cachedAt="2026-08-03T13:20:00+08:00"
      loading={false}
      progress={{ percent: 58, stage: "receiving", detail: "已接收 4096 字节" }}
      error="本地财务接口连接超时"
    />);

    const status = screen.getByRole("status", { name: "公司研究数据刷新状态" });
    expect(status).toHaveTextContent("失败环节：数据接收");
    expect(status).toHaveTextContent("失败对象：公司研究最新数据");
    expect(status).toHaveTextContent("原因：本地财务接口连接超时");
  });
});
