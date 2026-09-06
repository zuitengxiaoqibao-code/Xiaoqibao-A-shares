import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExternalDataSourceSection } from "./ExternalDataSourceSection";
import type { ExternalDataSourceView } from "./types";

const source = (sourceId: ExternalDataSourceView["source_id"], name: string): ExternalDataSourceView => ({
  source_id: sourceId,
  name,
  description: `${name}备用接口`,
  capabilities: ["实时行情", "日线 K 线"],
  key_label: `${name} API Key`,
  key_url: "https://example.com/docs",
  configured: false,
  enabled: false,
  api_key_hint: null,
  status: "unconfigured",
  last_tested_at: null,
  last_error: null,
});

describe("ExternalDataSourceSection", () => {
  it("shows all built-in sources with a clear unconfigured status", async () => {
    render(<ExternalDataSourceSection
      load={() => Promise.resolve({ sources: [source("tickflow", "TickFlow"), source("fuyao", "扶摇"), source("tushare", "Tushare")] })}
      save={vi.fn()}
      clear={vi.fn()}
      test={vi.fn()}
    />);

    expect(await screen.findByRole("heading", { name: "第三方行情数据源" })).toBeInTheDocument();
    expect(screen.getAllByText("未配置")).toHaveLength(3);
    expect(screen.getByText("TickFlow")).toBeInTheDocument();
    expect(screen.getByText("扶摇")).toBeInTheDocument();
    expect(screen.getByText("Tushare")).toBeInTheDocument();
  });

  it("saves a key without rendering the secret and tests a failed connection", async () => {
    const save = vi.fn().mockResolvedValue({ ...source("tickflow", "TickFlow"), configured: true, enabled: true, status: "configured", api_key_hint: "****-1234" });
    const test = vi.fn().mockResolvedValue({ ...source("tickflow", "TickFlow"), configured: true, enabled: true, status: "unavailable", api_key_hint: "****-1234", last_error: "网络不可达" });
    render(<ExternalDataSourceSection
      load={() => Promise.resolve({ sources: [source("tickflow", "TickFlow")] })}
      save={save}
      clear={vi.fn()}
      test={test}
    />);

    const input = await screen.findByLabelText("TickFlow API Key");
    fireEvent.change(input, { target: { value: "secret-token-1234" } });
    fireEvent.click(screen.getByRole("button", { name: "保存并测试" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("tickflow", "secret-token-1234", true));
    expect(screen.queryByText("secret-token-1234")).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText("****-1234")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "测试连接" }));
    await waitFor(() => expect(test).toHaveBeenCalledWith("tickflow"));
    expect(await screen.findByText(/TickFlow：异常/)).toBeInTheDocument();
  });

  it("runs the capability test immediately after saving a key", async () => {
    const save = vi.fn().mockResolvedValue({ ...source("tickflow", "TickFlow"), configured: true, enabled: true, status: "configured", api_key_hint: "****-1234" });
    const test = vi.fn().mockResolvedValue({ ...source("tickflow", "TickFlow"), configured: true, enabled: true, status: "limited", api_key_hint: "****-1234", capability_checks: [] });
    render(<ExternalDataSourceSection
      load={() => Promise.resolve({ sources: [source("tickflow", "TickFlow")] })}
      save={save}
      clear={vi.fn()}
      test={test}
    />);

    fireEvent.change(await screen.findByLabelText("TickFlow API Key"), { target: { value: "secret-token-1234" } });
    fireEvent.click(screen.getByRole("button", { name: "保存并测试" }));

    await waitFor(() => expect(save).toHaveBeenCalledWith("tickflow", "secret-token-1234", true));
    await waitFor(() => expect(test).toHaveBeenCalledWith("tickflow"));
  });

  it("clears a configured source and returns to unconfigured", async () => {
    const configured = { ...source("tushare", "Tushare"), configured: true, enabled: true, status: "configured" as const, api_key_hint: "****-demo" };
    const clear = vi.fn().mockResolvedValue(source("tushare", "Tushare"));
    render(<ExternalDataSourceSection
      load={() => Promise.resolve({ sources: [configured] })}
      save={vi.fn()}
      clear={clear}
      test={vi.fn()}
    />);

    fireEvent.click(await screen.findByRole("button", { name: "清除" }));
    await waitFor(() => expect(clear).toHaveBeenCalledWith("tushare"));
    expect(await screen.findByText("Tushare：未配置")).toBeInTheDocument();
  });

  it("strikes through capabilities that the configured key cannot access", async () => {
    const configured = {
      ...source("tickflow", "TickFlow"),
      configured: true,
      enabled: true,
      status: "limited" as const,
      api_key_hint: "****-demo",
      capability_checks: [
        { key: "realtime_quotes", label: "实时行情", status: "limited" as const, detail: "当前 Key 没有此接口权限", reason_code: "permission_denied", tested_at: "2026-09-04T00:00:00Z" },
        { key: "daily_klines", label: "日线 K 线", status: "ready" as const, detail: "接口响应正常", reason_code: "ok", tested_at: "2026-09-04T00:00:00Z" },
      ],
    };
    render(<ExternalDataSourceSection
      load={() => Promise.resolve({ sources: [configured] })}
      save={vi.fn()}
      clear={vi.fn()}
      test={vi.fn()}
    />);

    const limited = await screen.findByText("实时行情");
    expect(limited).toHaveAttribute("data-status", "limited");
    expect(limited).toHaveClass("capability-limited");
    expect(limited).toHaveAttribute("title", "无权限：当前 Key 没有此接口权限");
  });
});
