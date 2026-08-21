# 告警与盘后闭环收口实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成飞书、监控 TTS、盘后复盘与数据缺口诊断的端到端 EXE 交付。

**Architecture:** 复用现有实时快照总线和 Edge TTS；新增受保护通知配置、飞书投递器和监控运行器；盘后报告复用同一投递器。前端常驻播报器负责真实音频播放与状态回写。

**Tech Stack:** FastAPI、Pydantic、httpx、React、TypeScript、Edge TTS、PyInstaller。

## Global Constraints

- EXE 是唯一用户入口。
- 不关闭、重启或控制通达信，不控制鼠标和桌面。
- 不保存或输出 Webhook、API Key 等秘密。
- 不伪造行情、AI、发送成功或数据完整状态。
- 修改中文文件后执行乱码扫描和全量构建测试。

---

### Task 1: 飞书配置与投递器

**Files:** `apps/api/src/qibao_api/notifications/*`、`apps/api/src/qibao_api/routes/monitor_center.py`、对应 API 测试。

- [x] 写配置加密、URL 白名单、脱敏视图和 Webhook 响应校验的失败测试。
- [x] 运行聚焦测试确认按缺失能力失败。
- [x] 实现仓库、投递器和 GET/PUT/DELETE/test API。
- [x] 运行聚焦测试、Ruff 并提交。

### Task 2: 实时监控与常驻 TTS

**Files:** `apps/api/src/qibao_api/a_shares/monitor_center.py`、`apps/api/src/qibao_api/main.py`、`apps/web/src/features/monitor-center/*`、`apps/web/src/features/speech/*`。

- [x] 写总线触发、冷却去重、独立投递、待播领取和状态回写失败测试。
- [x] 实现运行器与 API，规则支持主题、字段路径、运算符、阈值和通道开关。
- [x] 实现常驻前端播报器及监控中心规则/状态界面。
- [x] 运行 API/Web 聚焦测试并提交。

### Task 3: 盘后自动复盘与补跑

**Files:** `apps/api/src/qibao_api/a_shares/postclose_report.py`、`apps/api/src/qibao_api/shangshu/scheduler.py`、盘后路由与历史复盘界面。

- [x] 写 15:30、启动补跑、事实冻结、AI 降级、飞书失败重试测试。
- [x] 接入统一投递器并增加报告/投递状态与手动重试 API。
- [x] 在历史复盘展示事实、AI、缺口和投递状态。
- [x] 运行聚焦测试并提交。

### Task 4: 数据缺口诊断与最终 EXE

**Files:** 数据质量聚合、监控/盘后界面、验证文档、便携发布脚本。

- [x] 为量化、公司研究、组合风险和专业数据补充缺失字段、来源水位与修复动作测试。
- [x] 实现统一诊断展示，不改变真实 `partial/unavailable` 状态。
- [x] 运行 API/Web 全量、Ruff、生产构建和乱码扫描。
- [x] 重建 EXE，运行真实 smoke、恢复演练、发布质量门禁并记录证据。
- [x] 更新项目记忆和计划勾选，提交最终文档。
