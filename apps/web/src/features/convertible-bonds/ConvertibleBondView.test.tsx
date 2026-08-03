import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConvertibleBondView } from "./ConvertibleBondView";

const diagnosis = {
  status: "stale_quote" as const,
  bond: { code: "113065", name: "测试转债", price: "121.50", suspended: false },
  linked_stock: { code: "600001", name: "测试股份", price: "10.25", source: "tencent", observed_at: "2026-07-14T02:30:00Z" },
  quote: { source: "tencent", observed_at: "2026-07-14T02:30:00Z", quality: "stale", turnover_amount: "526680000" },
  clause_snapshot: { source: "eastmoney", fetched_at: "2026-07-14T02:30:00Z", conversion_price: "12.34", maturity: "2028-09-15", remaining_size: "18.765432" },
  metrics: { conversion_value: "83.063", conversion_premium: "0.4627", pure_bond_premium: null, remaining_term: { days: 794 } },
  risk: { outcome: "observe_only", unknowns: ["pure_bond_value", "turnover_amount"], explanations: ["bond_liquidity_missing"] },
  strong_redemption: {
    state: "announced",
    clause_text: "发行人已发布提前赎回公告",
    source: "eastmoney",
    observed_at: "2026-07-14T02:30:00Z",
    evidence_fields: {
      "RPT_BOND_CB_LIST.NOTICE_DATE_SH": "2026-07-07 00:00:00",
      "RPT_BOND_CB_LIST.EXECUTE_START_DATESH": "2026-07-31 00:00:00",
      "RPT_BOND_CB_LIST.EXECUTE_REASON_SH": "4",
      "RPT_BOND_CB_LIST.IS_REDEEM": "是",
    },
  },
};

describe("ConvertibleBondView", () => {
  it("uses the shared terminal shell while keeping the bond domain separate", async () => {
    render(<ConvertibleBondView
      loadDashboard={() => Promise.resolve({ status: "empty", bond_count: 0, bond_codes: [] })}
      loadDiagnosis={() => Promise.resolve(diagnosis)}
      loadCandidates={() => Promise.resolve({ status: "empty", items: [] })}
    />);

    expect(screen.getByRole("region", { name: "可转债独立工作台" }))
      .toHaveClass("terminal-page", "bond-domain");
    expect(screen.getByRole("heading", { name: "可转债专区" })).toBeInTheDocument();
    expect(await screen.findByText("发现池与 A 股候选完全分离；只有行情、条款和风险输入完整且通过风险规则的转债才会进入可观察列表。")).toBeInTheDocument();
  });

  it("shows a cached diagnosis immediately while the live refresh continues", async () => {
    const liveDiagnosis = new Promise<typeof diagnosis>(() => undefined);
    render(<ConvertibleBondView
      loadDashboard={() => Promise.resolve({ status: "empty", bond_count: 0, bond_codes: [] })}
      loadCachedDiagnosis={() => Promise.resolve({
        ...diagnosis,
        is_cached: true,
        cache_recorded_at: "2026-07-14T02:31:00Z",
      })}
      loadDiagnosis={() => liveDiagnosis}
      loadCandidates={() => Promise.resolve({ status: "empty", items: [] })}
    />);

    fireEvent.click(screen.getByRole("tab", { name: "诊断" }));
    fireEvent.click(screen.getByRole("button", { name: "诊断转债" }));

    expect(await screen.findByText("测试转债")).toBeInTheDocument();
    expect(screen.getByText(/缓存快照/)).toBeInTheDocument();
    expect(screen.getByText(/后台更新中/)).toBeInTheDocument();
  });

  it("shows stale quote and evidence-backed strong redemption without invented values", async () => {
    render(<ConvertibleBondView loadDashboard={() => Promise.resolve({ status: "empty", bond_count: 0, bond_codes: [] })}
      loadDiagnosis={() => Promise.resolve(diagnosis)} loadCandidates={() => Promise.resolve({ status: "empty", items: [] })} />);
    fireEvent.click(screen.getByRole("tab", { name: "诊断" }));
    fireEvent.click(screen.getByRole("button", { name: "诊断转债" }));
    expect(await screen.findByText("行情已过期")).toBeInTheDocument();
    expect(screen.getByText("强赎已公告")).toBeInTheDocument();
    expect(screen.getByText(/发行人已发布/)).toBeInTheDocument();
    expect(screen.getByText("未知（缺少纯债价值）")).toBeInTheDocument();
    expect(screen.getByText("526680000 元")).toBeInTheDocument();
    expect(screen.getByText("仅观察")).toBeInTheDocument();
    expect(screen.getByText("当日成交额")).toBeInTheDocument();
    expect(screen.getByText(/成交额缺失/)).toBeInTheDocument();
    expect(screen.getByText("赎回公告日期")).toBeInTheDocument();
    expect(screen.getByText("2026-07-07")).toBeInTheDocument();
    expect(screen.getByText("赎回执行起始日")).toBeInTheDocument();
    expect(screen.getByText("2026-07-31")).toBeInTheDocument();
    expect(screen.getByText("执行原因")).toBeInTheDocument();
    expect(screen.getByText("原始代码 4（数据源未提供文字释义）")).toBeInTheDocument();
    expect(screen.getByText("数据源赎回标记")).toBeInTheDocument();
    expect(screen.queryByText("RPT_BOND_CB_LIST.NOTICE_DATE_SH")).not.toBeInTheDocument();
    expect(screen.queryByText("RPT_BOND_CB_LIST.EXECUTE_REASON_SH")).not.toBeInTheDocument();
  });

  it("shows authorization errors and source conflicts", async () => {
    const load = vi.fn().mockRejectedValueOnce(new Error("可转债数据源尚未授权：tencent")).mockResolvedValueOnce({ ...diagnosis, status: "source_conflict" });
    const openSettings = vi.fn();
    const props = { loadDashboard: () => Promise.resolve({ status: "empty" as const, bond_count: 0, bond_codes: [] }), loadDiagnosis: load, loadCandidates: () => Promise.resolve({ status: "empty" as const, items: [] }), openBondCompliance: openSettings };
    const { unmount } = render(<ConvertibleBondView {...props} />);
    fireEvent.click(screen.getByRole("tab", { name: "诊断" })); fireEvent.click(screen.getByRole("button", { name: "诊断转债" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("数据源尚未配置，请在数据设置中检查连接。");
    fireEvent.click(screen.getByRole("button", { name: "打开数据设置" }));
    expect(openSettings).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("尚未授权")).not.toBeInTheDocument();
    unmount(); render(<ConvertibleBondView {...props} />);
    fireEvent.click(screen.getByRole("tab", { name: "诊断" })); fireEvent.click(screen.getByRole("button", { name: "诊断转债" }));
    expect(await screen.findByText("数据源冲突")).toBeInTheDocument();
  });

  it("labels an announced redemption as an exclusion reason instead of missing data", async () => {
    render(<ConvertibleBondView
      loadDashboard={() => Promise.resolve({ status: "empty", bond_count: 0, bond_codes: [] })}
      loadDiagnosis={() => Promise.resolve({
        ...diagnosis,
        risk: { outcome: "exclude", unknowns: [], explanations: ["bond_strong_redemption_announced"] },
      })}
      loadCandidates={() => Promise.resolve({ status: "empty", items: [] })}
    />);

    fireEvent.click(screen.getByRole("tab", { name: "诊断" }));
    fireEvent.click(screen.getByRole("button", { name: "诊断转债" }));

    expect(await screen.findByText("风险依据：已公告强赎，按规则排除")).toBeInTheDocument();
    expect(screen.queryByText(/bond_strong_redemption_announced/)).not.toBeInTheDocument();
    expect(screen.queryByText(/需要补齐/)).not.toBeInTheDocument();
  });

  it("separates discovered bonds from diagnosed candidates", async () => {
    const loadDiagnosis = vi.fn().mockResolvedValue(diagnosis);
    render(<ConvertibleBondView
      loadDashboard={() => Promise.resolve({ status: "ready", bond_count: 2, bond_codes: ["113065", "123064"], discovered_count: 2, diagnosed_count: 1, unavailable_count: 1 })}
      loadDiagnosis={loadDiagnosis}
      loadCandidates={() => Promise.resolve({
        status: "empty",
        items: [],
        coverage: { discovered_count: 2, diagnosed_count: 1, candidate_count: 0, unavailable_count: 2, observed_at: null },
        discovered: [
          { bond_code: "113065", name: "测试转债", linked_stock_code: "600001", state: "unavailable", reason: "行情已过期，未进入观察候选" },
          { bond_code: "123064", name: "待诊断转债", linked_stock_code: "300001", state: "discovered", reason: "尚未诊断，行情、条款与估值尚未核验" },
        ],
      })}
    />);
    fireEvent.click(screen.getByRole("tab", { name: "候选池" }));
    expect(await screen.findByText("发现 2")).toBeInTheDocument();
    expect(screen.getByText("未诊断 · 尚未诊断，行情、条款与估值尚未核验")).toBeInTheDocument();
    expect(screen.getByText("数据不可用 · 行情已过期，未进入观察候选")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /123064/ }));
    expect(await screen.findByText("行情已过期")).toBeInTheDocument();
    expect(loadDiagnosis).toHaveBeenCalledWith("123064");
  });

  it("runs a bounded first diagnosis batch and reports its result", async () => {
    const diagnoseDiscovered = vi.fn().mockResolvedValue({
      status: "ready",
      requested: 2,
      processed: 2,
      diagnosed_count: 1,
      unavailable_count: 1,
      items: [
        { bond_code: "113065", state: "diagnosed", status: "ready", risk_outcome: "exclude" },
        { bond_code: "123064", state: "unavailable", reason_code: "invalid_provider_data" },
      ],
    });
    render(<ConvertibleBondView
      loadDashboard={() => Promise.resolve({ status: "ready", bond_count: 2, bond_codes: ["113065", "123064"], discovered_count: 2, diagnosed_count: 0, unavailable_count: 2 })}
      loadDiagnosis={() => Promise.resolve(diagnosis)}
      loadCandidates={() => Promise.resolve({ status: "empty", items: [], coverage: { discovered_count: 2, diagnosed_count: 0, candidate_count: 0, unavailable_count: 2, observed_at: null }, discovered: [] })}
      diagnoseDiscovered={diagnoseDiscovered}
    />);

    fireEvent.click(screen.getByRole("tab", { name: "候选池" }));
    fireEvent.click(await screen.findByRole("button", { name: "诊断首批" }));

    expect(diagnoseDiscovered).toHaveBeenCalledWith(6);
    expect(await screen.findByText("本轮完成诊断 1 只 · 可观察 0 只 · 风险排除 1 只 · 数据不可用 1 只")).toBeInTheDocument();
    expect(screen.getByText(/数据格式无法核验/)).toBeInTheDocument();
  });

  it("translates batch failure codes and separates risk exclusion from missing data", async () => {
    const diagnoseDiscovered = vi.fn().mockResolvedValue({
      status: "ready", requested: 2, processed: 2, diagnosed_count: 2, unavailable_count: 0,
      items: [
        { bond_code: "113065", state: "diagnosed", status: "ready", risk_outcome: "exclude" },
        { bond_code: "123064", state: "unavailable", reason_code: "source_unauthorized" },
      ],
    });
    render(<ConvertibleBondView
      loadDashboard={() => Promise.resolve({ status: "ready", bond_count: 2, bond_codes: ["113065", "123064"], discovered_count: 2, diagnosed_count: 0, unavailable_count: 2 })}
      loadDiagnosis={() => Promise.resolve(diagnosis)}
      loadCandidates={() => Promise.resolve({ status: "empty", items: [], coverage: { discovered_count: 2, diagnosed_count: 0, candidate_count: 0, unavailable_count: 1, risk_excluded_count: 1, undiagnosed_count: 0, observed_at: null }, discovered: [] })}
      diagnoseDiscovered={diagnoseDiscovered}
    />);

    fireEvent.click(screen.getByRole("tab", { name: "候选池" }));
    fireEvent.click(await screen.findByRole("button", { name: "诊断首批" }));

    expect(await screen.findByText(/数据源未授权/)).toBeInTheDocument();
    expect(screen.queryByText("source_unauthorized")).not.toBeInTheDocument();
    expect(screen.getAllByText(/风险排除/).length).toBeGreaterThan(0);
  });
});
