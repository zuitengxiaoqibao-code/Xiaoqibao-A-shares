# Company Research Evidence Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将通达信 F10 的“最新提示”整理为可核验的事件摘要、分类卡片和可展开原文，并消除公司研究页面中的重复与拥挤排版。

**Architecture:** API 在 `TdxCompanyProfileSource` 中保留原始字段，同时通过纯函数解析器输出 `latest_tip_items`；公司研究服务用这些事件生成“未来催化”简短摘要。React 页面只消费结构化事件，渲染摘要条、分类标签、事件卡片和 `details` 原文证据，不在浏览器端重新解释原始文本。

**Tech Stack:** Python 3 + Pydantic + pytest；React + TypeScript + Vitest + Testing Library；现有 CSS 终端主题；PowerShell 便携构建与烟测脚本。

## Global Constraints

- 所有摘要必须来自 F10 原文中的显式日期、关键词和数值，不使用推测或虚假模拟数据。
- 保留来源、观察时间和事件原文，解析失败时显示“原文待整理”。
- 中文文件使用 UTF-8 和 `apply_patch` 修改，修改后执行乱码扫描。
- 用户只通过 Windows EXE 验收；完成后执行 `scripts/build-portable.ps1` 与 `scripts/run-portable-smoke.ps1`。
- 便携版重建时保留 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。

---

### Task 1: 建立 F10 最新提示事件解析器

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/tdx_latest_tips.py`
- Create: `apps/api/tests/gongbu/test_tdx_latest_tips.py`

**Interfaces:**
- Produces `parse_latest_tips(text: str | None, *, source: str, observed_at: datetime | None) -> tuple[LatestTipItem, ...]`.
- `LatestTipItem` 是不可变 Pydantic 模型，字段为 `id`, `category`, `title`, `date`, `tone`, `summary`, `source`, `observed_at`, `raw_text`。

- [ ] **Step 1: Write failing parser tests**

覆盖：日期 `2026-08-05 16:42` 提取；“预告/净利润”归入“业绩预告”且为 `risk`；“签署协议/中标”归入“公告与合同”；“减持/质押/诉讼/风险”归入“风险提醒”；未识别片段进入“其他”和 `unknown`；空文本返回空元组；每条 `raw_text` 非空。

- [ ] **Step 2: Run parser tests and verify the expected missing-parser failure**

Run: `python -m pytest apps/api/tests/gongbu/test_tdx_latest_tips.py -q`

Expected: FAIL because `tdx_latest_tips` and `parse_latest_tips` do not exist.

- [ ] **Step 3: Implement the minimal deterministic parser**

先按 `●`、`◆`、`|`、连续空白和显式“最新提示/最新公告/业绩预告”边界切段；用正则提取 ISO 日期；按关键词映射分类和色调；标题取分类关键词附近的短句，摘要限制为 220 字；使用 SHA-256(source + raw_text + date) 生成稳定 ID；不匹配的片段保留原文并标记“原文待整理”。

- [ ] **Step 4: Run parser tests and verify they pass**

Run: `python -m pytest apps/api/tests/gongbu/test_tdx_latest_tips.py -q`

Expected: all parser tests PASS.

- [ ] **Step 5: Commit the parser**

Run: `git add apps/api/src/qibao_api/gongbu/tdx_latest_tips.py apps/api/tests/gongbu/test_tdx_latest_tips.py; git commit -m "feat: parse tdx latest tips into evidence events"`

### Task 2: 扩展 API 合约并接入公司研究服务

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/company_research.py`
- Modify: `apps/api/src/qibao_api/gongbu/tdx_company_profile.py`
- Modify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Modify: `apps/api/tests/contracts/test_company_research.py`
- Modify: `apps/api/tests/gongbu/test_tdx_company_profile.py`
- Modify: `apps/api/tests/a_shares/test_company_research.py`

**Interfaces:**
- Adds `LatestTipItem` and `CompanyProfileEvidence.latest_tip_items: tuple[LatestTipItem, ...] = ()`.
- Adds `summarize_latest_tips(items) -> str` returning counts such as `已识别 3 项事件：催化 1 · 中性 1 · 风险 1`.

- [ ] **Step 1: Add failing contract/service tests**

验证 profile 的 `latest_tip_items` 可序列化；F10 source 返回结构化事件；公司研究的 `catalysts` 维度摘要只包含事件计数，不重复整段 `latest_tips`；空事件返回“无可核验催化证据”。

- [ ] **Step 2: Run targeted API tests and verify failure**

Run: `python -m pytest apps/api/tests/contracts/test_company_research.py apps/api/tests/gongbu/test_tdx_company_profile.py apps/api/tests/a_shares/test_company_research.py -q`

Expected: FAIL on missing `latest_tip_items` and old catalyst summary.

- [ ] **Step 3: Implement contract and service integration**

`TdxCompanyProfileSource.fetch` 在清洗 `latest_tips` 后调用 `parse_latest_tips`；不可用 profile 使用空元组；`CompanyResearchService._dimensions` 使用事件计数和色调计数生成简短摘要；所有现有构造点显式传入或依赖默认空元组。

- [ ] **Step 4: Run targeted API tests and verify they pass**

Run: `python -m pytest apps/api/tests/contracts/test_company_research.py apps/api/tests/gongbu/test_tdx_company_profile.py apps/api/tests/a_shares/test_company_research.py -q`

Expected: all targeted API tests PASS.

- [ ] **Step 5: Commit API integration**

Run: `git add apps/api/src apps/api/tests; git commit -m "feat: expose structured company research evidence"`

### Task 3: React 事件摘要工作台

**Files:**
- Modify: `apps/web/src/features/company-research/types.ts`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Modify: `apps/web/src/features/company-research/companyResearch.css`
- Modify: `apps/web/src/features/company-research/CompanyResearchView.test.tsx`

**Interfaces:**
- `CompanyProfileEvidence.latest_tip_items` mirrors the API contract.
- `EvidenceTimeline` receives `LatestTipItem[]` and renders category filters, event cards and expandable raw evidence.

- [ ] **Step 1: Add failing component tests**

验证：催化维度出现“已识别 3 项事件”；证据卡出现分类标签和事件标题；点击分类后只显示对应事件；`查看原始证据` 展开 raw text；空数据显示“通达信 F10 未返回最新提示”；页面不再重复显示整段 latest tips。

- [ ] **Step 2: Run the component test and verify the expected failure**

Run: `npm --prefix apps/web test -- CompanyResearchView.test.tsx --run`

Expected: FAIL because `EvidenceTimeline` and new rendering are absent.

- [ ] **Step 3: Implement typed evidence timeline**

新增纯展示组件和 `useState` 分类筛选；默认全部；摘要条计算总数、最近日期和风险数；事件卡用 `tone` 和 `category` class；原文使用原生 `<details>`，无数据和解析失败状态使用明确提示；将 profile 的“最新提示”改为摘要 + 折叠原文，避免与事件卡重复。

- [ ] **Step 4: Update responsive visual system**

在 `companyResearch.css` 增加 `.evidence-timeline`, `.evidence-summary`, `.evidence-filter`, `.evidence-event`, `.evidence-raw` 等样式；正文 14px，标题 15–16px；桌面 3 列，小屏 1 列；保持终端颜色变量和 reduced-motion 兼容。

- [ ] **Step 5: Run component tests and verify green**

Run: `npm --prefix apps/web test -- CompanyResearchView.test.tsx --run`

Expected: all CompanyResearchView tests PASS.

- [ ] **Step 6: Commit web evidence workbench**

Run: `git add apps/web/src/features/company-research; git commit -m "feat: redesign company research evidence timeline"`

### Task 4: 全量验证、便携 EXE 重建与记录

**Files:**
- Create: `docs/verification/2026-08-06-company-research-evidence-layout.md`
- Modify: relevant durable project memory card only after verification.

- [ ] **Step 1: Run frontend and API full test suites**

Run: `npm --prefix apps/web test -- --run` and `python -m pytest apps/api/tests -q`

Expected: no failures; record counts and any intentional skips.

- [ ] **Step 2: Run UTF-8 and mojibake scans**

Run: `python -c "from pathlib import Path; files=[Path('apps/web/src/features/company-research/CompanyResearchView.tsx'),Path('apps/web/src/features/company-research/companyResearch.css'),Path('apps/api/src/qibao_api/gongbu/tdx_latest_tips.py')]; [b.decode('utf-8') for f in files for b in [f.read_bytes()]]; print('utf8 ok')"` and `rg -n "�|锟斤拷|\?\?\?" apps/web/src/features/company-research apps/api/src/qibao_api/gongbu`

Expected: UTF-8 check passes and no mojibake matches.

- [ ] **Step 3: Rebuild portable EXE while preserving persistent directories**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`

Before/after the build, preserve `dist/XiaoQiBao-Portable/{config,data,news,cache,logs,models,exports,backups}`.

- [ ] **Step 4: Run the actual EXE smoke test**

Run: `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1 -ExecutablePath dist/XiaoQiBao-Portable/xiaoqibao.exe`

Expected: EXE launches, first screen renders, and smoke test exits successfully.

- [ ] **Step 5: Record evidence and commit verification**

Write test counts, smoke result, EXE path and SHA-256 to `docs/verification/2026-08-06-company-research-evidence-layout.md`; run `git diff --check`; commit with `git commit -m "verify: validate company research evidence layout"`.
