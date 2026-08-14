# 全站加载进度连续反馈 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复公司研究、个股观察等页面加载进度长期停在 1% 后跳到 100% 的问题，同时保持进度含义真实可解释。

**Architecture:** 在共享 `fetchJsonWithProgress` 中加入响应头等待阶段的受限估算计时器，收到响应后切换到真实字节/接收阶段；`DailyRefreshStatus` 统一展示可信度、耗时和持续运动反馈。首页和量化已有更真实的阶段进度，保持不变。

**Tech Stack:** React 19、TypeScript 5.8、Vitest、CSS、Vite、PyInstaller。

## Global Constraints

- EXE 是唯一用户交付入口。
- 禁止把估算进度描述成真实后端完成比例。
- 进度不得倒退，解析成功前不得到达 100%。
- 不关闭、重启或控制通达信。
- 修改后执行 Web 全量测试、生产构建、乱码扫描、便携构建和真实发布 smoke。

---

### Task 1: 响应等待阶段连续进度

**Files:**
- Modify: `apps/web/src/shared/fetchJsonWithProgress.ts`
- Modify: `apps/web/src/shared/fetchJsonWithProgress.test.ts`

- [x] **Step 1:** 增加失败测试，证明响应头未到达时百分比会继续上升、明确为阶段估算且不超过 45%。
- [x] **Step 2:** 运行聚焦测试并确认因当前进度停在 1% 而失败。
- [x] **Step 3:** 实现受限估算计时器、单调进度、真实字节切换和清理逻辑。
- [x] **Step 4:** 运行聚焦测试并确认通过。

### Task 2: 共享状态视觉与语义

**Files:**
- Modify: `apps/web/src/shared/DailyRefreshStatus.tsx`
- Modify: `apps/web/src/shared/DailyRefreshStatus.test.tsx`
- Modify: `apps/web/src/shared/dailyRefreshStatus.css`

- [x] **Step 1:** 增加失败测试，要求加载状态展示“阶段估算/真实字节/正在校验”标签。
- [x] **Step 2:** 实现可信度标签、已等待时间文案和进度轨道流光。
- [x] **Step 3:** 运行共享组件、公司研究和个股观察测试。

### Task 3: 全量验收与 EXE 交付

**Files:**
- Create: `docs/verification/2026-08-12-sitewide-loading-progress.md`
- Modify: durable project memory after verification.

- [x] **Step 1:** 运行 Web 全量测试和生产构建。
- [x] **Step 2:** 执行 UTF-8/乱码扫描和 `git diff --check`。
- [x] **Step 3:** 重建便携 EXE并保留八类持久目录。
- [x] **Step 4:** 使用真实发布数据执行 smoke，记录性能、SHA-256 和进程释放结果。
- [x] **Step 5:** 更新验证文档与长期项目记忆。
