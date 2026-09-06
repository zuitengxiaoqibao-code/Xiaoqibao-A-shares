# 数据大屏 C3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将数据大屏改造成紧凑、投影友好、数据驱动动态的 C3 主视区，减少留白和新闻占用，同时保持真实数据边界。

**Architecture:** 继续复用现有 `MarketOverviewResponse`、尾盘选股、首次涨停和新闻告警 loader，不增加重复行情连接。布局通过现有 CSS Grid 重排，动态效果只在局部数据容器更新时触发，所有长列表在容器内轮播，不重挂载整页。

**Tech Stack:** React 18、TypeScript、CSS Grid/Flex、Vitest、Vite、PyInstaller portable EXE。

## Global Constraints

- 股票上涨使用红色，下跌使用绿色。
- 不生成模拟行情；缺失数据必须显示 `--`、等待或真实不可用状态。
- 新闻压缩为底部快讯带，不占据主视区大面积空间。
- 不使用页面滚动条作为大屏主要交互；1920×1080 最大化优先。
- 刷新只更新局部容器，不触发整页闪烁或路由重挂载。
- 最终交付入口为 Windows EXE，构建后必须运行便携版烟测。

### Task 1: C3 布局回归基线

**Files:**
- Modify: `apps/web/src/features/data-screen/DataScreenView.test.tsx`
- Test: `apps/web/src/features/data-screen/DataScreenView.test.tsx`

- [x] **Step 1: 写入布局约束断言**

```ts
it("uses the compact C3 information hierarchy", () => {
  expect(dataScreenCss).toContain("data-screen-c3");
  expect(dataScreenCss).toContain("data-screen-left-matrix");
  expect(dataScreenCss).toContain("data-screen-news-strip");
  expect(dataScreenCss).toMatch(/\.data-screen-grid[\\s\\S]*grid-template-areas/);
});
```

- [x] **Step 2: 运行测试确认断言失败**

Run: `pnpm --filter @qibao/web test -- src/features/data-screen/DataScreenView.test.tsx`
Expected: FAIL because the C3 class names do not exist yet.

### Task 2: 左侧紧凑数据矩阵

**Files:**
- Modify: `apps/web/src/features/data-screen/DataScreenView.tsx`
- Modify: `apps/web/src/features/data-screen/dataScreen.css`

- [x] **Step 1: 将左侧市场广度内容包入 C3 矩阵容器**

```tsx
<div className="data-screen-left-matrix">
  <div className="data-screen-hero-number">...</div>
  <div className="data-screen-breadth-stack">...</div>
  <div className="data-screen-breadth-legend">...</div>
  <div className="data-screen-mini-grid">...</div>
  <div className="data-screen-limit-bars">...</div>
</div>
```

- [x] **Step 2: 用 2 列紧凑网格替代大块留白**

```css
.data-screen-c3 .data-screen-breadth .terminal-panel-body { display: grid; grid-template-rows: auto auto auto auto 1fr; gap: 7px; }
.data-screen-left-matrix { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 7px; min-height: 0; }
.data-screen-left-matrix > .data-screen-hero-number,
.data-screen-left-matrix > .data-screen-breadth-stack,
.data-screen-left-matrix > .data-screen-breadth-legend,
.data-screen-left-matrix > .data-screen-limit-bars { grid-column: 1 / -1; }
.data-screen-c3 .data-screen-mini-grid { margin-top: 0; }
```

- [x] **Step 3: 运行数据大屏测试**

Run: `pnpm --filter @qibao/web test -- src/features/data-screen/DataScreenView.test.tsx`
Expected: PASS.

### Task 3: 主视区重排与新闻压缩

**Files:**
- Modify: `apps/web/src/features/data-screen/DataScreenView.tsx`
- Modify: `apps/web/src/features/data-screen/dataScreen.css`
- Modify: `apps/web/src/features/data-screen/dataScreenViewport.css`

- [x] **Step 1: 添加 C3 页面类和新闻条类**

```tsx
<main className="terminal-page data-screen-page data-screen-c3" ...>
...
<div key={`news-${newsWindow.offset}`} className="data-screen-news-ticker data-screen-news-strip data-screen-rail-swap" ...>
```

- [x] **Step 2: 将主网格改为核心行情优先的三行布局**

```css
.data-screen-c3 .data-screen-grid {
  grid-template-columns: minmax(0, .78fr) minmax(0, 1.55fr) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1.35fr) minmax(0, 1fr) minmax(0, .62fr);
  grid-template-areas: "breadth indices sectors" "liquidity flow stocks" "events events audit";
}
.data-screen-news-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; margin-top: 4px; padding-top: 4px; }
.data-screen-news-strip button { min-height: 34px; padding: 3px 5px; }
```

- [x] **Step 3: 验证桌面和窄屏规则不产生新滚动条**

Run: `pnpm --filter @qibao/web test -- src/features/data-screen/DataScreenView.test.tsx src/app/layout-safety.test.ts`
Expected: PASS.

### Task 4: 数据驱动动态反馈

**Files:**
- Modify: `apps/web/src/features/data-screen/DataScreenView.tsx`
- Modify: `apps/web/src/features/data-screen/dataScreen.css`
- Test: `apps/web/src/features/data-screen/DataScreenView.test.tsx`

- [x] **Step 1: 为数据变化增加可观察的局部状态类**

```tsx
const livePanelClass = pulseActive ? " data-screen-pulse" : "";
const flowClass = pulseActive ? " flow-field-live" : "";
```

- [x] **Step 2: 仅使用短脉冲和呼吸，不做整页持续移动**

```css
.data-screen-c3 .data-screen-pulse { animation: screen-panel-pulse 1.1s ease-out; }
.data-screen-c3 .flow-node-live { animation: screen-flow-node-live 1.1s ease-out; }
.data-screen-c3 .flow-line-live { animation: screen-flow-line-live 1.1s ease-out; }
```

- [x] **Step 3: 测试辅助数据变化会触发局部高亮且失败不清空旧内容**

```ts
expect(screen.getByRole("region", { name: "尾盘选股候选" })).toHaveClass("data-screen-pulse");
```

- [x] **Step 4: 运行全量前端测试**

Run: `pnpm --filter @qibao/web test`
Expected: all test files pass.

### Task 5: 生产验证与 EXE 交付

**Files:**
- Modify: `docs/superpowers/plans/2026-09-01-data-screen.md`
- Modify: `D:/Users/90090/Documents/知识库/02-项目记忆/金融财经.md`

- [x] **Step 1: 运行生产构建和差异检查**

Run: `pnpm --filter @qibao/web build; git diff --check`
Expected: Vite build succeeds and diff check has no errors.

- [x] **Step 2: 重建便携 EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -SkipTests`
Expected: `dist/XiaoQiBao-Portable/xiaoqibao.exe` is rebuilt and persistent directories remain.

- [x] **Step 3: 运行便携版烟测**

Run: `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1 -StartupKind cold`
Expected: window visible, API ready, 14/14 menu performance gate passes, no residual `xiaoqibao.exe`.

- [x] **Step 4: 检查 EXE 哈希和数据目录**

Run: `Get-FileHash dist/XiaoQiBao-Portable/xiaoqibao.exe -Algorithm SHA256; Get-ChildItem dist/XiaoQiBao-Portable -Directory`
Expected: hash is printed and `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, `backups` all exist.
