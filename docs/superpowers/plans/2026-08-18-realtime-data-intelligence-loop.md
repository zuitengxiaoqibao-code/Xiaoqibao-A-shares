# 全站实时数据与智能分析闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让真实 A 股行情、K 线、异动、新闻、板块、量化和 AI 分析通过共享快照与事件触发机制快速、完整、可追溯地呈现。

**Architecture:** 后端按数据域采集真实源，生成带版本、时间、覆盖率和证据的快照；`RealtimeSnapshotBus` 在进程内扇出增量事件，SSE 为主、HTTP 为回退。前端按快照合并，不整页闪烁；AI 只消费阈值触发的事实证据包。

**Tech Stack:** FastAPI、Python `queue`/线程池、SQLite 追溯存储、React/TypeScript、SSE、Vitest、Pytest、便携 EXE 发布脚本。

## Global Constraints

- 只有 Windows EXE 是用户交付入口，不生成浏览器产品页面。
- 真实数据缺失必须标记 `partial` 或 `unavailable`，不使用模拟值或代理值。
- 红涨绿跌；K 线增量追加，不回滚新点，不造成整页闪烁。
- 不关闭、重启或控制用户的通达信，不控制鼠标或桌面。
- 所有核心数据展示来源、采集时间、延迟、覆盖率、快照版本和限制原因。
- 发布前必须运行 `scripts/build-portable.ps1` 和 `scripts/run-portable-smoke.ps1`。

### Task 1: Shared real-time snapshot bus and overview SSE

**Files:**
- Create: `apps/api/src/qibao_api/operations/realtime_snapshot_bus.py`
- Modify: `apps/api/src/qibao_api/a_shares/market_overview.py`
- Modify: `apps/api/src/qibao_api/routes/market_overview.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Test: `apps/api/tests/operations/test_realtime_snapshot_bus.py`
- Test: `apps/api/tests/routes/test_market_overview.py`

- [x] 写总线顺序、过滤、限长队列和 SSE 帧测试。
- [x] 实现发布/订阅/最新快照保留。
- [x] 在信息总览真实快照完成后发布 `market_overview`。
- [x] 增加 SSE 初始快照、心跳和断开清理。
- [x] 保留 HTTP 路由作为回退。

### Task 2: Frontend incremental stream consumer

**Files:**
- Modify: `apps/web/src/features/market-overview/api.ts`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Test: `apps/web/src/features/market-overview/api.test.ts`

- [x] 解析完整与半帧 SSE 数据。
- [x] 接入实时推送，断线自动降级轮询。
- [x] 使用现有稳定快照合并，保留选择状态和缓存。
- [x] 在工具栏显示实时推送或 HTTP 回退状态。

### Task 3: Multi-domain stream and source health

**Files:**
- Modify: `apps/api/src/qibao_api/operations/realtime_snapshot_bus.py`
- Modify: `apps/api/src/qibao_api/a_shares/quant_strategy.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research_versions.py`
- Modify: `apps/api/src/qibao_api/routes/operations.py`
- Test: corresponding API and route tests

- [ ] 为量化、个股观察和公司研究发布独立主题。
- [ ] 统一事件去重、阈值变化和输入快照哈希。
- [ ] 将来源延迟、覆盖率、回退次数接入数据源健康面板。

### Task 4: Event-triggered AI evidence queue

- [ ] 定义事件触发条件和去重窗口。
- [ ] 生成包含事实、公式、来源、缺失字段和变化差异的 AI 输入包。
- [ ] 输出新手结论、证据、风险、失效条件、置信度和更新时间。
- [ ] AI 不可用时保留规则解释并明确原因。

### Task 5: Replay, governance and EXE acceptance

- [ ] 用回放快照重演盘中事件和 AI 输入。
- [ ] 增加断线、延迟、覆盖率和任务失败告警。
- [ ] 运行 API/Web 全量测试、编码扫描和 `git diff --check`。
- [ ] 重建便携 EXE，保留 `config/data/news/cache/logs/models/exports/backups`。
- [ ] 运行真实 EXE smoke、恢复演练和发布质量门禁。
