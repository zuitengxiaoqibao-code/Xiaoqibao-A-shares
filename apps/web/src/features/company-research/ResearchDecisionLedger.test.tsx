import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ResearchDecisionLedger } from "./ResearchDecisionLedger";
import type { ResearchDecisionLedgerRow } from "./types";

const rows: ResearchDecisionLedgerRow[] = [
  { key: "peer_context", label: "同行参照", status: "ready", summary: "已核验 2 家同板块同行。", facts: ["600809 山西汾酒 · PE 28.00"], evidence_ids: [], limitation: null },
  { key: "valuation", label: "估值证据", status: "partial", summary: "仅有 2 家机构预测，不计算前向 PE。", facts: ["PE(TTM) 25.00", "明年EPS预测样本 2家，未达到3家门槛"], evidence_ids: [], limitation: "缺少历史估值序列。" },
  { key: "catalysts", label: "未来催化", status: "ready", summary: "识别 1 项正向事件。", facts: ["2026-08-05 · 签署合作协议"], evidence_ids: ["notice-1"], limitation: "不推导涨跌。" },
  { key: "contrary", label: "反方证据", status: "triggered", summary: "触发 1 项。", facts: ["盈利与现金流不匹配"], evidence_ids: ["cash-1"], limitation: null },
  { key: "invalidation", label: "逻辑失效", status: "triggered", summary: "需要重新核验研究假设。", facts: ["现金利润比低于规则阈值"], evidence_ids: ["cash-1"], limitation: null },
];

describe("ResearchDecisionLedger", () => {
  it("renders five compact research decisions and expands their verified facts", () => {
    render(<ResearchDecisionLedger rows={rows} />);

    const region = screen.getByRole("region", { name: "公司研究决策账本" });
    expect(region.querySelectorAll("details")).toHaveLength(5);
    expect(region).toHaveTextContent("低样本不计算前向 PE");
    const valuation = screen.getByText("估值证据").closest("details");
    fireEvent.click(screen.getByText("估值证据"));
    expect(valuation).toHaveAttribute("open");
    expect(valuation).toHaveTextContent("明年EPS预测样本 2家，未达到3家门槛");
    expect(region).not.toHaveTextContent(/目标价|建议买入|建议卖出/);
  });
});
