# Company Research Evidence Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把公司研究证据区从“原文切片卡片”收敛为一句重点结论、最多三条有效事件和可展开的其余证据。

**Architecture:** Python 解析器先过滤 F10 菜单目录、财务表格和无效片段，并为业绩预告、风险和公告生成确定性短标题；React 面板按风险/业绩/公告优先级排序，只展示前三条，其余内容折叠。原始 F10 仍保存在现有资料区和每张事件的 details 中。

**Tech Stack:** Python + pytest；React + TypeScript + Vitest；现有终端 CSS；便携 EXE 构建和烟测脚本。

## Global Constraints

- 只使用原文显式日期、关键词和数值，不生成模型猜测。
- 默认视图不超过一句综合结论和三张事件卡。
- 过滤 F10 菜单、报告期表格和装饰性分隔符。
- 中文文件使用 UTF-8 和 `apply_patch`；完成后运行乱码扫描。
- 完成后执行 `scripts/build-portable.ps1` 与 `scripts/run-portable-smoke.ps1`。

---

### Task 1: 过滤噪声并提炼事件标题

**Files:** `apps/api/src/qibao_api/gongbu/tdx_latest_tips.py`, `apps/api/tests/gongbu/test_tdx_latest_tips.py`

- [ ] 添加失败测试：截图样本只保留公告、报道和业绩预告；菜单目录和“每股收益/每股净资产”片段被过滤；业绩标题包含同比下降区间；合同公告标题包含实际动作。
- [ ] 运行 `\.venv\Scripts\python.exe -m pytest apps/api/tests/gongbu/test_tdx_latest_tips.py -q`，确认新断言失败。
- [ ] 实现 `_is_noise`、`_event_title` 和清洁摘要；无明确事件的无日期片段不进入默认有效事件，但原始 profile 保留。
- [ ] 重跑解析器测试并提交 `feat: simplify tdx evidence extraction`。

### Task 2: 简化 React 默认视图

**Files:** `apps/web/src/features/company-research/LatestTipEvidencePanel.tsx`, `apps/web/src/features/company-research/companyResearch.css`, `apps/web/src/features/company-research/CompanyResearchView.test.tsx`

- [ ] 添加失败测试：不再渲染分类筛选；显示“重点结论”；默认最多三张事件卡；超过三条显示“查看其他 X 项”；重点风险标题可见。
- [ ] 运行 `pnpm --dir apps/web test -- CompanyResearchView.test.tsx --run`，确认失败。
- [ ] 删除统计框与分类按钮，增加确定性结论条、优先级排序和折叠更多事件。
- [ ] 把事件卡压缩为日期、实际标题、单句摘要、性质标签和原文展开；正文保持易读字号。
- [ ] 重跑公司研究测试并提交 `feat: simplify company research evidence view`。

### Task 3: 全量验证和便携 EXE

**Files:** `docs/verification/2026-08-06-company-research-evidence-simplification.md`

- [ ] 运行前端 391+ 项和 API 全量测试。
- [ ] 运行 UTF-8 严格解码、乱码扫描和知识库校验。
- [ ] 停止占用旧发布目录的 `xiaoqibao.exe` 后运行 `scripts/build-portable.ps1 -SkipTests`。
- [ ] 运行 `scripts/run-portable-smoke.ps1`，记录窗口启动、API 就绪、EXE SHA-256。
- [ ] 更新验证记录和项目记忆，提交 `verify: validate simplified company research evidence`。
