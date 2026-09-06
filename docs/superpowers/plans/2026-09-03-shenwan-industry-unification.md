# 申万行业统一实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将申万行业分类作为全项目唯一正式行业口径，同时保留原始来源和映射证据。

**Architecture:** 后端通过 `ShenwanIndustryResolver` 将通达信、东方财富等原始分类映射到带版本的申万代码；快照同时保存原始字段、正式字段和映射状态。所有聚合和风险计算优先使用 `shenwan_industry`，无法映射时标记待核验，不伪造行业归属。

**Tech Stack:** Python 3.12、Pydantic、SQLite、React/TypeScript。

## Global Constraints

- 旧行业字段仅作为原始证据或兼容字段，不得作为正式行业聚合依据。
- 无法映射时必须返回 `unmapped`，前端显示“申万行业待核验”。
- 中文文件按 UTF-8 修改，保留用户既有改动和便携目录持久化数据。

### Task 1: 统一契约与映射层

**Files:** `apps/api/src/qibao_api/contracts/industry.py`, `apps/api/src/qibao_api/gongbu/shenwan_industry.py`

- 定义带代码、名称、级别、版本的 `ShenwanIndustry`。
- 定义来源、匹配方式、观测时间的 `IndustryMappingEvidence`。
- 提供 SQLite 映射表和待核验返回值。

### Task 2: 接入数据快照与风险聚合

**Files:** `stock_classification.py`, `research_enrichment.py`, `fundamentals.py`, `portfolio_risk.py`, `diagnosis.py`, `market_overview.py`, `tdx_local_overview.py`, `main.py`

- 快照增加正式申万字段和映射状态。
- 组合风险、诊断、市场板块和资金流使用申万字段。
- 启动时初始化持久化映射数据库。

### Task 3: 前端统一展示

**Files:** `company-research/ResearchEnrichmentPanel.tsx`, `stock-cockpit/CockpitSections.tsx`, `a-shares/AShareResearchView.tsx`, `market-overview/types.ts`, `data-screen/presenter.ts`

- 统一显示“申万行业分类”及版本、代码、级别。
- 缺失时明确显示待核验，不显示供应商分类冒充正式行业。

### Task 4: 回归验证与交付

- 运行申万映射、分类、研报、组合风险、市场总览定向测试。
- 运行 Web/API 全量测试和构建。
- 运行 `scripts/build-portable.ps1` 与 `scripts/run-portable-smoke.ps1`。
- 更新项目记忆并确认无乱码。
