# 一树品牌改名 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将用户可见品牌统一为“一树-A股观测台”和“一树电子商务-A股观测台”，并在侧栏底部增加公司全称。

**Architecture:** 只修改展示文案和对应测试，不改内部可执行文件名、数据目录、单实例 ID 或日志标识。React 负责导航品牌与公司名称，Python 桌面层负责启动壳和窗口标题。

**Tech Stack:** React、TypeScript、Vitest、Python、pytest、pywebview、FastAPI、PowerShell 构建脚本。

## Global Constraints

- 左侧品牌名必须为 `一树-A股观测台`。
- 软件标题必须为 `一树电子商务-A股观测台`。
- 公司名称必须为 `上海一树电子商务有限公司`，位于“只做观察与风险提示”上方。
- 保留 `xiaoqibao.exe`、`XiaoQiBao-Portable` 和既有持久目录名称。
- 中文文件使用 UTF-8，并在完成后执行乱码扫描。

---

### Task 1: 锁定导航品牌与公司名称

**Files:**
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.test.tsx`
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`

**Interfaces:**
- Consumes: `BeginnerNavigation` 现有渲染结构。
- Produces: 新品牌名与公司名称 DOM 文案。

- [ ] **Step 1: Write the failing test**

增加断言，验证“一树-A股观测台”“上海一树电子商务有限公司”和“只做观察与风险提示”的顺序。

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --filter @qibao/web test -- BeginnerNavigation.test.tsx`

Expected: FAIL，因为新品牌和公司名称尚未渲染。

- [ ] **Step 3: Write minimal implementation**

替换品牌 `<strong>` 文案，并在免责声明前增加公司名称元素。

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --filter @qibao/web test -- BeginnerNavigation.test.tsx`

Expected: PASS。

### Task 2: 统一桌面窗口和启动页标题

**Files:**
- Modify: `apps/api/tests/desktop/test_window.py`
- Modify: `apps/api/tests/desktop/test_entrypoint.py`
- Modify: `apps/api/tests/desktop/test_instance.py`
- Modify: `apps/api/src/qibao_desktop/window.py`
- Modify: `apps/api/src/qibao_desktop/entrypoint.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/web/index.html`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `README.md`

**Interfaces:**
- Consumes: pywebview 窗口标题、启动 HTML 和 FastAPI 标题。
- Produces: 统一的新软件名称。

- [ ] **Step 1: Write the failing tests**

把桌面测试期望值改为 `一树电子商务-A股观测台`，并验证启动 HTML 使用新名称。

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest apps/api/tests/desktop/test_window.py apps/api/tests/desktop/test_entrypoint.py apps/api/tests/desktop/test_instance.py -q`

Expected: FAIL，因为生产代码仍使用旧标题。

- [ ] **Step 3: Write minimal implementation**

替换窗口标题、启动页、重复启动查找、API 标题、HTML 标题、语音文案和 README 品牌标题。

- [ ] **Step 4: Run focused tests**

Run: `.venv/Scripts/python.exe -m pytest apps/api/tests/desktop/test_window.py apps/api/tests/desktop/test_entrypoint.py apps/api/tests/desktop/test_instance.py -q`

Expected: PASS。

### Task 3: 完整验证和 EXE 交付

**Files:**
- Modify: `docs/verification/2026-08-03-yishu-brand-rename.md`

**Interfaces:**
- Consumes: 修改后的前后端源码和现有构建脚本。
- Produces: 重建并烟测通过的便携 EXE。

- [ ] **Step 1: Run full tests and build**

Run: `pnpm --filter @qibao/web test -- --reporter=dot`

Run: `.venv/Scripts/python.exe -m pytest -q`

Run: `pnpm --filter @qibao/web build`

- [ ] **Step 2: Run copy and encoding scans**

扫描用户界面旧中文品牌、UTF-8 解码错误和乱码特征。

- [ ] **Step 3: Rebuild portable EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`

- [ ] **Step 4: Smoke-test rebuilt EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1`

- [ ] **Step 5: Record verification and commit**

记录测试数量、启动时间、EXE 路径和 SHA-256，并提交本轮改名。

