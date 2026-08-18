# 尾盘选股与全站实时数据增量优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有真实数据快照和 SSE 基础上，完成尾盘两阶段扫描、稳定候选生命周期、全站分层刷新、字段级仲裁、新鲜度熔断、AI 事件触发和次日评价闭环。

**Architecture:** 慢因子按交易日批量缓存，快因子按股票输入指纹增量计算；候选状态机产生有版本的 `late_session_candidates` 快照。共享调度器为数据主题分配刷新预算，字段仲裁器保留来源冲突，快照审计和性能门禁保证可追溯与可交付。

**Tech Stack:** Python 3.11、FastAPI、Pydantic、SQLite、React 18、TypeScript、SSE、Pytest、Vitest、PowerShell 便携发布脚本。

## Global Constraints

- 只有 Windows 便携 EXE 是用户验收入口。
- 不关闭、重启或控制用户的通达信，不控制鼠标和桌面。
- 不生成模拟行情、模拟候选或代理字段。
- 数据缺失或过期必须标记 `partial` / `stale` / `unavailable`。
- 红涨绿跌；不整页闪烁，不在刷新时清空上一份真实快照。
- 所有新行为先写失败测试，再写最小实现。
- 用户自定义尾盘规则及现有 API 字段保持向后兼容。

---

### Task 1: 交易阶段与候选生命周期

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/late_session_selection.py`
- Create: `apps/api/src/qibao_api/a_shares/late_session_lifecycle.py`
- Test: `apps/api/tests/a_shares/test_late_session_lifecycle.py`

**Interfaces:**
- Produces: `classify_monitor_stage(datetime) -> LateSessionMonitorStage`
- Produces: `LateSessionLifecycleTracker.update(trading_date, candidates, observed_at) -> tuple[LateSessionCandidateResult, ...]`

- [x] 写失败测试，覆盖预计算、缩池、监控、确认、收盘竞价和冻结六个阶段。
- [x] 写失败测试，覆盖首次入池、连续 3 次升级、未通过退出、交易日切换清理和缺失字段不升级。
- [x] 实现纯函数阶段分类和内存状态跟踪器，不从其他股票推断状态。
- [x] 运行聚焦测试并提交。

### Task 2: 慢因子批量缓存与预选缩池

**Files:**
- Create: `apps/api/src/qibao_api/a_shares/late_session_factor_cache.py`
- Modify: `apps/api/src/qibao_api/a_shares/late_session_selection_service.py`
- Test: `apps/api/tests/a_shares/test_late_session_factor_cache.py`
- Test: `apps/api/tests/a_shares/test_late_session_selection_service.py`

**Interfaces:**
- Produces: `LateSessionFactorCache.get_or_build(trading_date, symbols, loader) -> SlowFactorSnapshot`
- Produces: `LateSessionSelectionService.current(..., force_full_scan=False)` 保持现有返回类型。

- [x] 写失败测试，证明同一交易日相同股票集合只加载一次历史窗口。
- [x] 写失败测试，证明缩池不超过配置上限，但严格通过股票不被分数截断。
- [x] 实现按交易日的线程安全缓存、输入指纹和缩池排序证据。
- [x] 在服务中优先使用批量历史，保留现有真实数据回退和限制提示。
- [x] 运行聚焦测试、全部尾盘 API 测试并提交。

### Task 3: 尾盘增量快照与 SSE

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/late_session_selection_service.py`
- Modify: `apps/api/src/qibao_api/routes/late_session_selection.py`
- Modify: `apps/api/src/qibao_api/operations/realtime_ai.py`
- Test: `apps/api/tests/routes/test_late_session_selection.py`
- Test: `apps/api/tests/operations/test_realtime_ai.py`

**Interfaces:**
- Produces realtime topic: `late_session_candidates`
- Consumes: `RealtimeSnapshotBus.publish(...)`

- [x] 写失败测试，候选状态指纹未改变时不重复发布。
- [x] 写失败测试，状态升级、移除和冲突时发布新快照。
- [x] 将尾盘主题加入通用 SSE 和 AI 事件触发器，只对状态变化触发 AI。
- [x] 运行实时总线、路由和 AI 聚焦测试并提交。

### Task 4: 前端候选生命周期和稳定合并

**Files:**
- Modify: `apps/web/src/features/late-session-selection/types.ts`
- Modify: `apps/web/src/features/late-session-selection/api.ts`
- Modify: `apps/web/src/features/late-session-selection/LateSessionSelectionView.tsx`
- Modify: `apps/web/src/features/late-session-selection/lateSessionSelection.css`
- Test: `apps/web/src/features/late-session-selection/LateSessionSelectionView.test.tsx`

**Interfaces:**
- Consumes realtime topic: `late_session_candidates`
- Preserves: last complete real snapshot while refresh is pending or failed

- [x] 写失败测试，验证 SSE 只更新变化候选，断线回退调用 `next_refresh_ms`。
- [x] 写失败测试，验证页面显示首次入池、持续时长、触发次数、最近变化和淘汰原因。
- [x] 实现不清空的快照合并和四种候选状态标签。
- [x] 运行聚焦 Vitest 与 TypeScript 构建并提交。

### Task 5: 分层刷新预算、字段仲裁与熔断

**Files:**
- Create: `apps/api/src/qibao_api/operations/refresh_policy.py`
- Create: `apps/api/src/qibao_api/operations/field_arbitration.py`
- Create: `apps/api/src/qibao_api/operations/source_circuit_breaker.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_overview.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Test: `apps/api/tests/operations/test_refresh_policy.py`
- Test: `apps/api/tests/operations/test_field_arbitration.py`
- Test: `apps/api/tests/operations/test_source_circuit_breaker.py`

**Interfaces:**
- Produces: `RefreshPolicy.interval_ms(topic, phase, visible) -> int | None`
- Produces: `FieldArbitrator.select(field, evidences, now) -> FieldResolution`
- Produces: `SourceCircuitBreaker.before_request/record_success/record_failure/status`

- [x] 写失败测试，覆盖 L0–L3 在盘前、盘中、午休、盘后和页面隐藏时的调度。
- [x] 写失败测试，覆盖新鲜主源、过期主源回退、字段冲突和不可用。
- [x] 写失败测试，覆盖连续失败熔断、半开探测和恢复。
- [x] 实现三个独立纯组件，先接入尾盘和市场总览两个高价值链路。
- [x] 运行聚焦测试和市场总览回归并提交。

### Task 6: 快照审计与次日真实评价

**Files:**
- Create: `apps/api/src/qibao_api/storage/late_session_audit_store.py`
- Create: `apps/api/src/qibao_api/a_shares/late_session_evaluation.py`
- Modify: `apps/api/src/qibao_api/a_shares/late_session_selection_service.py`
- Test: `apps/api/tests/storage/test_late_session_audit_store.py`
- Test: `apps/api/tests/a_shares/test_late_session_evaluation.py`

**Interfaces:**
- Produces: append-only audit snapshots linked by `snapshot_id`, `input_hash`, `formula_version`
- Produces: `evaluate_next_session(snapshot, bars) -> LateSessionOutcome`

- [x] 写失败测试，证明审计仓追加、幂等且禁止修改/删除。
- [x] 写失败测试，覆盖次日开盘涨幅、最高涨幅、最大回撤和假突破，禁止读取截止时间之后的选股输入。
- [x] 实现 SQLite 审计仓和纯评价器，按 Regime 保留分层结果。
- [x] 运行存储和评价聚焦测试并提交。

### Task 7: 数据质量与性能发布治理

**Files:**
- Modify: `apps/api/src/qibao_api/operations/observability.py`
- Modify: `apps/api/src/qibao_api/operations/quality_gates.py`
- Modify: `scripts/run-portable-smoke.ps1`
- Modify: `scripts/verify-release-quality.ps1`
- Test: `apps/api/tests/operations/test_quality_gates.py`
- Test: `scripts/verify-release-quality.tests.ps1`

**Interfaces:**
- Produces release evidence: `late_session_metrics`, `realtime_freshness`, `traceability`

- [x] 写失败测试，关键延迟、候选丢失和快照不可追溯阻断发布。
- [x] 非关键源的真实缺失仅产生 warning，不降格为伪 pass。
- [x] smoke 采集预计算、缩池、增量评估 P95、候选保留、快照延迟、SSE 丢帧和 AI 积压。
- [x] 运行 API 治理测试和 Pester 回归并提交。

### Task 8: 全量验证与 EXE 交付

**Files:**
- Modify: `docs/verification/2026-08-18-late-session-realtime-optimization.md`
- Generated: `dist/XiaoQiBao-Portable/xiaoqibao.exe`

- [x] 运行 API 全量 Pytest 和 Ruff。
- [x] 运行 Web 全量 Vitest、TypeScript 和 Vite 生产构建。
- [x] 运行 UTF-8/乱码扫描和 `git diff --check`。
- [x] 运行 `scripts/build-portable.ps1`，保留 `config/data/news/cache/logs/models/exports/backups`。
- [x] 运行 `scripts/run-portable-smoke.ps1` 、恢复演练和发布质量门禁。
- [x] 记录 EXE 路径、SHA-256、测试计数、性能指标和真实数据边界并提交。
