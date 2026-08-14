---
type: verification
status: confirmed
updated: 2026-08-11
tags: [verification, a-share, evidence, operations, portable]
---

# Market Evidence and Operations 验收

## Scope

本轮完成数据水位、候选筛选漏斗、后台刷新解耦、统一证据账本、
本地运维中心、策略评估门槛、公司研究决策账本和新闻事件图谱。
数据设置中的数据源健康面板默认折叠，用户展开后才读取详情。

## Automated Verification

- API: `1208 passed, 1 skipped`。
- Web: `89` 个测试文件，`540 passed`。
- TypeScript/Vite production build: passed。
- `git diff --check`: passed。
- UTF-8 strict decode for changed source files: passed。
- Mojibake scan for source and verification files: no matches。
- Company research focused regression: `16 passed`。
- News event graph focused regression: `19 passed`，包含去重、来源计数、方向门控、宏观范围和空关联防推断。

## Portable EXE Acceptance

- Build command: `scripts/build-portable.ps1`，passed。
- Release path: `dist/XiaoQiBao-Portable/xiaoqibao.exe`。
- SHA-256: `B8B433D9024BD92E73DC275E6DE31682AB2A17D11A0CC651A8A8DA854E41B174`。
- Smoke command: `scripts/run-portable-smoke.ps1 -UseReleaseData`，passed。
- Window visible: `292ms`。
- API lifespan ready: `9538ms`；full verification: `11907ms`。
- Home request: `128ms`；market overview: `119ms`；quant strategy: `550ms`。
- Market overview: `ready`；source health: `ready`；quant strategy: `partial`。
- Quant candidate count: `0`，coverage `85.00%`；零候选保留真实扫描结果，不用旧候选替代。
- Persistent directories present after rebuild: `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, `backups`。

## Data Truthfulness

- Missing professional TongdaXin plugin data remains `unavailable` with the source-specific reason; no ordinary quote or simulated value is substituted。
- News event direction is shown only for verified, non-degraded interpretation with confidence at least `0.7` and explicit positive/negative result；otherwise the UI shows `方向待核验`。
- Stock/industry/theme links require concrete verified association evidence；only a verified macro event may show `全市场` when no concrete instrument link exists。
- Red remains A-share rise/improvement/inflow；green remains fall/deterioration/outflow。
- Market watermark `ready` additionally requires at least `98%` dominant-date coverage and no watermark blockers。
- Candidate funnel `ranked` counts the full liquidity-eligible population independently of the display limit；the UI limit does not masquerade as an exclusion。
- Backtest train/validation/out-of-sample rows are withheld when closed trades are fewer than `5`；rolling rows remain explicitly `gated`。

## Process Boundary

Smoke verification left TongdaXin `TdxW.exe` PID `3336` running and did not close, restart, or control it。The temporary `xiaoqibao.exe` smoke process exited before acceptance completed。

## Residual Limitations

- The existing Vite chunk-size warning remains；it does not block compilation or the portable smoke。
- TongdaXin professional Python interfaces remain unavailable until the local professional plugin is initialized；the product reports this explicitly。
- A full market candidate pool can legitimately be empty when confirmed trading-day history or trigger evidence is incomplete。

## Plan Status

All nine tasks in `docs/superpowers/plans/2026-08-11-market-evidence-operations.md` are implemented and verified in this worktree。The portable EXE is the only user-facing delivery entry point。
