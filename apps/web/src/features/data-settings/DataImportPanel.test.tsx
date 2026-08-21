import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DataImportPanel } from "./DataImportPanel";

describe("DataImportPanel", () => {
  it("previews and imports a file with visible progress and quarantine reason", async () => {
    const inspect = vi.fn().mockResolvedValue({
      path: "quotes.csv", format: "csv", columns: ["symbol", "as_of", "close"],
      row_count: 2, preview_rows: [{ symbol: "600519", as_of: "2026-08-20", close: 1500 }], error: null,
    });
    const ingest = vi.fn().mockResolvedValue({
      task_id: "import-1", state: "succeeded", stage: "completed", progress: 100,
      processed: 2, total: 2, quarantined_rows: 1, quality_status: "partial",
      error_message: null, quarantine_reasons: ["第 2 行：股票代码无效"],
    });
    render(<DataImportPanel inspect={inspect} ingest={ingest} />);

    const file = new File(["symbol,as_of,close\n600519,2026-08-20,1500"], "quotes.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("导入数据文件"), { target: { files: [file] } });
    await waitFor(() => expect(inspect).toHaveBeenCalledWith(file));
    expect(screen.getByText("CSV · 2 行" )).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "发布导入" }));
    await waitFor(() => expect(ingest).toHaveBeenCalledWith(file, { symbol: "symbol", as_of: "as_of", close: "close" }));
    expect(await screen.findByText("已完成 · 100%" )).toBeInTheDocument();
    expect(screen.getByText("第 2 行：股票代码无效")).toBeInTheDocument();
    expect(screen.getByText("数据质量：部分可用")).toBeInTheDocument();
  });
});
