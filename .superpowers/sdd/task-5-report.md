# Task 5 Report: 公司研究证据图谱与事件影响

## 实现摘要

- 新增公司研究有向证据图：以原始证据、事实、推导、判断和不可用结论为节点，使用 `supports` / `derives_from` 有向边连接；模型校验未知节点、重复边、自环、环路及不可用节点伪造证据。
- `CompanyResearchService` 在确定性研究结论后生成 `evidence_graph`；展示型证据图不改变既有公司研究语义哈希，并兼容字段新增前后的历史快照校验口径。
- 新增新闻事件影响契约、计算服务和 API：`GET /api/v1/news/events/{event_id}/impact`。报告使用引用中的首次发布时间、事件类型、真实关联股票/板块和本地真实日线计算 1/3/5/20 个交易日收益。
- 重复新闻通过 `NewsRepository` 聚类显式标注；关联置信度低于 0.70、待复核/拒绝关联、缺少基准日线或完整收益窗口均保持 `partial` / `unavailable`，不填充代理值。
- 板块缺少可验证的板块/指数日线时生成显式 `unavailable` 目标，不使用成分股均值代替板块收益。
- 公司研究页新增证据图面板；新闻事件证据抽屉新增按需影响复盘。正收益使用市场上涨红色，负收益使用市场下跌绿色，缺失窗口显示“不可用”。
- 应用入口已接入事件影响请求；FastAPI 生命周期注册 `EventImpactService`，桌面 EXE 构建包含新增路由和前端。

## 提交 SHA

`19307cb97525876a613d1f93cb1ab7bf1fdb2e02`

提交：`feat: add evidence graph and news event impact review`

## TDD 红灯记录

### 后端 RED

命令：

```powershell
& '.venv/Scripts/python.exe' -m pytest tests/a_shares/test_evidence_graph.py tests/a_shares/test_event_impact.py -q
```

原始结果：

```text
ERROR tests/a_shares/test_evidence_graph.py
ModuleNotFoundError: No module named 'qibao_api.a_shares.evidence_graph'
ERROR tests/a_shares/test_event_impact.py
ModuleNotFoundError: No module named 'qibao_api.a_shares.event_impact'
2 errors in 0.41s
```

### 前端 RED

命令：

```powershell
npm test -- --run src/features/company-research/ResearchEvidenceGraph.test.tsx src/features/news-intelligence/EventImpactPanel.test.tsx
```

原始结果：

```text
Failed to resolve import "./ResearchEvidenceGraph"
Failed to resolve import "./EventImpactPanel"
Test Files 2 failed (2)
```

## 验证命令与原始结果

### API 全量测试

```powershell
& '.venv/Scripts/python.exe' -m pytest -q
```

```text
1409 passed, 1 skipped, 5 warnings in 42.90s
```

5 个 warning 均来自 `exchange_calendars` / pandas timedelta 的第三方 DeprecationWarning。

### 新增契约、边界和历史兼容聚焦测试

```powershell
& '.venv/Scripts/python.exe' -m pytest tests/a_shares/test_evidence_graph.py tests/a_shares/test_event_impact.py tests/a_shares/test_company_research_versions.py -q
```

```text
10 passed in 0.74s
```

### Ruff

```powershell
& '.venv/Scripts/python.exe' -m ruff check src tests/a_shares/test_evidence_graph.py tests/a_shares/test_event_impact.py
```

```text
All checks passed!
```

### Web 全量测试

```powershell
npm test -- --run
```

```text
Test Files 117 passed (117)
Tests 663 passed (663)
Duration 19.78s
```

### Web 关键集成复测

```powershell
npm test -- --run src/features/dashboard/Dashboard.test.tsx src/features/news-intelligence/NewsIntelligenceView.test.tsx src/features/company-research/CompanyResearchView.test.tsx src/features/company-research/ResearchEvidenceGraph.test.tsx src/features/news-intelligence/EventImpactPanel.test.tsx
```

```text
Test Files 5 passed (5)
Tests 58 passed (58)
Duration 6.82s
```

### TypeScript / Vite 生产构建

```powershell
npm run build
```

```text
tsc -b && vite build
2280 modules transformed
built in 4.56s
```

Vite 保留既有大 chunk 警告；构建退出码为 0。

### UTF-8 / diff 检查

```powershell
rg -n "�" <本任务修改的 API 与 Web 源文件>
git diff --check
```

```text
无匹配；git diff --check 通过。
```

### 便携 EXE 构建与 smoke

```powershell
./scripts/build-portable.ps1 -SkipTests
./scripts/run-portable-smoke.ps1 -Port 18805 -UseReleaseData -ReleaseRootOverride <staged-release>
```

```text
Portable smoke passed; window visible in 360ms; API ready in 6648ms;
verification completed in 22641ms; overview ready coverage=99.94%;
quant strategy partial (candidates=12; coverage=85.00%);
company research partial (symbol=600519; coverage=0.65; counter_case=10);
tdx professional unavailable.
```

现有便携 EXE 正由用户打开（PID 34308），构建脚本未覆盖、关闭或控制该进程，而是生成 staged release：

`D:\Users\90090\Documents\金融财经\.worktrees\a-share-daily-research\dist\XiaoQiBao-Portable-staged-85d0da80e8784354887506020a08e61a\XiaoQiBao-Portable\xiaoqibao.exe`

该 staged release 将在现有窗口退出后的下次启动自动应用。smoke 仅启动并结束 staged EXE 测试实例，未启动、关闭或控制通达信。

## 已知限制

- 事件收益以首次发布时间为锚点：盘中发布使用前一交易日收盘为基准，收盘后发布使用当日收盘为基准；本地日线不足时相应 1/3/5/20 日窗口保持 `unavailable`。
- 当前本地仓库没有经过同一口径验证的板块/指数日线，因此板块目标只展示关联和 `unavailable`，不以成分股平均收益作为代理值。
- 重复标记依赖已冻结的 `NewsRepository` 聚类；尚未入库或未聚类的外部转载无法在当前点时报告中推断为重复。
- 现有 live release 因用户正在使用而未覆盖；已完成 staged EXE smoke，自动替换将在用户正常退出后下一次启动发生。

## 控制器审查修复

- 事件影响面板不再直接显示内部限制码；1/3/5/20 日窗口、关联状态和板块缺口均显示中文原因，未知内部码安全降级为“状态原因待核验”。
- 切换或关闭新闻事件时立即清空上一事件的影响报告，并以请求版本隔离迟到响应，避免旧结果挂到新事件。
- 新增事件影响 API 路由契约测试，覆盖响应模型与中文 404 错误。
- 新增面板文字由 12px 提升到 13px，保留紧凑布局并改善可读性。
- 控制器聚焦复测：API 30 项、Web 33 项、事件切换与限制码专项 18 项通过；Ruff 通过。最终全量与 EXE 验收仍留到 v9 全部任务完成后统一执行。
