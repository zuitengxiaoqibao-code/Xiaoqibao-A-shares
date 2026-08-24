# 监控中心提醒测试与菜单顺序 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在监控中心提供真实语音/飞书测试反馈，修复规则卡片操作按钮对齐，并调整监控中心菜单位置。

**Architecture:** 复用现有语音合成和飞书测试 API；前端只负责调用真实通道、播放语音并把后端/浏览器结果翻译成中文。卡片操作区通过 CSS 网格固定底部对齐，导航继续使用同一平铺 entries 数组。

**Tech Stack:** React 19、TypeScript、Vitest、FastAPI、pytest、CSS、便携 Windows EXE。

## Global Constraints

- 不暴露飞书 webhook、密钥或其它凭据。
- 没有真实配置时必须显示“未配置”，不能伪造成功。
- 红涨绿跌、中文提示和现有监控中心视觉系统保持不变。
- 不控制通达信、鼠标或桌面。

### Task 1: Web 回归测试先行

**Files:**
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.test.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.test.tsx`

- [ ] 增加测试：点击“测试语音提醒”调用 `/api/v1/speech/synthesize`，收到音频后显示“语音测试已完成”。
- [ ] 增加测试：飞书未配置时按钮不可用；配置时调用 `/api/v1/monitor-center/notification-settings/test` 并显示后端消息。
- [ ] 更新导航断言，确认“历史复盘”下一项为“监控中心”，“监控中心”下一项为“数据设置”。
- [ ] 先运行两个定向测试，确认新增断言因界面尚未实现而失败。

### Task 2: 监控中心提醒测试实现

**Files:**
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`

- [ ] 增加 `testVoice` 状态和 `testVoice` 函数，使用 `fetch('/api/v1/speech/synthesize', { method: 'POST', body: JSON.stringify({ text: '一树 A 股观测台监控语音测试，提醒通道正常。' }) })` 获取 Blob。
- [ ] 创建 `Audio` 播放对象，监听 `onended`、`onerror`，统一释放 object URL；成功显示“语音测试已完成”，失败显示具体中文原因。
- [ ] 在监控中心顶部渲染“提醒通道测试”区域，两个按钮独立显示加载状态和结果。
- [ ] 飞书测试继续调用现有测试接口，成功、未配置和失败均保留中文反馈。

### Task 3: 菜单和规则卡片布局

**Files:**
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.test.tsx`
- Modify: `apps/web/src/features/monitor-center/MonitorCenterView.tsx`
- Modify: `apps/web/src/app/theme.css`

- [ ] 将 entries 中 `monitor_center` 移到 `history` 后、`settings` 前。
- [ ] 规则卡片保持左侧可点击摘要，右侧操作区增加稳定的 `monitor-rule-actions` 结构；状态、暂停/恢复、停止删除按钮在卡片底部同线。
- [ ] 为模板卡片操作区设置相同的最小高度，避免说明文字长度不同导致按钮上下错位；窄屏使用现有响应式规则整块换行。

### Task 4: 验证和交付

- [ ] 运行监控中心 Web 定向测试、导航定向测试、API 通知和语音路由测试。
- [ ] 运行 Web 生产构建、UTF-8/乱码扫描、`git diff --check`。
- [ ] 执行 `scripts/build-portable.ps1`，保留 `config/data/news/cache/logs/models/exports/backups`。
- [ ] 执行 `scripts/run-portable-smoke.ps1 -UseReleaseData -StartupKind hot` 和发布质量门禁。
- [ ] 更新验证文档和项目记忆，提交源码与文档。
