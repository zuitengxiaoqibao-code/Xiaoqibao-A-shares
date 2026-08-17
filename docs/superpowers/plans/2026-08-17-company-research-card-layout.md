# 公司研究卡片排版修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复十段公司研究账本的方框错位，让箭头、编号、标题摘要和状态标签稳定对齐。

**Architecture:** 只调整账本组件的 DOM 布局契约与局部 CSS，显式渲染箭头并为摘要预留四列；不改 API、数据语义和路由。

**Tech Stack:** React、TypeScript、Vitest、CSS、Vite、Windows portable EXE。

## Global Constraints

- 交付入口只能是 Windows EXE，不交付独立 HTML。
- 中文文件保持 UTF-8；优先使用 `apply_patch`。
- 红涨绿跌语义不变；本次不改数据颜色。
- 不关闭、重启或控制通达信，不控制鼠标或桌面。

### Task 1: 锁定错误布局

**Files:**
- Modify: `apps/web/src/features/company-research/CompanyResearchSections.test.tsx`

- [ ] **Step 1: 写失败测试**

在现有测试中增加断言：每张账本摘要都有 `data-part="chevron"`，且四个布局单元分别标记 `chevron`、`index`、`content`、`status`。

- [ ] **Step 2: 运行测试确认失败**

运行 `npm --prefix apps/web test -- CompanyResearchSections.test.tsx --run`，预期因当前组件没有显式箭头和布局标记而失败。

### Task 2: 修复账本 DOM 与 CSS

**Files:**
- Modify: `apps/web/src/features/company-research/CompanyResearchSections.tsx`
- Modify: `apps/web/src/features/company-research/companyResearch.css`

- [ ] **Step 1: 增加显式四列布局单元**

摘要依次渲染箭头、编号、标题摘要容器和状态标签，箭头使用 `aria-hidden="true"`，保留现有 `details` 原生展开行为。

- [ ] **Step 2: 局部覆盖全局折叠伪元素**

为账本摘要关闭 `::before`，四列宽屏布局为 `14px 32px minmax(0,1fr) auto`；打开时仅旋转显式箭头；小屏切换为 `14px 28px minmax(0,1fr)`，状态落到内容列。

### Task 3: 验证与交付

**Files:**
- Create: `docs/verification/2026-08-17-company-research-card-layout.md`

- [ ] **Step 1:** 定向 Web 测试通过。
- [ ] **Step 2:** Web 全量测试、生产构建、乱码扫描和 `git diff --check` 通过。
- [ ] **Step 3:** 运行 `scripts/build-portable.ps1` 重建便携 EXE。
- [ ] **Step 4:** 运行 `scripts/run-portable-smoke.ps1 -UseReleaseData`，确认实际 EXE 启动。
- [ ] **Step 5:** 运行发布质量门禁并记录 EXE 路径、哈希和测试证据。
