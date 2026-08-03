import { describe, expect, it } from "vitest";

import type { BondCandidates } from "./types";
import { bondTaskCards, bondTaskPreview } from "./taskCards";

describe("bondTaskCards", () => {
  it("keeps discovered bond states separate and promotes verified candidates", () => {
    const input: BondCandidates = {
      status: "ready",
      items: [{ bond_code: "113065", conversion_premium: "0.12", risk: { outcome: "eligible" } }],
      discovered: [
        { bond_code: "113065", name: "样本转债", linked_stock_code: "600001", state: "diagnosed", reason: null },
        { bond_code: "123064", name: "待诊断转债", linked_stock_code: "300001", state: "discovered", reason: "尚未诊断" },
        { bond_code: "110001", name: "缺失转债", linked_stock_code: null, state: "unavailable", reason: "行情不可用" },
        { bond_code: "127001", name: "排除转债", linked_stock_code: "000001", state: "risk_excluded", reason: "强赎风险" },
      ],
    };

    expect(bondTaskCards(input)).toEqual([
      expect.objectContaining({ code: "113065", stateLabel: "可观察", tone: "ready" }),
      expect.objectContaining({ code: "123064", stateLabel: "未诊断", tone: "pending" }),
      expect.objectContaining({ code: "110001", stateLabel: "数据不可用", tone: "unavailable" }),
      expect.objectContaining({ code: "127001", stateLabel: "风险排除", tone: "excluded" }),
    ]);
  });

  it("appends candidates missing from discovery exactly once without invented metrics", () => {
    const cards = bondTaskCards({
      status: "ready",
      items: [{ bond_code: "113065", conversion_premium: null, risk: { outcome: "eligible" } }],
      discovered: [],
    });

    expect(cards).toHaveLength(1);
    expect(cards[0]).toEqual({
      code: "113065", name: "转债 113065", linkedStockCode: null,
      stateLabel: "可观察", reason: null, tone: "ready",
    });
    expect(cards[0]).not.toHaveProperty("price");
    expect(cards[0]).not.toHaveProperty("score");
  });

  it("limits the overview stack and puts actionable or risky records before pending ones", () => {
    const cards = [
      ...Array.from({ length: 8 }, (_, index) => ({
        code: `12${index}`,
        name: `待诊断 ${index}`,
        linkedStockCode: null,
        stateLabel: "未诊断",
        reason: null,
        tone: "pending" as const,
      })),
      { code: "ready", name: "可观察", linkedStockCode: null, stateLabel: "可观察", reason: null, tone: "ready" as const },
      { code: "risk", name: "风险排除", linkedStockCode: null, stateLabel: "风险排除", reason: "强赎风险", tone: "excluded" as const },
      { code: "missing", name: "数据不可用", linkedStockCode: null, stateLabel: "数据不可用", reason: "行情不可用", tone: "unavailable" as const },
    ];

    expect(bondTaskPreview(cards)).toEqual({
      visible: [
        expect.objectContaining({ code: "ready" }),
        expect.objectContaining({ code: "risk" }),
        expect.objectContaining({ code: "missing" }),
        ...cards.slice(0, 4).map((card) => expect.objectContaining({ code: card.code })),
      ],
      hiddenCount: 4,
    });
  });
});
