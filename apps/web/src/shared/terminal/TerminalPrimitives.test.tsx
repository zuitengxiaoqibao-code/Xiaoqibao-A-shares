import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  TerminalMetricBand,
  TerminalPageHeader,
  TerminalPanel,
  TerminalStateNotice,
  TerminalStatusStrip,
} from "./TerminalPrimitives";

describe("terminal visual primitives", () => {
  it("renders a shared page header and explicit partial state", () => {
    render(<>
      <TerminalPageHeader eyebrow="MARKET / OVERVIEW" title="信息总览" />
      <TerminalStateNotice state="partial" title="部分数据可用" detail="保留最近快照" />
    </>);

    expect(screen.getByRole("heading", { name: "信息总览" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "partial");
    expect(screen.getByRole("status")).toHaveTextContent("保留最近快照");
  });

  it("composes status, metrics and panel content without business logic", () => {
    render(<>
      <TerminalStatusStrip ariaLabel="数据状态"><span>实时数据就绪</span></TerminalStatusStrip>
      <TerminalMetricBand ariaLabel="核心指标"><div>市场情绪 76</div></TerminalMetricBand>
      <TerminalPanel title="决策证据" subtitle="已验证" ariaLabel="决策证据面板">
        <p>价格和新闻时间一致</p>
      </TerminalPanel>
    </>);

    expect(screen.getByRole("region", { name: "数据状态" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "核心指标" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "决策证据面板" })).toHaveTextContent("已验证");
  });
});
