# 资金流可靠性实施计划

## Task 1: 同源端点回退

- [x] 为日级备用端点、连接断开和 5xx 回退写失败测试。
- [x] 实现串行回退，保留原有东方财富来源和限流策略。
- [x] 保证所有端点失败时不生成快照、不补零。

## Task 2: 部分快照与新手提示

- [x] 为分钟端点失败写诊断回归测试。
- [x] 新增端点变体和分钟错误字段，并将诊断状态标为 `partial`。
- [x] 将原因码传入驾驶舱，显示日级可用、盘中缺失的明确说明。

## Task 3: 生产验证

- [x] 运行资金流、诊断、驾驶舱聚焦测试。
- [x] 运行后端全量测试、Ruff、前端全量测试、生产构建、乱码扫描和 `git diff --check`。
- [x] 重启服务并完成真实 `600519` 准备检查及桌面/移动浏览器验收。

### 生产验证记录

- API 全量测试：`771 passed, 1 skipped`；Ruff、严格 UTF-8 解码、乱码扫描和 `git diff --check` 通过。
- Web 全量测试：`162 passed`；生产构建成功。
- 正式 API 健康检查返回 `status=ready`。
- 真实 `600519` 准备检查返回 HTTP 200，状态为 `partial`；资金流状态为 `partial`，并保留东方财富两个日报端点断连原因，不补零、不伪装为可用。
- 驾驶舱正确继承当前刷新失败：整体 `partial`、资金流 `partial`，两张当前建议卡动作均为 `observe`，置信度分别为 `0.58` 和 `0.42`。
- 桌面端及 390x844 移动端验收通过：资金流部分可用提示可见，页面无页面级横向溢出，控制台无 error/warn。

### Source-health follow-up

- [x] `EastmoneyFundFlowSource` emits append-only `SourceAttemptEvent` records for daily and minute attempts, including validated row/field counts and explicit minute failures; observer errors cannot affect the data result.
- [x] The production lifespan wires the shared `OperationsRepository.append_source_attempt` callback into the authorized fund-flow source.
