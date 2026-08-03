# 公司研究工作台实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增真实证据驱动的“公司研究”一级菜单，支持多年财务、F10摘录、同行比较、反方审查与估值观察。

**Architecture:** 后端增加新浪三表归一化源、通达信 F10 文本源和 `CompanyResearchService`，通过新路由返回稳定契约；前端增加独立研究工作台，比较池只负责加载最多四个真实研究响应，不复用短线分数。

**Tech Stack:** FastAPI、Pydantic、httpx、mootdx、React 18、TypeScript、Vitest、现有深色终端 CSS、便携 PyInstaller EXE。

## Global Constraints

- 所有数据必须来自真实数据源或现有冻结证据，禁止随机数、占位行情和伪造财报。
- 缺失证据显示“未评分/无法核验”，不得补 50 分。
- 用户只通过 `dist/XiaoQiBao-Portable/xiaoqibao.exe` 交付和验收。
- 中文文件使用 UTF-8 与 `apply_patch` 修改。
- 不改动可转债独立区域，不把公司研究混入短线量化结论。

---

### Task 1: 新增研究数据契约和财务解析器

**Files:**
- Create: `apps/api/src/qibao_api/contracts/company_research.py`
- Create: `apps/api/src/qibao_api/gongbu/sina_financials.py`
- Test: `apps/api/tests/gongbu/test_sina_financials.py`
- Test: `apps/api/tests/contracts/test_company_research.py`

**Interfaces:**
- `SinaFinancialHistorySource.fetch(symbol: str, limit: int = 20) -> FinancialHistory`
- `parse_sina_report(payload: Mapping[str, Any], report_type: str, limit: int) -> tuple[FinancialReportRow, ...]`
- `CompanyResearchResponse` 包含 `symbol`、`name`、`generated_at`、`financial_history`、`dimensions`、`score`、`counter_case`、`valuation`、`sources`。

- [ ] 写失败测试：新浪 `report_list` 能按报告期合并三表；无法识别科目保持 `None`；年度序列只选择 12 月 31 日报告期。
- [ ] 运行 `pytest apps/api/tests/gongbu/test_sina_financials.py apps/api/tests/contracts/test_company_research.py -q`，确认新类型和解析函数尚不存在。
- [ ] 实现别名映射：收入、营业成本、归母净利润、经营现金流、资产、负债、权益；所有原始数值解析失败时返回 `None`。
- [ ] 实现衍生指标：毛利率、现金流/净利润、资产负债率、三年 CAGR，并为每个值保留报告期和来源。
- [ ] 运行定向测试，确认通过。

### Task 2: 新增 F10 源和公司研究服务

**Files:**
- Create: `apps/api/src/qibao_api/gongbu/tdx_company_profile.py`
- Create: `apps/api/src/qibao_api/a_shares/company_research.py`
- Create: `apps/api/tests/gongbu/test_tdx_company_profile.py`
- Create: `apps/api/tests/a_shares/test_company_research.py`

**Interfaces:**
- `TdxCompanyProfileSource.fetch(symbol: str) -> CompanyProfileEvidence`
- `CompanyResearchService.get(symbol: str, as_of: date | None = None) -> CompanyResearchResponse`

- [ ] 写失败测试：三类 F10 文本分别清理空白并截断到 1200 字符；单类失败不影响其他类别。
- [ ] 写失败测试：研究分只对可用维度加权，覆盖度低于 60% 时为 `None`；十项反方检查只能返回 `clear/triggered/unavailable`。
- [ ] 运行定向测试确认失败。
- [ ] 使用现有 `create_tdx_client` 读取 `公司概况`、`行业分析`、`最新提示`，不把文本内容转成未经证实的数值。
- [ ] 使用 `asyncio.to_thread` 与现有诊断服务、财务源并发取数；任何单源失败转换为响应内的不可用证据。
- [ ] 实现评分：增长15、盈利10、现金流15、资产负债10、估值15，其余维度未评分；按覆盖度归一化后再扣风险分。
- [ ] 实现十项反方审查和来源清单，确保至少返回十个审查槽位。
- [ ] 运行定向测试确认通过。

### Task 3: 路由、依赖和应用状态接入

**Files:**
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/routes/research.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Test: `apps/api/tests/routes/test_company_research.py`

**Interfaces:**
- `GET /api/v1/a-shares/{symbol}/company-research`
- Query: `as_of: date | None`
- Response: `CompanyResearchResponse`

- [ ] 写路由失败测试：有效股票返回研究契约；非法代码返回 422；服务不可用返回 503 且不伪造空分数。
- [ ] 在应用 lifespan 创建 `SinaFinancialHistorySource`、`TdxCompanyProfileSource`、`CompanyResearchService`，并在 shutdown 阶段关闭 HTTP 客户端。
- [ ] 添加 `get_company_research_service` 依赖和路由错误映射。
- [ ] 运行路由定向测试确认通过。

### Task 4: 前端公司研究 API、类型和工作台

**Files:**
- Create: `apps/web/src/features/company-research/types.ts`
- Create: `apps/web/src/features/company-research/api.ts`
- Create: `apps/web/src/features/company-research/CompanyResearchView.tsx`
- Create: `apps/web/src/features/company-research/companyResearch.css`
- Test: `apps/web/src/features/company-research/CompanyResearchView.test.tsx`
- Test: `apps/web/src/features/company-research/api.test.ts`

**Interfaces:**
- `loadCompanyResearch(symbol: string, asOf?: string, signal?: AbortSignal): Promise<CompanyResearchResponse>`
- `CompanyResearchView({ load, search, selectedSymbol, onOpenAShare })`

- [ ] 写失败测试：页面显示三个顶部仪表、九维矩阵、财务趋势、同行标签和十项反方审查。
- [ ] 写失败测试：未评分维度显示不可用原因，不出现“买入/卖出/目标价”指令。
- [ ] 写失败测试：同行最多四只，切换股票时旧响应不能覆盖新股票。
- [ ] 运行 Vitest 定向测试确认失败。
- [ ] 使用现有 `searchAShareInstruments` 选择公司；比较池加载多个真实响应并显示单只失败原因。
- [ ] 使用 JetBrains Mono + Orbitron、现有终端颜色和高可读字号；研究账本证据印章作为页面签名元素。
- [ ] 运行定向测试确认通过。

### Task 5: 一级菜单与 Dashboard 路由接入

**Files:**
- Modify: `apps/web/src/features/beginner-shell/BeginnerNavigation.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.test.tsx`
- Modify: `apps/web/src/app/theme.css`

- [ ] 写失败测试：新手/专家模式均出现“公司研究”；路径为 `/company-research`；保留 `symbol` 查询参数。
- [ ] 写失败测试：从信息总览或个股观察跳转后，公司研究接收当前股票。
- [ ] 运行 Dashboard 定向测试确认失败。
- [ ] 添加 `BeginnerView` 类型、导航项、App loader 和 Dashboard 分支。
- [ ] 调整导航间距和响应式布局，确保不破坏可转债独立入口。
- [ ] 运行 Dashboard 和公司研究全套前端测试。

### Task 6: 全量验证和便携 EXE

**Files:**
- Verify: `apps/api/src/qibao_api/contracts/company_research.py`
- Verify: `apps/api/src/qibao_api/gongbu/sina_financials.py`
- Verify: `apps/api/src/qibao_api/a_shares/company_research.py`
- Verify: `apps/web/src/features/company-research/*`
- Build: `scripts/build-portable.ps1`
- Smoke: `scripts/run-portable-smoke.ps1`

- [ ] 运行后端全量 pytest 和前端全量 Vitest。
- [ ] 运行前端生产构建。
- [ ] 对所有新增/修改中文文件执行严格 UTF-8、替换字符/重复问号扫描和 `git diff --check`。
- [ ] 重建便携 EXE，核对并保留 `config/data/news/cache/logs/models/exports/backups`。
- [ ] 运行真实 EXE 烟测，并额外请求 `/api/v1/a-shares/600519/company-research` 验证接口状态和不可用降级。
- [ ] 计算 EXE SHA-256，更新项目长期记忆，确认无残留便携进程。
