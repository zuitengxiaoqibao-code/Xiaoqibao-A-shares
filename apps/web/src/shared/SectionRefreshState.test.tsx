import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SectionRefreshState } from "./SectionRefreshState";

describe("SectionRefreshState", () => {
  it("keeps the last-good snapshot visible and exposes one scoped retry", () => {
    const onRetry = vi.fn();
    render(<><div data-testid="last-good">最新真实快照</div><SectionRefreshState state="stale" phase="本地行情刷新" error="行情源请求超时，请稍后重试。" onRetry={onRetry} /></>);

    expect(screen.getByTestId("last-good")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("保留上一次真实数据");
    expect(screen.getByRole("status")).toHaveTextContent("本地行情刷新");
    expect(screen.getByRole("status")).toHaveTextContent("行情源请求超时，请稍后重试。");
    expect(screen.getAllByRole("button", { name: "重试本区块" })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "重试本区块" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders a compact first-load error without pretending the request succeeded", () => {
    render(<SectionRefreshState state="error" phase="公司研究数据" error="公司研究数据暂不可用，请稍后重试。" onRetry={() => undefined} />);

    expect(screen.getByRole("alert")).toHaveTextContent("公司研究数据");
    expect(screen.getByRole("alert")).toHaveTextContent("公司研究数据暂不可用，请稍后重试。");
    expect(screen.getByRole("button", { name: "重试本区块" })).toBeInTheDocument();
  });
});
