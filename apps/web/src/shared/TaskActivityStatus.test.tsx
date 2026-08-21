import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { TaskActivityStatus } from "./TaskActivityStatus";
import { resetTaskActivityForTests, updateTaskActivity } from "./taskActivity";

describe("TaskActivityStatus", () => {
  beforeEach(() => resetTaskActivityForTests());
  it("shows the real AI configuration state and an active data task", () => {
    updateTaskActivity({ id: "timeline:600519", label: "个股事件 K 线", stage: "正在加载事件", state: "running", percent: 42 });
    render(<TaskActivityStatus ai={{ configured: false, state: "unconfigured", message: "尚未配置 AI 接口" }} />);

    expect(screen.getByText("AI 未配置")).toBeInTheDocument();
    expect(screen.getByText("正在加载事件")).toBeInTheDocument();
    expect(screen.getByText("42%")).toBeInTheDocument();
  });

  it("shows a Chinese failure reason without polling when there are no tasks", () => {
    updateTaskActivity({ id: "research:600519", label: "公司研究", stage: "财务源失败", state: "failed", error: "财务源连接超时" });
    render(<TaskActivityStatus ai={{ configured: true, state: "connection_failed", message: "AI 连接失败" }} />);

    expect(screen.getByText("AI 异常")).toBeInTheDocument();
    expect(screen.getByText("财务源连接超时")).toBeInTheDocument();
    expect(screen.queryByText("正在轮询")).not.toBeInTheDocument();
  });

  it("cleans its singleton state between tests", () => {
    render(<TaskActivityStatus ai={{ configured: true, state: "connected", message: "AI 已连接" }} />);
    expect(screen.getByText("AI 正常")).toBeInTheDocument();
    expect(screen.queryByText("正在加载事件")).not.toBeInTheDocument();
  });
});
