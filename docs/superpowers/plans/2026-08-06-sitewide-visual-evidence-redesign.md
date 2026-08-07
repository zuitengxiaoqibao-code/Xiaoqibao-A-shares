# 一树 A 股观测台全站可视化与证据可信度 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** 用统一的真实数据可视化内核和证据状态契约，逐批升级全站页面，并通过便携 EXE 交付。

**Architecture:** 先建立共享视觉原语、ECharts 主题和证据状态渲染器，再迁移信息总览、今日研判、个股观察、公司研究和量化分析；市场专题页按菜单语义逐页绑定专属图表组合。后端继续复用既有 API 与本地通达信/腾讯/缓存来源，第三阶段才扩展已实测的 TdxQuant 只读能力。

**Tech Stack:** React 19, TypeScript 5.8, ECharts 5.6, CSS, Vitest, FastAPI, Pydantic, pytest, PyInstaller portable EXE。

## Current Progress (2026-08-07)

### 2026-08-07 continuation: quant cache observability, snapshot index and staged smoke timings

| 目标 | 状态 | 最近证据 |
|---|---|---|
| 量化候选池/触发证据缓存状态可解释 | 已完成 | API 返回各层采集时间、年龄和是否复用；前端状态栏显示“刚刚采集/复用缓存” |
| 盘中快照按股票和时间读取不再全表扫描 | 已完成 | `intraday_market_snapshot_events(symbol, observed_at, sequence)` 索引，新增查询计划回归 |
| 便携烟测拆分请求耗时 | 已完成 | smoke 输出首页、信息总览、量化策略、专业探针分别耗时 |
| 量化接口首次扫描耗时审计 | 已完成 | 真实发布目录量化请求约 6.3 秒，确认主要来自全市场日线候选扫描；30 秒缓存保留后续刷新预算 |

### 2026-08-07 continuation: non-blocking quant candidate prewarm

| 目标 | 状态 | 最近证据 |
|---|---|---|
| 量化首次候选扫描不阻塞页面 | 已完成 | 便携运行时使用单线程后台扫描；首个请求返回 `candidate_scan_state=pending`，完成后下一次轮询消费真实候选 |
| 扫描过程有明确证据状态 | 已完成 | API 新增 `candidate_scan_state/started_at/error`；前端状态栏显示后台预热中或失败原因 |
| 退出释放后台资源 | 已完成 | `QuantStrategyService.close()` 在应用 lifespan 结束时取消执行器任务 |

### 2026-08-07 continuation: professional probe correctness and diagnostics

| 目标 | 状态 | 最近证据 |
|---|---|---|
| 修复便携 smoke 的通达信专业字段探针 | 已完成 | 探针字段由非法 `Fn` 修正为契约要求的 `Fn193`，并新增回归断言 |
| 区分专业接口真实不可用原因 | 已完成 | 路由按已知安全错误类型返回可行动中文原因，不回显内部异常 |
| 重建并验证 Windows 便携 EXE | 已完成 | 隔离 smoke 与真实发布目录 smoke 均通过，专业状态保持 `unavailable` |
| 修正预交易时段情绪刷新日志 | 已完成 | `MarketSentimentWrongPhase` 只记录为预期跳过，不再附带 traceback |

### 2026-08-07 continued: bridge root-cause evidence and quant refresh budget

| 目标 | 状态 | 最近证据 |
|---|---|---|
| 确认官方 TdxQuant 初始化失败断点 | 已确认外部条件阻塞 | 直接调用 `TPythClient.dll` 返回 `ErrorId=11`；`TdxW.exe` 存在但未加载 `TPythClient.dll`，`tdxsys3.log` 未出现后台数据服务启动记录 |
| 继续保持专业字段不可用边界 | 已完成 | 未获得经验证的专业行前，`Fn/GP/BK/SC/GO` 仍返回 `unavailable`，不使用 DBF 或普通行情代理 |
| 桥接状态按实际配置端口展示 | 已完成 | 设置页与 API 不再把自定义桥接地址硬编码为 17709 |
| 减少量化策略轮询重复扫描 | 已完成 | 候选池扫描缓存 30 秒，触发证据缓存 5 秒；新增服务回归测试 |

### 持续计划与完成门槛

- [ ] 通达信客户端完成登录并启动 TdxQuant/只读服务、桥接恢复后，逐项实测 `Fn/GP/BK/SC/GO`，每个字段保存请求、响应形状、来源和时间戳证据。
- [ ] 仅将经过实测的专业字段绑定到财务、交易、板块、市场和量化专题；任何字段为空、错误包或单位不明时继续显示 `unavailable`，不生成代理值。
- [x] 用冷盘与热启动各至少三次 EXE smoke 记录窗口首帧、API 就绪和完整验证时间；当前证据已记录，Windows 冷盘扫描波动仍作为持续观察项。
- [ ] 真实专业字段恢复后，对依赖这些字段的菜单执行来源切换回归，确保缓存、实时、部分可用和不可用状态不会互相覆盖。

### 本轮继续目标

- [ ] 通达信只读桥恢复后逐字段验证 `Fn/GP/BK/SC/GO`，并将实测字段绑定到对应业务菜单。
- [x] 在不牺牲数据真实性的前提下，继续压缩首次量化候选扫描；本轮采用后台预热，禁止用未经校验的持久缓存冒充最新数据。
- [x] 累积真正冷盘与热启动各至少三次样本，区分窗口首帧、API 就绪、信息总览、量化策略和专业探针耗时。

### 2026-08-07 continuation: final EXE evidence for background prewarm

| 验收项 | 结果 |
|---|---|
| 隔离 smoke | 三次通过；窗口 `121/112/118ms`，API `2440/2421/2415ms`；量化在无真实样本时 `unavailable` |
| 真实发布 smoke | 三次通过；窗口 `325/91/62ms`，API `5590/1971/1992ms`；后台候选最终为真实 `7` 只、覆盖 `85.00%` |
| 资源释放 | 三次 smoke 后均无应用/探测进程，`17709` 未监听，持久目录全部保留 |
| 交付 EXE | `dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `3EF466C656801B4869DD9FB9D04A2E054F0633CF16F1B808A80B1A19DE56D476` |

| 目标 | 状态 | 最近证据 |
|---|---|---|
| 共享证据状态与图表原语 | 已完成 | `784400f`、`f5ef932`、`b72d456` |
| 信息总览缓存优先与启动状态 | 已完成 | `1bdcb50`、`docs/verification/2026-08-06-cache-startup-performance.md` |
| 全局可读性基线 | 已完成 | `ea2995a`；正文 14px、辅助文字 13px |
| 专题工作区语义拆分 | 已完成基础版本，第二轮语义审计已落地，持续审查 | 50 个独立定义；`DistinctMarketWorkspace.test.tsx` 19 项专题行为回归 |
| 不可用/陈旧证据诚实展示 | 持续推进 | `f5dcd65`；专题页不再冒充实时连接 |
| TdxQuant 只读深度接入 | 基础能力探测完成；官方 Python 只读回退已接入，设置页已区分客户端进程与 JSON-RPC 桥，真实专业字段持续等待桥接/数据包返回 | 设置页显示 13 类只读能力状态、客户端运行状态和桥接监听状态；专业字段严格走 `table_list`，本机桥不可达时保持 `unavailable` |
| 区间统计真实日期选择与历史窗口计算 | 已完成 | 本地日线区间接口、日期控件、逐股收益/振幅/成交额、边界回归 |
| 全站最终验收与 EXE 交付 | 本轮验收完成，后续按数据源变化持续回归 | 前端 468 项、API 1128 项、EXE 连续三次 smoke 通过 |

## 2026-08-07 增量进度

| 目标 | 状态 | 证据 |
|---|---|---|
| 真实发布数据便携 smoke | 已完成 | `run-portable-smoke.ps1 -UseReleaseData` 直接使用发布目录且不清理持久数据 |
| 发布 smoke 的通达信专业字段探针 | 已完成 | `/api/v1/tdx/local/professional` 返回真实 `unavailable` 状态和原因 |
| 本轮 API/前端/生产构建回归 | 已完成 | API `1130 passed, 1 skipped`；前端 `469 passed`；Vite 与 PyInstaller 通过 |
| 本轮 EXE 交付 | 已完成 | SHA-256 `83CD95D5E750AEBBDAF84DD6F01875144F7E3CFA75E12A34B2D5F21AD8027930` |
| 首屏 ECharts 按需加载实验 | 已完成（保留） | 首屏块约 `483KB`，ECharts 独立块约 `1.04MB`；EXE smoke 窗口 `115ms`、API `2676ms` |

## Remaining Goals

以下目标在全部验收通过前保持为持续计划，不以单个阶段完成代替项目完成：

- [x] 完成第一轮 50 个专题页的真实字段覆盖审查：缺失行情、成交额、板块字段不再转成 0；不满足必要字段的筛选、排行和强度指标不入选，页面显示 `--` / 未接入。
- [x] 完成第二轮 50 个专题页语义审计：开盘/人气/赛道/热点/AI 选股/问财/概念拥挤使用专属字段与规则；历史逐股接口未返回时明确展示证据缺口；行情主源不可用时不显示 0 值脉冲卡。
- [x] 将通达信本地只读能力扩展为可探测的行情、财务、板块、事件和公式能力，并在设置页显示能力状态。
- [x] 将已探测为 ready 的通达信能力接入对应业务字段；`get_more_info`/`get_stock_info` 已进入个股基本面与估值，`get_kzz_info` 已进入可转债条款诊断，`get_ipo_info` 已提供严格的新股/新债日历只读接口，`formula_process_mul_*` 已提供严格的公式批量只读接口并在量化分析仪表盘展示；专业数据包或接口不支持时继续保持不可用，不使用代理字段。
- [x] 完成个股观察 30 秒、公司研究 5 分钟的可见页面后台刷新，并在恢复可见时立即刷新；保留当日缓存、避免请求重叠，量化分析继续使用页面可见轮询。
- [x] 提升量化 TICK 图表的信息密度：增加 inside/slider 双层缩放导航，成交量按已验证涨跌方向使用红涨绿跌，缺失数据仍不绘制伪曲线。
- [x] 完成跨交易日缓存回归：缓存日期统一按 `Asia/Shanghai` 计算，交易日午夜边界不会误读上一日快照；通达信实时行情仅在明确返回 `MarketCapYi` 时把市值传入板块成分字段，单位不明的 `MarketValue` 保持不可用。
- [x] 增加并执行真实发布目录 smoke：量化 `partial` 时记录真实候选数量与市场风格覆盖度；专业字段状态和原因进入验收输出。
- [ ] 在本机通达信专业数据包实际可用后，继续扩展更多真实字段并逐菜单做数据源切换回归。
- [x] 增加通达信专业缓存文件的只读发现状态：只报告“已发现/等待桥接读取”，不把文件存在误报为字段可用。
- [x] 新增通达信专业数据只读契约：支持 `get_financial_data`、`get_gpjy_value`、`get_bkjy_value`、`get_scjy_value`、`get_gp_one_data` 及其按日版本；字段严格校验 `Fn/GP/BK/SC/GO` 前缀，请求统一使用官方实际参数 `table_list`，并提供 `/api/v1/tdx/local/professional` API。
- [x] 将可延后的远程转债全量同步移到可取消后台任务，健康检查不再等待网络同步；业务 `lifespan-ready` 约 656ms，窗口首帧 118ms，修正烟测健康轮询后 API 就绪 4112ms、完整验证 4460ms。
- [x] 将 `exchange_calendars` 从 API 模块导入阶段移到首次交易日查询时构造；功能保持不变，新增懒加载回归。连续三次 EXE 烟测窗口 100-111ms、API 3423-3480ms、完整验证 3982-4126ms。
- [x] 将 Edge TTS 从 API 语音服务顶层导入移到首次请求语音时懒加载，并新增子进程回归测试；本轮 API 1093 项通过、1 项按环境跳过，便携 EXE 连续三次烟测通过。
- [x] 优化便携桌面启动就绪路径：`LocalApiServer` 只等待 Uvicorn 完成 lifespan，不再重复发起自探测 HTTP 请求；通达信 fallback 全市场扫描在便携运行时延后 2 秒启动，先展示当日缓存再刷新最新数据。API 1095 项通过、1 项按环境跳过，连续三次 EXE 烟测通过。
- [x] 将便携桌面 API 线程提前到窗口创建前启动，让 Python 导入、lifespan 初始化与 WebView 建窗并行；热启动 API 就绪降至 2.69-2.74 秒，窗口首帧保持 114-119ms。
- [x] 接入官方 TdxQuant Python 专业只读适配器作为 JSON-RPC 不可达时的惰性回退；只允许 `Fn/GP/BK/SC/GO` 专业方法，异常统一为 `unavailable`，不触碰账户或交易接口。
- [x] 将 direct TdxQuant 根目录接入应用生命周期，自动发现的真实 TDX 安装目录才会进入回退候选，疑似测试目录继续排除。
- [x] 设置页增加官方 TdxQuant Python 回退的文件发现状态；`detected_only` 只表示模块/DLL 已发现，不表示专业字段已经可用。
- [x] 设置页分离显示通达信客户端进程、17709 JSON-RPC 桥和专业只读能力；客户端已运行但桥未监听时明确提示，不再把进程存在误报成桥接 ready。
- [x] 桥接端口可达但专业方法报错、返回空包或字段不完整时，先释放桥接客户端，再尝试官方 Python 只读回退；两条链路都失败时才返回 `unavailable`。
- [ ] 本机通达信进程与 `127.0.0.1:17709` 恢复后，实测 direct Python 专业字段并把经过验证的字段绑定到对应菜单；当前环境仅能确认模块可加载，不能把桥接未运行时的结果当作真实数据。
- [ ] 继续剖析 Windows 冷盘安全扫描与 PyInstaller 重型模块，保持功能完整前提下把 API 冷启动继续压缩；任何优化需用实际 EXE smoke 结果确认，不以单次热启动替代冷盘证据。
- [x] 延后 DuckDB、mootdx、pandas 和 numpy 的顶层导入；BarRepository 首次真实日线操作时才初始化 DuckDB，备份和通达信客户端保持兼容的懒加载入口。便携 smoke 改为先等待 `lifespan-ready` 日志再发起 HTTP，避免 Windows 预绑定 socket 的早期取消连接触发 `WinError 64`。
- [ ] 继续压缩冷启动等待：窗口首帧已满足 3 秒目标，热启动 API 本轮 2688ms；首次冷盘仍可能受 Windows 首次加载/安全扫描影响，后续继续审计 PyInstaller 冷磁盘读取和剩余重型模块导入，同时保留缓存优先和健康检查先可用。
- [ ] 在真实专业字段可用后，继续对财务、交易、板块、市场和量化专题逐字段做来源切换回归。
- [x] 评估首屏 ECharts 依赖拆分：按需加载不阻塞桌面窗口，图表加载期间显示动态状态；EXE smoke 未出现启动回归，保留该优化。
- [x] 延后 SQLAlchemy/SQLite 相关导入：`qibao_api.main` 冷导入不再加载 `sqlalchemy`，新增子进程回归；累计导入时间由约 817ms 降至约 626ms，减少约 191ms。
- [x] 缓存官方 TdxQuant Python 模块加载结果：同一安装路径的重复只读专业查询只初始化模块一次，仍在每次查询后关闭 `tq` 会话，避免重复导入和句柄泄漏。
- [x] 对非首屏工作区实施路由级懒加载：量化分析、公司研究、首次涨停、可转债、设置、新闻、复盘和今日研判均通过 `React.lazy + Suspense` 分离；首屏入口 JS 从约 1.69MB 降至约 1.52MB，加载期间展示明确状态。
- [x] 将本地终端目录扫描与 SQLite schema 建立并行化；不改变数据源和证据状态，便携版连续三次 smoke 的窗口首帧为 104-112ms、API 就绪为 2344-2664ms。
- [x] 修复候选池异步加载与自动首选股票的竞争条件：用户在候选池返回前点击波段股票时，自动首选不会再把 URL 改回短线首个候选；前端回归保持 454 项全绿。
- [x] 完成第二轮专题语义审计：开盘啦改为高开/低开/延续/回落检查单；人气榜使用人气分布、板块赛道使用板块强度分布；热点解读与证据链仅保留已核验且关联 A 股的新闻；AI+选股与问财选股显示各自本地规则闸门；历史未接入逐股结果显示明确接口缺口，不再渲染通用空表；行情不可用时市场脉冲不再把 0 当真实计数。
- [x] 完成日线回填第一批逐股结果：百日新高、昨涨停次日反馈已接入后端 v2 复盘快照、前端清单和分布仪表；历史字段缺失时继续显示证据缺口。
- [x] 完成区间统计真实日期选择与历史窗口计算：新增 `/api/v1/a-shares/market-overview/interval`，按起止交易日读取本地通达信日线，逐股计算区间收益、区间振幅和区间成交额；历史窗口不足、起止收盘缺失和行情源不可用时明确返回 `unavailable`，前端提供日期控件、加载状态、收益分布、强弱榜和可点击逐股表格。
- [x] 增强便携 smoke 的错误诊断：量化策略返回非 JSON 错误时保留原始 HTTP 状态和错误体，避免验证器异常掩盖真实服务故障；验证脚本回归通过。
- [x] 完成工作区、个股观察、公司研究、量化分析和全站测试的字号、颜色、红涨绿跌回归；窄屏/布局测试通过。
- [x] 本轮源代码改动后已重建便携 EXE，保留持久目录并运行真实烟测；后续每次源代码改动仍重复此验收。
- [x] 通达信桥已启用但暂不可用时，数据设置页在可见期间每 60 秒自动重探测，页面隐藏暂停、恢复可见立即探测，且不会打断手动检测或保存。
- 远程可转债全量同步不再阻塞 API lifespan：启动后后台执行，退出时显式取消并等待任务；烟测健康探测改为 1 秒轮询，避免把连接建立等待误计为 API 业务就绪时间。
- [x] 完成盘前/盘中/收盘后快照语义拆分：行情字段完整度与时间新鲜度分别使用 `quality`、`phase/freshness`；上一交易日完整快照不再显示“实时监控中”。
- [x] 完成盘前跨日缓存连续性：09:25 前允许最近 1 至 3 日的上一交易日收盘快照，开盘后严格拒绝跨日缓存，并兼容升级旧版本缓存元数据。
- [x] 统一信息总览、50 个专题工作区和量化策略的上一收盘、实时、最终和陈旧状态。
- [ ] 通达信专业插件和只读桥真实恢复后，完成 `Fn/GP/BK/SC/GO` 的逐字段实测、业务绑定和来源切换回归。
- [ ] 继续积累真正冷盘与热启动证据；不得用 Windows 文件缓存预热后的结果替代冷盘结论。

## 2026-08-06 增量记录：专题指标证据边界

- [x] 收紧信息总览专题指标的“已就绪”边界：情绪分、市场风格、风险分、热度分、复盘质量/日期、上涨/下跌家数、两市成交额、题材叠加股票和龙虎榜均在必要字段缺失或样本为空时显示 `未接入/不可用`，不再显示 `--`、`待准备` 或 `0` 作为已验证结果。
- [x] 龙虎榜证据要求至少存在一条真实上榜记录；空列表即使没有后端警告，也不会被当作可验证席位数据。
- [x] 新增 5 个边界回归场景；前端全量 71 个测试文件、453 项通过；API 1099 项通过、1 项按环境跳过；Vite 生产构建通过；乱码扫描和 `git diff --check` 通过。
- [x] 完成专题派生分数的可解释性和命名审计，页面标签已区分原始字段、确定性派生、观察性合成、部分证据和禁止代理，并展示计算口径。
- [x] 本轮已完成专题派生分数的证据标签和计算口径展示，并补充自动发现 mock/fixture 等目录的生产选择排除规则；前端/API/EXE 全量验收通过。
- [x] 通达信本地 overview 后台刷新失败改为限频日志：首次失败、错误类型变化和每 20 次失败记录一次，恢复时记录一次；避免桥接不可达时重复写完整堆栈导致日志膨胀，同时保留诊断线索。

## 2026-08-06 后续增量：启动并行化与打包实验

- `packaging/xiaoqibao.spec` 的 `noarchive=True` 实验已完成并回退。独立 `.pyc` 文件使便携目录从 1,845 个文件增加到 4,558 个，热启动仅有轻微变化，首次冷盘启动约 10.76 秒，未证明有稳定收益；最终保留 `noarchive=False`，优先控制文件数量和冷盘扫描成本。
- 桌面 GUI 路径现在先准备便携运行目录、迁移旧数据并启动 API 线程，再创建 WebView；窗口显示与 API 导入/lifespan 初始化可以重叠。服务器仍在窗口失败或退出时统一释放。
- 本轮专项桌面与冷导入测试通过；前端 71 个测试文件、449 项通过；API 1,099 项通过、1 项按环境跳过；Vite 构建和便携 EXE 构建通过。
- 本轮 EXE 烟测（串行、无端口冲突）：窗口 102/118/111ms；API `/health` 2,664/2,387/2,414ms；完整验证 3,371/3,201/3,212ms；信息总览均为 `ready`，量化策略均为 `unavailable`（真实样本不足，不虚构）。
- 当前便携 EXE SHA-256：`C6BCBED43368E286AEE03A6CA2481E967ECC66D1813DC47B2F325E13D6B38487`；持久目录 `config/data/news/cache/logs/models/exports/backups` 均保留。

## 2026-08-06 增量记录

- 继续收紧专题与量化视觉真实性边界：龙虎榜/席位缺金额、连板缺高度、复盘缺量能时不再显示 0 值；市场风格、策略、公司研究和回测空值增加明确 unavailable 状态与中性空条样式。前端 444 项、API 1089 项通过；便携 EXE 烟测窗口 125ms、API 4645ms、完整验证 5041ms，SHA-256 为 `6C510317E60A482FEE6EF905B034CE0B5D731AA96F574473839AACD909764522`。

- 已完成设置页只读能力探测：证券目录、实时行情、板块目录、扩展行情与估值、基础财务与行业、新股与新债日历、可转债条款、通达信公式计算。
- 探测只调用 JSON-RPC 只读方法，不连接券商、不调用交易接口；接口异常只保留错误类型，不回显异常原文或凭据。
- 首页实时更新失败且存在当日缓存时，启动层增加“继续使用缓存”操作，避免错误遮罩持续阻塞已有完整数据。
- 个股诊断已增加可选本地 TdxQuant 明细源：仅在设置启用且桥接返回明确字段时使用 `get_more_info`/`get_stock_info`；本地桥不可用、空响应或字段不足时自动回到既有 mootdx 财务源，估值区仍保留来源和不可用边界。
- 可转债条款诊断已增加只读 `get_kzz_info` 优先源；只有正股代码、转股价、到期日、转股起始日和剩余规模全部明确返回时才接受，否则自动回退公开条款源。
- 新增 `/api/v1/tdx/local/ipo-calendar`：仅接受明确的代码、名称、类型和申购日期，上市日/中签日缺失保持为空；错误包、空包和不完整行返回 `unavailable`。
- 新增 `/api/v1/tdx/local/formula`：仅允许 `formula_process_mul_*` 只读公式方法，量化分析仪表盘按当前标的读取明确返回的公式字段；缺失字段不转成 0，结果不可用时显示原因。
- 量化公式面板按当前分析标的每 15 秒刷新一次，切换标的或卸载页面时释放旧定时器，避免旧股票响应覆盖新股票。

## Global Constraints

- 所有用户交付通过 `dist/XiaoQiBao-Portable/xiaoqibao.exe`，不交付 HTML 或 localhost。
- A 股上涨/改善使用 `--market-up: #f04f5f`，下跌/恶化使用 `--market-down: #2fcf91`。
- 缺失、陈旧、冲突和未验证数据必须有状态，不用随机、截图静态数字或无关字段填空。
- AI 只能解释已有证据，不创建证券代码、价格、新闻事实或评分。
- 用户可见正文不低于 12px；桌面、窄屏和 390px 视口不能出现遮挡或横向溢出。
- 构建前保留 `config/data/news/cache/logs/models/exports/backups`。

### Task 1: 可视化状态与图表原语

**Files:**
- Create: `apps/web/src/shared/visualization/types.ts`
- Create: `apps/web/src/shared/visualization/chartTheme.ts`
- Create: `apps/web/src/shared/visualization/VisualPrimitives.tsx`
- Create: `apps/web/src/shared/visualization/visualization.css`
- Test: `apps/web/src/shared/visualization/VisualPrimitives.test.tsx`

**Deliverable:** 统一的 `EvidenceState`、`DataStateNotice`、`ChartPanel`、`MetricBand`、`GaugeRow`、`RankBarList` 和 `EvidenceBadge`，提供 ready/partial/stale/unavailable/error 五种状态。

### Task 2: ECharts 主题与图形工厂

**Files:**
- Modify: `apps/web/src/features/quant-analysis/QuantChart.tsx`
- Create: `apps/web/src/shared/visualization/chartOptions.ts`
- Test: `apps/web/src/shared/visualization/chartOptions.test.ts`

**Deliverable:** 统一字体、坐标轴、tooltip、零轴、涨跌色和缺失点断线配置；提供 bar-line、dual-axis、radar、heatmap、treemap、gauge、candlestick 等工厂函数。

### Task 3: 全局 CSS 基线迁移

**Files:**
- Modify: `apps/web/src/app/tokens.css`
- Modify: `apps/web/src/app/theme.css`
- Modify: `apps/web/src/app/terminal.css`
- Test: `apps/web/src/app/typography.test.ts`, `apps/web/src/app/layout-safety.test.ts`

**Deliverable:** 统一深色终端背景、边框、间距、字号、状态色和 reduced-motion；清理局部浅色和冲突的粉色上涨语义。

### Task 4: 信息总览基准页

**Files:**
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/OverviewTables.tsx`
- Modify: `apps/web/src/features/market-overview/OverviewMinuteChart.tsx`
- Modify: `apps/web/src/features/market-overview/overview.css`
- Test: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`, `apps/web/src/features/market-overview/OverviewMinuteChart.test.tsx`

**Deliverable:** 顶部指标带、指数分时、异动时间线、板块热力、热门板块/股票表统一为截图所示的高密度图形结构，保持真实数据和自动刷新。

### Task 5: 今日研判与个股观察

**Files:**
- Modify: `apps/web/src/features/decision-workbench/TodayDecisionView.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/KeySignalDashboard.tsx`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Test: corresponding existing tests plus new visual state assertions

**Deliverable:** 三阶段状态带、资金流向混合图、K 线事件索引、亮点/风险标签和来源账本统一展示。

### Task 6: 公司研究与量化分析

**Files:**
- Modify: `apps/web/src/features/company-research/ResearchVisualSummary.tsx`
- Modify: `apps/web/src/features/company-research/companyResearch.css`
- Modify: `apps/web/src/features/quant-analysis/QuantAnalysisDashboard.tsx`
- Modify: `apps/web/src/features/quant-analysis/ShortTermStrategyWorkbench.tsx`
- Test: existing company research and quant tests plus chart option assertions

**Deliverable:** 财务五维组合图、估值双轴历史、资产负债 treemap、研究仪表和策略投票仪表统一为真实数据状态驱动的面板。

### Task 7: 市场专题页语义迁移

**Files:**
- Modify: `apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`
- Modify: `apps/web/src/features/market-overview/workspaces/workspaceRegistry.ts`
- Test: `DistinctMarketWorkspace.test.tsx`, `workspaceRegistry.test.ts`

**Deliverable:** 每个菜单绑定独立图形组合：涨停/连板/炸板、竞价、龙虎榜、突破、低位放量、热点/复盘等不再重复同一模板。

### Task 8: TdxQuant 只读增强

**Files:**
- Modify: `apps/api/src/qibao_api/gongbu/tdx_local_overview.py`
- Create: `apps/api/src/qibao_api/gongbu/tdx_local_professional.py`
- Modify: `apps/api/src/qibao_api/contracts/tdx_local.py`
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/routes/tdx_local.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/web/src/features/data-settings/LocalSourceSettingsSection.tsx`
- Test: `apps/api/tests/gongbu/test_tdx_local_overview.py`, `apps/api/tests/gongbu/test_tdx_local_professional.py`, `apps/api/tests/routes/test_tdx_local.py` and data settings tests

**Deliverable:** 能力探测、`get_more_info`/`get_stock_info`/`get_ipo_info`/`get_kzz_info`/`formula_process_mul_*` 与专业 `Fn/GP/BK/SC/GO` 表格只读接入；专业数据包缺失时返回明确降级，不碰交易接口。

### Task 9: EXE 交付与全站验收

**Files:**
- Modify: `docs/verification/2026-08-06-sitewide-visual-evidence-redesign.md`

**Commands:**
- `pnpm --dir . --filter "@qibao/web" test`
- `.venv/Scripts/python.exe -m pytest apps/api/tests -q`
- `pnpm --dir . --filter "@qibao/web" build`
- `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -SkipTests`
- `powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1`

**Deliverable:** 便携 EXE、测试证据、SHA-256 和持久目录保留记录。

## 2026-08-07 量化后台预热动态状态

- [x] 后台候选扫描在前端显示真实的动态等待状态：不伪造百分比，使用无确定进度条动画并显示已运行秒数。
- [x] 动态状态继续遵循页面隐藏暂停和恢复刷新规则。
- [x] 新增组件回归，验证 `pending` 状态为无确定进度、没有 `aria-valuenow`，并随时间刷新已运行秒数。
- [x] 只有在后端扫描器能够提供真实阶段/已处理数量时，才增加确定百分比；在此之前保持不确定进度，避免把估算当真实采集进度。

## 2026-08-07 量化扫描真实阶段进度

- [x] 后端返回 `candidate_scan_phase`、`candidate_scan_processed`、`candidate_scan_total`，区分历史读取、因子计算、排序、就绪和失败。
- [x] 因子计算阶段只报告扫描器实际提供的 `processed/total`；历史读取和排序阶段继续使用无确定百分比的动态等待。
- [x] 前端在有真实计数时显示“因子扫描 n/m · x%”并同步 `aria-valuenow`；无计数时不显示伪造百分比。
- [x] API/前端回归、生产构建和两组便携 EXE smoke 已通过；真实发布目录获得 7 只真实候选、85% 市场风格覆盖，隔离数据不足时保持 unavailable。

## 2026-08-07 桌面启动真实里程碑提示

- [x] 新增启动阶段解析器，只识别 API 已写入日志的真实里程碑，不按时间或固定步长推测完成度。
- [x] 启动页在 API 等待期间展示本地数据源、数据库、仓库、市场服务、历史校准和 API 初始化阶段；阶段更新由独立线程读取，结束时及时释放。
- [x] 增加启动里程碑解析、脚本生成和窗口等待期间更新回归；便携 EXE 冒烟未出现启动回归。
- [x] 将 Uvicorn 字符串应用导入显式化并记录 `api-app-imported import_ms`，用于区分模块导入和生命周期初始化耗时。
