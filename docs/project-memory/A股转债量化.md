---
type: project-memory
status: confirmed
updated: 2026-08-12
project_path: "D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research"
sources: ["task:019f59b1-db6e-78f2-9b0f-9c46e36657f1", "task:019fd5ca-cbff-7760-8cf4-af3d778634a2", "task:019fd5d1-36ec-7713-98bc-89eabd37b736", "task:019fd5fc-ed46-7642-9994-0fbcd2b804c1", "task:019fd5fd-fb66-73e3-ba52-437912b0ecf9", "task:019fd4ab-859f-7462-842f-87bd5cdb247e", "git:8ae202d", "git:667838a", "git:7efbe73", "github:10e4345507203e6baee0e4d55b8c58efd485d5a5"]
tags: [project-memory, quant, a-share, convertible-bond]
---

# A 股转债量化

## 目标

面向新手的 A 股与可转债研究辅助软件，覆盖盘前新闻、盘中数据、热点、个股观察、公司研究、复盘、回测和 AI 分析；所有结论必须区分真实、延迟、缺失和推断，不生成无证据的交易指令。

## 当前产品状态

- `confirmed`：用户可见品牌已统一为“一树-A股观测台”，窗口标题为“一树电子商务-A股观测台”，侧栏显示“上海一树电子商务有限公司”；内部兼容标识继续使用 `xiaoqibao.exe` 和 `XiaoQiBao-Portable`。
- `confirmed`：完整源码已上传至私有仓库 `zuitengxiaoqibao-code/Xiaoqibao-A-shares` 的 `main`；远程最终提交为 `10e4345507203e6baee0e4d55b8c58efd485d5a5`，本地数据库、缓存、日志、EXE、压缩包和真实凭据均未上传。
- `confirmed`：量化分析使用真实分层刷新：当前股票 TICK 1 秒、市场风格与策略 5 秒、首次涨停候选池 30 秒；页面隐藏时暂停，恢复后立即刷新，失败时保留最后有效证据并标记延迟。
- `confirmed`：个股观察刷新状态为“加载中 / 最新可用但待补齐 / 实时监控完成”三态，避免主行情完成但扩展数据仍补齐时产生矛盾文案。
- `confirmed`：新增“公司研究”一级菜单和 `/company-research` 路由，支持九维研究矩阵、多年财务、估值观察、十项反方审查、来源账本及最多 4 只股票的同行比较；缺失证据明确不评分。
- `confirmed`：公司研究资料源只提取请求栏目，通达信节点返回错误栏目时继续故障切换，禁止把“最新提示”冒充“公司概况”或“行业分析”。
- `confirmed`：个股观察与公司研究按页面、日期和股票隔离缓存，先展示完整当日缓存，再用真实字节和阶段进度后台更新；刷新失败继续保留缓存。
- `confirmed`：导航模式按钮使用新手蓝色、专家红色，其他菜单和行情语义色不变。

## 交付与验证

- `confirmed`：2026-08-03 当前工作树为干净状态，最新本地提交为品牌更名 `8ae202d`。
- `confirmed`：源码上传前验证为前端 382 项、后端 1054 项通过并有 1 项环境跳过，生产构建通过。
- `confirmed`：最新授权测试压缩包为 `一树-A股观测台-便携测试版-含默认AI-20260803-191204.zip`，SHA-256 为 `84CC39B6DC473580CBC5597245A8F8E82B2863FD1CB47D6900C44A3A41719248`。
- `confirmed`：该测试包包含已配置的默认 AI 访问能力，只适合授权测试用户；凭据原文未写入 Vault，也未进入源码仓库。
- `confirmed`：误删的 `dist/XiaoQiBao-Portable` 已从已验证测试包恢复，默认 AI 配置重新迁移为本机 Windows 加密状态。

## 持久约束

- 每个菜单必须使用与语义匹配的真实指标和内容结构；缺失时明确写“未接入/不可用”，不得用无关指标填充。
- 可见字体、图表标注和关键按钮必须易读；新闻热点优先采用横向标签并自动换行。
- 无真实盘中触发证据时，策略只能显示“等待触发”，实际仓位保持为 0。
- 重建便携版时保留配置、数据、新闻、缓存、日志、模型、导出和备份目录。
- 源码仓库与测试交付严格分离；含默认 AI 访问能力的压缩包不得公开发布。

## 风险与下一步

- `confirmed`：2026-08-06，量化分析仪表盘的分析标的区域已改为桌面端左右分栏：左侧放当前标的、代码/名称搜索和结果，右侧放首次涨停候选快速切换与规则快照；宽度不足时才恢复上下堆叠。前端 392 项测试、后端相关回归 4 项通过；便携 EXE 烟测窗口 313ms 出现，市场总览返回 `ready`，量化策略在无可用数据时诚实返回 `unavailable`。提交 `667838a`，EXE SHA-256 为 `036482112D266CE123C39DB56F9B7184EF60DE131566C22C0E8C97E52BE57AEA`。
- `obsolete`：2026-08-04 提出的“量化分析默认恢复最近股票、右上角分析标的搜索并同步全局状态”已在 2026-08-06 的 `667838a` 及后续提交中完成；后续只需继续回归跨页面切股和异步旧响应隔离。
- `observed`：真实数据源可能返回 `partial/stale` 或栏目缺失；界面应继续诚实标记数据年龄、覆盖度和失败原因。
- `observed`：包含默认 AI 访问能力的测试包具有分发风险，只能按授权范围交付并在后续测试后及时替换或回收。
- 下一步读取优先关注品牌、真实数据语义、当前干净提交、测试包授权边界和新需求；逐版本哈希与过程验证仅在追溯时读取 [[docs/history/A股转债量化-2026-W31]]。

## 2026-08-07 设置页运行状态诊断与交付

- `confirmed`：设置页新增通达信客户端与 JSON-RPC 桥分离状态。客户端状态来自当前运行的 `TdxW.exe`/`tdx.exe` 进程发现；桥状态来自 `127.0.0.1:17709` 端口可达性和只读能力探测；客户端运行不再等同于桥接 ready。
- `confirmed`：`TdxRpcStatus` 现在同时保留客户端状态、可执行文件路径、桥接状态、13 类只读能力和官方 Python 回退状态；专业缓存文件仍只显示 `detected_only`，没有真实专业行时不绑定字段。
- `confirmed`：本轮前端 `72` 个测试文件、`468` 项通过；API `1128` 项通过、`1` 项环境跳过；生产构建通过；便携 EXE 首轮 smoke 窗口 `120ms`、API `2660ms`、完整验证 `3485ms`，随后连续三次 API 分别为 `2448/2432/2431ms`；最新 EXE SHA-256 为 `E8516463D82C1DBD8639175588080D1A0AAECE0C402E8BD5C4F7A7E6E3018A6C`。
- `confirmed`：smoke 后桌面进程已释放，`17709` 未被本程序占用，便携持久目录全部保留。
- `observed`：本机当前未检测到通达信客户端进程，`127.0.0.1:17709` 未监听；专业字段继续保持 `detected_only/unavailable`。
- `inferred`：下一步只有在只读桥恢复并返回有效专业数据包后，才逐字段实测并绑定到财务、交易、板块和市场菜单；冷盘启动仍需要用多次 EXE 证据继续剖析 Windows 安全扫描波动。

## 2026-08-07 冷导入优化与便携交付复验

- `confirmed`：将 SQLAlchemy/SQLite 相关导入从 `qibao_api.main` 顶层延后到数据库引擎创建和 lifespan 数据库 bootstrap 的实际使用点；冷导入回归确认不会提前加载 `duckdb`、`pandas`、`numpy`、`mootdx` 或 `sqlalchemy`。
- `confirmed`：冷导入累计时间由约 817ms 降至约 626ms，减少约 191ms；该结果只作为 Python 模块导入证据，不等同于完整 EXE 冷盘启动耗时。
- `confirmed`：本轮 API 全量 `1128 passed, 1 skipped`；前端全量 72 个测试文件、468 项通过；Vite/TypeScript 生产构建通过。
- `confirmed`：便携 EXE 已重建，连续三次 smoke 窗口首帧为 `114/117/110ms`，API 就绪为 `2680/2476/2442ms`，完整验证为 `3537/3278/3241ms`；信息总览均为 `ready`，量化策略均为 `unavailable`，因为当前没有足够真实样本，未生成模拟推荐。
- `confirmed`：本轮 EXE SHA-256 为 `F6E29E181F01E5D385975F26CC0313C53D20C7154C2610DDE6E156A9A2097AD4`；`config/data/news/cache/logs/models/exports/backups` 均保留；smoke 后桌面进程和本程序对 `17709` 的占用均已释放。
- `observed`：当前本机仍未检测到通达信客户端进程，`127.0.0.1:17709` 未监听；专业缓存只能表示 `detected_only`，不能升级为专业字段 ready。
- `inferred`：后续持续目标为：只读桥恢复后逐字段验证 `Fn/GP/BK/SC/GO`，再绑定到财务/交易/板块/市场菜单；同时用冷盘与热启动两组 EXE 证据继续降低并解释 Windows 安全扫描与 PyInstaller 内读取波动。

## 2026-08-07 专业模块重复读取优化

- `confirmed`：`TdxQuantPythonSource` 现在按安装路径缓存已经加载的官方 Python 模块；重复只读查询复用模块对象，但每次调用仍重新初始化并关闭 `tq` 会话，避免长期句柄占用。
- `confirmed`：新增回归验证模块加载器只调用一次；相关专业源和路由测试 `13 passed`，API 全量 `1129 passed, 1 skipped`，前端全量 `468 passed`。
- `confirmed`：便携 EXE 本轮 smoke 冷盘一次为窗口 `308ms`、API `5520ms`、完整验证 `11302ms`；热启动两次为窗口 `108/115ms`、API `2452/2372ms`、完整验证 `3295/3195ms`。本次冷盘仍体现 Windows 扫描波动，不能用热启动替代冷盘结论。
- `confirmed`：本轮 EXE SHA-256 为 `4EF707390AD5B6C8DAB658764AA8C2299838F489BE6BEB3206BA4BA71C050ACF`；持久目录均保留，smoke 后无应用进程残留且 `17709` 未被本程序占用。
- `observed`：对 `D:\new_tdx64` 的官方 Python 专业只读实测仍返回 `TDX Python professional call unavailable`；模块可发现不等于专业字段可用，当前仍保持 `detected_only/unavailable`。

## 2026-08-07 首屏资源拆分优化

- `confirmed`：非首屏工作区使用 `React.lazy + Suspense`，量化分析、公司研究、首次涨停、可转债、设置、新闻、复盘和今日研判均独立加载；切换期间显示明确的“正在加载工作区”状态。
- `confirmed`：Vite 首屏入口 JS 从约 `1.69MB` 降至约 `1.52MB`，并生成量化、公司研究、设置等独立资源块；前端全量 `469 passed`。
- `confirmed`：本轮便携 EXE SHA-256 为 `6ED5422B694881DD825211A2A8FEB7B7015341E53B36FEC60C3F3A105C9723DB`；连续 smoke 冷盘一次 `320ms/5596ms/11377ms`，热启动两次 `104/126ms`、`2325/2433ms`、`3237/3260ms`（窗口/API/完整验证）；信息总览均 `ready`，量化策略均 `unavailable`。
- `confirmed`：smoke 后无 `xiaoqibao/qibao_desktop` 应用进程残留，`17709` 未被本程序占用，便携持久目录均保留。
- `inferred`：首屏入口仍受行情和 ECharts 依赖影响，后续只在实际 EXE 证据支持时继续拆分，避免为体积指标牺牲首屏功能完整性。

## 2026-08-07 真实发布数据烟测能力与验收

- `confirmed`：`scripts/run-portable-smoke.ps1` 新增 `-UseReleaseData` 模式，直接读取 `dist/XiaoQiBao-Portable` 中的真实 `config/data/news/cache/logs/models/exports/backups`，不复制、不清理发布目录；默认模式仍使用隔离临时目录。
- `confirmed`：发布烟测新增 `/api/v1/tdx/local/professional` 只读探针，专业字段状态与原因会被记录，不把模块发现或普通行情当作专业数据 ready。
- `confirmed`：本轮 API 全量 `1130 passed, 1 skipped`，前端全量 `72` 个测试文件、`469 passed`，生产构建通过。
- `confirmed`：默认隔离 EXE smoke 为窗口 `124ms`、API `2620ms`、完整验证 `3500ms`；信息总览 `ready`，量化策略 `unavailable`，通达信专业字段 `unavailable`。
- `confirmed`：真实发布数据 EXE smoke 为窗口 `61ms`、API `2018ms`、完整验证 `9430ms`；信息总览 `ready`，量化策略 `partial`，真实候选 `7` 只，市场风格覆盖 `85.00%`；通达信专业字段保持 `unavailable`，未生成模拟值。
- `confirmed`：本轮 EXE SHA-256 为 `83CD95D5E750AEBBDAF84DD6F01875144F7E3CFA75E12A34B2D5F21AD8027930`；smoke 后桌面进程已释放、`127.0.0.1:17709` 未被本程序占用，便携持久目录全部保留。

### 当前仍未完成的长期目标

- `observed`：本机通达信客户端/只读桥仍未恢复，专业 `Fn/GP/BK/SC/GO` 只能保持 `detected_only/unavailable`；待真实桥返回有效行后逐字段绑定财务、交易、板块和市场专题并回归。
- `inferred`：继续以冷盘/热启动两组 EXE 数据剖析 Windows 安全扫描和 PyInstaller 内读取成本；窗口首帧已满足 3 秒目标，但冷盘 API 与完整验证存在环境波动。

## 2026-08-07 量化缓存可观测性与最终烟测

- `confirmed`：量化策略响应新增候选扫描、触发证据两层的采集时间、年龄和缓存复用标记；前端状态栏明确显示“刚刚采集/复用缓存”，保持 30 秒候选扫描与 5 秒触发证据预算可解释。
- `confirmed`：盘中快照 SQLite 表新增 `(symbol, observed_at, sequence)` 索引，并以 `EXPLAIN QUERY PLAN` 回归确认按股票索引读取，避免候选触发证据读取全表。
- `confirmed`：便携烟测新增 `home/overview/quant/professional` 独立请求耗时。真实发布目录本轮为窗口 96ms、API 2050ms、完整验证 11370ms；量化请求 6318ms，信息总览 1105ms，专业探针 1776ms；量化真实候选 7 只、市场风格覆盖 85%，专业字段仍 unavailable。
- `confirmed`：隔离目录本轮为窗口 126ms、API 2460ms、完整验证 4379ms；隔离数据不足时量化保持 unavailable，不生成模拟推荐。
- `confirmed`：最新便携 EXE SHA-256 为 `787C004202E1DCCDF2E98662E6B0A4ED19FA3557889D3CFEE4EFF751438AC315`；烟测后无应用/通达信探测进程残留，17709 未监听，`config/data/news/cache/logs/models/exports/backups` 全部保留。
- `observed`：真实发布首次量化耗时主要来自全市场日线候选扫描；后续刷新复用内存缓存。继续优化时必须评估物化因子或后台预热的真实性边界，不能用未经校验的持久缓存冒充最新数据。
- `inferred`：通达信专业桥恢复仍是 `Fn/GP/BK/SC/GO` 逐字段绑定的唯一外部前置条件；当前 `detected_only/unavailable` 继续保持。
- `inferred`：继续在真实发布数据 smoke 中观察量化 `partial` 的覆盖字段和候选池变化，始终保持缺失数据的诚实状态。

## 2026-08-07 量化候选后台预热与 EXE 复验

- `confirmed`：便携运行时的量化候选扫描改为单线程后台预热。首次请求立即返回真实市场状态和 `candidate_scan_state=pending`，不再同步等待全市场日线扫描；后续轮询消费成功结果后才展示真实候选。
- `confirmed`：量化响应新增 `candidate_scan_state`、`candidate_scan_started_at`、`candidate_scan_error`；状态栏显示“后台预热中”“扫描失败”或原有缓存年龄，用户能区分页面等待、真实采集和复用缓存。
- `confirmed`：应用 lifespan 结束时会等待并取消候选扫描执行器，smoke 后无 `xiaoqibao/qibao_desktop/TdxW/TdxSP/TdxNonSP` 残留进程，`127.0.0.1:17709` 未监听。
- `confirmed`：本轮 API 全量 `1143 passed, 1 skipped`；前端 `72` 个测试文件、`473 passed`；生产构建通过；便携 EXE 已重建。
- `confirmed`：本轮隔离 smoke 三次窗口首帧 `121/112/118ms`，API 就绪 `2440/2421/2415ms`，完整验证 `4556/4477/4443ms`；信息总览均 `ready`，隔离环境量化无真实样本时保持 `unavailable`。
- `confirmed`：本轮真实发布 smoke 三次窗口首帧 `325/91/62ms`，API 就绪 `5590/1971/1992ms`，完整验证 `19117/11205/11013ms`；量化后台扫描最终得到真实候选 `7` 只、市场风格覆盖 `85.00%`；专业字段仍 `unavailable`。
- `confirmed`：最新便携 EXE SHA-256 为 `A7391C2B83912EDB2E0519BD3FBC61178A070719E98017C770576F02085EB08A`；发布目录 `config/data/news/cache/logs/models/exports/backups` 全部保留。
- `observed`：真实发布首次 API 就绪仍受 Windows 冷盘安全扫描波动影响，窗口首帧未受阻；不能用热启动结果替代冷盘结论。

### 本轮仍未完成的长期目标

- `inferred`：本机通达信只读桥恢复后，继续逐项实测 `Fn/GP/BK/SC/GO`，记录请求、响应形状、单位、来源和时间戳，再绑定业务菜单。
- `inferred`：继续评估持久化因子快照或受校验的后台预热策略；当前后台预热已解决首个量化请求阻塞，但没有把未经最新校验的旧候选当作实时结果。

## 2026-08-12 九阶段平台完善路线完成

- `confirmed`：完成请求合并、字段证据、统一事件、量化严格验证、公司研究版本闭环、全站图形语义、七类共享快照、便携增量更新和最终 EXE 验收九个阶段。
- `confirmed`：七类共享快照为市场横截面、涨跌停事件、板块强度、个股资金、新闻事件、财务估值和量化因子；只保存版本与哈希元数据，不复制事实数据库，并区分缓存复用与同内容重复计算。
- `confirmed`：信息总览 50 个菜单保持唯一显式指标契约与专属工作区；不退回通用重复面板。
- `confirmed`：便携更新只复制发生变化的程序文件，删除旧程序资源，失败自动回滚；`config/data/news/cache/logs/models/exports/backups` 永不参与替换或删除。
- `confirmed`：最终 API `1313 passed, 1 skipped`，Web `582 passed / 101 files`，Vite 生产构建、UTF-8 扫描和差异检查通过。
- `confirmed`：最新 EXE 为 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `AAA3E27F481528D7D83BE9301D18119550471FB7380FE4B49726CAB863E1CE92`。
- `confirmed`：真实发布数据 smoke 窗口 317ms、API 5442ms、完整验证 16345ms；信息总览 ready，量化 partial（真实候选 1 只、覆盖 85%），公司研究 partial（证据覆盖 65%），专业 Fn/GP/BK/SC/GO 保持 unavailable，未生成模拟值。
- `confirmed`：发布总体积约 2.40GB，其中程序约 135.5MB、持久数据约 2.27GB；主要体积来自本地真实行情库。烟测后应用进程为 0、17709 未监听、八个持久目录完整。
- `observed`：本机本轮未发现通达信客户端进程；专业插件仍是外部真实性前置条件，恢复后才可把专业字段升级为 ready。

## 2026-08-07 后台扫描失败边界与最终交付

- `confirmed`：后台候选扫描失败时只向页面返回固定的可行动原因，不暴露异常原文、本机路径或潜在凭据片段；对应回归已覆盖。
- `confirmed`：最终构建 API `1144 passed, 1 skipped`；前端 `72` 个测试文件、`473 passed`；Vite/TypeScript 与 PyInstaller 构建通过。
- `confirmed`：最终真实发布 smoke：窗口 `63ms`、API `2122ms`、完整验证 `11403ms`；信息总览 `ready`，量化后台扫描最终真实候选 `7` 只、市场风格覆盖 `85.00%`，专业桥 `unavailable`。
- `confirmed`：最终隔离 smoke：窗口 `125ms`、API `2446ms`、完整验证 `4526ms`；隔离无真实候选时量化保持 `unavailable`。
- `confirmed`：最终 EXE SHA-256 为 `3EF466C656801B4869DD9FB9D04A2E054F0633CF16F1B808A80B1A19DE56D476`；持久目录保留，smoke 后应用/探测进程和 `17709` 均已释放。

## 2026-08-07 首屏 ECharts 按需加载与通达信桥探测

- `confirmed`：`QuantChart` 已改为运行时按需加载 ECharts，图表容器在引擎加载期间显示动态状态，加载成功后才初始化图表，异常时显示不可用状态；量化、分时、事件 K 线、回测和公司研究继续共用该组件。
- `confirmed`：Vite 首屏资源由约 `1.52MB` 单块拆为约 `483KB` 首屏块和约 `1.04MB` ECharts 块；前端全量 `72` 个测试文件、`469 passed`，生产构建通过。
- `confirmed`：便携 EXE smoke 窗口 `115ms`、API `2676ms`、完整验证 `3529ms`；真实发布数据仍为信息总览 `ready`、量化 `partial`（7 只候选、85.00% 覆盖），未出现启动回归；最新构建沿用真实发布目录保留策略。
- `confirmed`：完成本轮源码后的便携 EXE 重建，最新 SHA-256 为 `2AB32C12962D25FE9839FFA8169C7D12AACC230F0207BB3E6DA3660FC0B3425A`；API 全量 `1130 passed, 1 skipped`，前端全量 `469 passed`。
- `observed`：隐藏启动 `D:\new_tdx64\TdxW.exe` 后，客户端进程正常但 `127.0.0.1:17709` 在 8 秒内仍未监听；探测进程已释放，专业字段继续保持 `unavailable`。
- `inferred`：保留 ECharts 按需加载，它降低首屏脚本阻塞但没有显著改变 Python API 冷启动；后续继续分别分析 Windows 冷盘扫描与本地桥接恢复。

## 2026-08-07 专业探针修正与原因诊断

- `confirmed`：便携 smoke 的专业字段探针已从非法 `table_list=Fn` 修正为契约要求的 `table_list=Fn193`；新增回归断言防止错误参数再次进入发布验收。
- `confirmed`：专业数据路由现在按已知安全错误类型返回可行动中文原因，不回显供应商异常、内部堆栈或凭据；官方 Python 初始化/调用失败会提示检查通达信客户端和专业插件初始化。
- `confirmed`：本轮 API 全量 `1131 passed, 1 skipped`，前端全量 `469 passed`，生产构建通过；相关专业/路由/打包回归 `22 passed`。
- `confirmed`：便携 EXE SHA-256 为 `0886D0EED76769B2E31EB39BF52FD63251308F5A4529951350275244300B210D`；隔离 smoke 窗口/API/完整验证为 `113/2645/4568ms`，真实发布目录为 `65/2032/10753ms`；信息总览 `ready`，真实发布量化 `partial`（7 只候选、85.00% 覆盖），专业字段仍 `unavailable`。
- `confirmed`：smoke 后应用进程已释放，`127.0.0.1:17709` 未监听，发布目录持久数据保留。
- `observed`：本机官方 Python 模块存在但真实调用仍返回初始化/调用失败；模块发现不能升级为专业字段可用。
- `inferred`：下一步继续等待/验证通达信只读桥，逐项实测 `Fn/GP/BK/SC/GO` 后再绑定业务菜单；同时用冷盘与热启动多次 EXE 证据剖析 Windows 安全扫描波动。

## 2026-08-07 三次连续 EXE 启动基线

- `confirmed`：连续三次隔离 smoke 窗口首帧为 `134/110/110ms`，API 就绪为 `2355/2432/2469ms`，完整验证为 `4196/4208/4219ms`；三次信息总览均 `ready`，量化策略均按真实样本状态返回 `unavailable`。
- `confirmed`：三次 smoke 后均无应用残留进程，`127.0.0.1:17709` 未被本程序占用；本次只建立热启动基线，不替代冷盘结论。
- `observed`：启动窗口和 API 就绪已稳定在目标范围内，剩余波动主要出现在完整验证阶段；需用后续冷盘样本继续拆分 Windows 扫描与业务初始化成本。

## 2026-08-07 预交易时段情绪刷新日志修正

- `confirmed`：`MarketSentimentWrongPhase` 已从通用异常日志中分离；交易时段外刷新属于预期跳过，日志改为 `initial market sentiment refresh skipped outside session`，真实异常仍保留 traceback。
- `confirmed`：本轮 EXE SHA-256 为 `54D4F206EFC2E45951E8F8D028D48E565B48FC88766567F446F29929112A7FE0`；隔离 smoke 窗口/API/完整验证为 `112/2684/4514ms`，真实发布 smoke 为 `65/2074/10677ms`。
- `confirmed`：真实发布 smoke 后无应用残留进程，`127.0.0.1:17709` 未监听；信息总览 `ready`，量化 `partial`（7 只候选、85.00% 覆盖），专业字段仍 `unavailable`。

## 2026-08-07 盘前快照语义与缓存连续性

- `confirmed`：信息总览行情状态已拆分字段完整度与时间新鲜度；`market_data.quality` 表示字段覆盖，`market_data.phase/freshness` 表示盘前、盘中、收盘后、休市以及实时、上一交易日收盘、当日最终、陈旧或不可用。
- `confirmed`：盘前上一交易日完整快照不会再被页面标记为“实时监控中”；首页、专题工作区和量化策略统一显示上一收盘/等待开盘语义。收盘后显示最终快照而非实时监控。
- `confirmed`：浏览器端跨日缓存改为开盘前允许最近 1 至 3 个自然日的收盘快照，09:25 后拒绝跨日行情；旧版本缓存读取时补充 `premarket/previous_close` 元数据。
- `confirmed`：本轮 API 全量 `1136 passed, 1 skipped`；前端全量 72 个测试文件、`472 passed`；生产构建和便携 EXE smoke 均通过。
- `confirmed`：最新 EXE SHA-256 为 `F440A924F547225CEF7FD8D93A1F5F714AEA349B6BA2430F6579C4B7CCCFFDE0`。隔离三次窗口/API/完整验证为 `118/2421/4244ms`、`112/2328/4208ms`、`110/2336/4185ms`；真实发布三次为 `57/1980/11373ms`、`60/1958/11251ms`、`54/1993/11345ms`。
- `confirmed`：所有 smoke 完成后应用进程和 `127.0.0.1:17709` 均已释放，`config/data/news/cache/logs/models/exports/backups` 全部保留。
- `observed`：本机通达信专业只读桥仍未监听，专业 `Fn/GP/BK/SC/GO` 继续为 `unavailable`；真实发布量化策略有 7 只候选、市场风格覆盖 85.00%，隔离环境因真实样本不足保持 `unavailable`。
- `inferred`：下一步只在通达信专业桥恢复并返回有效行后逐字段绑定业务菜单；启动性能继续以真正冷盘与热启动双组数据审计，不能用热启动代替冷盘结论。

## 2026-08-07 桥接根因与量化刷新缓存

- `confirmed`：对 `D:\new_tdx64\PYPlugins\TPythClient.dll` 进行只读 direct 初始化实测，使用官方 `tqcenter.py` 的 DLL 路径、连接脚本和当前 Python 3.12 版本号，返回 `ErrorId=11`；解码原因为“初始化错误：请确认是否打开通达信客户端”。
- `confirmed`：`TdxW.exe` 进程可以启动并响应，但本次进程模块列表未加载 `TPythClient.dll`，`T0001\tdxsys3.log` 未出现后台数据服务启动记录；专业 `Fn/GP/BK/SC/GO` 继续保持 `detected_only/unavailable`，不把缓存文件名或普通行情字段升级为专业数据。
- `confirmed`：数据设置页和 API 的桥接状态改为按实际配置 URL 解析端口；自定义端口不再被显示为固定 17709。
- `confirmed`：量化策略服务增加两级缓存：候选池日线扫描默认缓存 30 秒，触发证据默认缓存 5 秒；API 全量 `1139 passed, 1 skipped`，前端 `473 passed`，生产构建和便携 smoke 通过。
- `confirmed`：本轮 EXE SHA-256 为 `01C9B70BE8EF3F98FB6B83C7DC5997AE9B76B00482033AAFE2A8D959ED2F918`；真实发布 smoke 窗口/API/完整验证 `60/2005/11532ms`，信息总览 `ready`，量化 `partial`（7 只候选、85.00% 覆盖），专业字段 `unavailable`。
- `observed`：隔离冷盘第一次静态资源请求超时，保留烟测目录复测成功（`117/2439/4383ms`）；需要继续累积冷盘与热启动样本，不能把一次失败归因于代码回归。

### 持续目标

- `inferred`：通达信客户端登录并在客户端内启动 TdxQuant/只读服务后，逐项实测 `Fn/GP/BK/SC/GO`，记录请求、响应形状、单位、来源和时间戳，再绑定业务菜单。
- `inferred`：继续拆分 Windows 冷盘安全扫描、PyInstaller 内读取和业务接口耗时；保持缓存优先、实时年龄标记和缺失数据诚实状态。

## 2026-08-07 量化后台预热动态状态与交付复验

- `confirmed`：量化状态栏在候选扫描 `pending` 时显示无确定进度动画、已运行秒数和“进度由本地扫描决定”；不伪造 1% 至 100% 的百分比。
- `confirmed`：新增前端回归后，前端全量 `474 passed`（73 个测试文件），后端全量 `1144 passed, 1 skipped`，Vite/TypeScript 生产构建通过。
- `confirmed`：本轮便携 EXE 已重建，SHA-256 为 `DC4E82CAC982F8B9AAC7912243F585FD49D3896A5284BDF8556D565E55331766`。
- `confirmed`：真实发布目录 smoke：窗口首帧 `73ms`、API 就绪 `2166ms`、完整验证 `11493ms`；首页 `149ms`、信息总览 `1100ms`、量化首次请求 `175ms`、专业探针 `1015ms`；量化真实候选 `7` 只、市场风格覆盖 `85.00%`，通达信专业字段继续 `unavailable`。
- `confirmed`：隔离目录 smoke：窗口首帧 `125ms`、API 就绪 `2454ms`、完整验证 `4570ms`；无真实样本时量化保持 `unavailable`，没有生成模拟推荐。
- `confirmed`：两次 smoke 后均无桌面/探测残留进程，`127.0.0.1:17709` 未被本程序占用，`config/data/news/cache/logs/models/exports/backups` 全部保留。
- `observed`：smoke 终端的中文原因在部分 Windows 管道环境中仍可能出现编码显示异常；应用接口本身返回固定安全原因，源码和发布文件通过 UTF-8/乱码扫描。

### 仍未完成的计划与目标

- `inferred`：通达信专业桥恢复后逐项实测 `Fn/GP/BK/SC/GO`，记录请求、响应形状、字段单位、来源和时间戳，再绑定业务菜单。
- `inferred`：仅在扫描器能提供真实处理数量或阶段时增加确定百分比；当前继续使用无确定进度，避免把估算当作采集事实。
- `inferred`：继续积累真正冷盘与热启动 EXE 样本，分别记录窗口首帧、API 就绪、业务请求和专业探针耗时。

## 2026-08-07 真实量化扫描阶段进度与最终复验

- `confirmed`：候选扫描契约新增 `candidate_scan_phase`、`candidate_scan_processed`、`candidate_scan_total`，阶段明确为历史读取、因子计算、排序、就绪或失败。
- `confirmed`：仅在因子计算阶段使用扫描器实际提供的 `processed/total` 显示百分比；历史读取和排序阶段仍显示动态等待，不用计时器伪造 1% 至 100%。
- `confirmed`：本轮 API `1146 passed, 1 skipped`，前端 73 个测试文件、`475 passed`，Vite/TypeScript 生产构建通过；源码 UTF-8/乱码扫描和 `git diff --check` 通过。
- `confirmed`：真实发布目录 smoke：窗口 `94ms`、API `2152ms`、完整验证 `11295ms`；首页 `144ms`、信息总览 `1097ms`、量化 `171ms`、专业探针 `1020ms`；量化真实候选 `7` 只、市场风格覆盖 `85.00%`，专业字段 `unavailable`。
- `confirmed`：隔离目录 smoke：窗口 `113ms`、API `2465ms`、完整验证 `4527ms`；数据不足时量化保持 `unavailable`，未生成模拟候选。
- `confirmed`：smoke 后应用/探测进程均已释放，`127.0.0.1:17709` 未被本程序占用，`config/data/news/cache/logs/models/exports/backups` 全部保留；本轮 EXE SHA-256 为 `896D6C80A2850451C631B87485425F7F134307B44B9679E53261E8D2F41560E9`。

### 当前持续计划

- `inferred`：通达信专业插件/只读桥恢复后，逐项实测 `Fn/GP/BK/SC/GO`，记录请求、响应形状、单位、来源和时间戳，再绑定业务菜单。
- `inferred`：继续积累真正冷盘与热启动 EXE 样本，拆分 Windows 安全扫描、PyInstaller 内读取和业务请求耗时；不得以热启动替代冷盘结论。

## 2026-08-07 桌面启动真实里程碑提示

- `confirmed`：便携 EXE 启动页新增真实里程碑读取；只解析 API 日志白名单阶段，不按时间或固定步长伪造完成度。
- `confirmed`：启动等待期间可以显示本地数据源、数据库、仓库、市场服务、历史校准和 API 初始化阶段；读取线程在 API 成功/失败后立即停止并回收。
- `confirmed`：API 全量 `1151 passed, 1 skipped`，前端 73 个测试文件、`475 passed`，生产构建通过；真实发布连续两次 smoke 为 `297/5554/19340ms`（冷盘波动）和 `59/2021/11091ms`（热启动），两次均有真实候选 `7` 只、覆盖 `85.00%`；隔离 smoke 为 `112/2395/4425ms`，数据不足时量化 `unavailable`。
- `confirmed`：本轮 EXE SHA-256 为 `5F1B0E34E6E39CA54CED4FFCE5B098F81BF3FEF68437D45021D14AEB1FA210A3`；smoke 后进程释放、`17709` 未监听、持久目录保留。

### 当前持续计划

- `inferred`：通达信专业桥恢复后继续逐项实测 `Fn/GP/BK/SC/GO` 并绑定菜单。
- `inferred`：继续用冷盘/热启动双组 EXE 证据拆分 PyInstaller 内读取和 Windows 安全扫描成本，不能用热启动替代冷盘结论。

## 2026-08-07 API 导入阶段冷盘证据

- `confirmed`：便携 API 服务器在 Uvicorn 启动前显式加载应用对象并记录 `api-app-imported`，启动页可显示“API 模块已加载”；不改变业务路由和数据状态。
- `confirmed`：本轮桌面测试目录 `35 passed`；API 全量 `1152 passed, 1 skipped`，前端 73 个测试文件、`475 passed`，生产构建通过。
- `confirmed`：真实发布 smoke 冷盘为窗口/API/完整验证 `317/5570/19459ms`，热启动为 `62/1960/11194ms`；隔离 smoke 为 `114/2452/4545ms`。真实发布仍有 7 只候选、85% 覆盖，隔离数据不足保持 `unavailable`。
- `observed`：冷盘日志记录应用导入 `1951ms`，生命周期约 `546ms`；剩余 API 就绪差异来自 PyInstaller/Windows 冷盘读取，后续继续收集证据，不用热启动替代冷盘。
- `confirmed`：本轮 EXE SHA-256 为 `80102A8140A9E794DF44D576288C2BC0624D5B7A14452B5F5671C6F40E76BD13`；smoke 后无残留进程，`17709` 未监听，持久目录保留。

## 2026-08-07 API 导入里程碑复验

- `confirmed`：启动专项测试目录 `35 passed`；Uvicorn 字符串应用现在显式预加载并记录 `api-app-imported import_ms`，启动页可区分模块导入和生命周期初始化。
- `confirmed`：本轮真实发布目录连续三次 smoke 的窗口/API/完整验证为 `299/5584/19437ms`、`59/1956/11085ms`、`55/2004/11035ms`；量化真实候选均为 7 只、市场风格覆盖 85.00%。隔离 smoke 为 `122/2414/4492ms`，无真实样本时量化保持 unavailable。
- `confirmed`：smoke 后无应用/探测残留进程，`127.0.0.1:17709` 未监听，便携持久目录全部保留；最新 EXE SHA-256 为 `EC47CDAFA176977C8D9CE2FBBA8FFF5F59DB763F8003A02DB4B8DCEEAAD08A8E`。
- `observed`：专业 `Fn/GP/BK/SC/GO` 探针仍返回 unavailable；当前继续遵守不使用缓存文件或普通行情代理专业字段的边界。

### 仍未完成的计划

- `inferred`：通达信客户端完成专业插件初始化并恢复只读桥后，逐项记录 `Fn/GP/BK/SC/GO` 请求、响应形状、字段单位、来源和时间戳，再绑定业务菜单。
- `inferred`：继续积累真正冷盘与热启动样本，拆分 PyInstaller/Windows 冷读取成本和业务请求耗时；不以热启动代替冷盘结论。

## 2026-08-07 冷启动导入成本基线

- `confirmed`：本轮发布 smoke 日志中的 API 应用导入耗时样本为 `1951/1974/974ms`，生命周期初始化约 `546-594ms`；冷启动波动主要位于 PyInstaller/Windows 内读取和应用模块导入，不是业务生命周期。
- `confirmed`：CPython `-X importtime` 导入 `qibao_api.main` 约 `637ms`，主要开销集中在 FastAPI/Pydantic schema、公司研究/诊断契约和多路由模块。
- `inferred`：下一轮只对已验证的重型导入做小范围懒加载实验，并以 EXE 冷盘/热启动、接口回归和资源释放结果作为保留门槛。

## 2026-08-07 信息总览缓存优先刷新

- `confirmed`：便携版新增 `cache/market-overview.json`，只保存上一轮真实 `MarketOverviewResponse`；读取时按当前市场阶段重新标记 freshness，不把旧数据称为实时。
- `confirmed`：有缓存时先返回完整旧证据，后台刷新最新指数、分钟线、新闻和本地市场；失败保留旧结果并增加固定失败标记。真实发布 smoke 的信息总览请求从首次 `5215ms` 降到后续 `616/569ms`。
- `confirmed`：本轮 API `1153 passed, 1 skipped`，信息总览/生命周期专项 `24 passed`，生产构建和隔离 smoke 通过；最新 EXE SHA-256 为 `84AA38BF398D6B151D596F93E731EFEED8D72C0D8496CDBAE6C8DF417756B5DB`。
- `observed`：通达信专业桥仍未监听，`Fn/GP/BK/SC/GO` 继续 `unavailable`；缓存优化不改变专业字段真实性边界。

## 2026-08-07 专业五类探针覆盖

- `confirmed`：便携 smoke 现在逐项探测 `get_financial_data/Fn193`、`get_gpjy_value/GP1`、`get_bkjy_value/BK5`、`get_scjy_value/SC1`、`get_gp_one_data/GO1`，并分别记录状态与原因。
- `confirmed`：本机五类结果均为 `unavailable`，没有把单一字段、缓存文件或模块发现状态误报为整体专业数据可用；本次专业探针总耗时约 `5206ms`。
- `inferred`：通达信客户端和只读桥恢复后，直接使用同一 smoke 命令完成真实逐字段映射，再绑定财务、交易、板块、市场和量化菜单。

## 2026-08-07 同日旧快照 freshness 边界

- `confirmed`：盘中同日快照只有在观测时间距当前不超过 2 分钟时才显示 `live`，超过窗口显示 `stale`；缓存不会因为日期相同而被误报为实时。
- `confirmed`：新增同日旧快照回归并修正候选后台扫描测试的条件等待；专项连续 10 次通过。
- `inferred`：后续继续以观测时间、来源和覆盖度三者共同决定数据状态，不用页面请求是否成功替代行情新鲜度。

- `confirmed`：freshness 修复后的 EXE 串行 smoke 为窗口/API/完整验证 `63/2000/14700ms`，信息总览 `593ms`；五类专业探针仍均 `unavailable`，最新 EXE SHA-256 为 `DA8C2486AA19F8EFEE4088FCFD1934F3639F4F688AB33086BB5F5D68004BABC1`。

## 2026-08-07 通达信专业失败冷却

- `confirmed`：官方 TdxQuant Python 初始化或调用失败后增加 10 秒短时失败冷却；冷却只复用 `unavailable` 状态，不缓存、生成或代理任何专业字段，成功响应会立即清除冷却。
- `confirmed`：新增回归确认连续两次查询只执行一次官方初始化；API 全量 `1156 passed, 1 skipped`，前端最近全量 `475 passed`，生产构建和便携构建通过。
- `confirmed`：真实发布 smoke 的五类专业探针由约 5.1 秒降至 `1032/1079ms`；五类仍全部 `unavailable`，量化保持 7 只真实候选和 85.00% 市场覆盖。
- `confirmed`：最新 EXE SHA-256 为 `743434B752F0B13007E261B6B793AE47D872D788B7DA89EAD72953A7D81C6DA6`；冷盘窗口/API/完整验证 `290/5577/18858ms`，热启动 `58/1959/10359ms`，持久目录保留且 smoke 后无进程与端口残留。
- `inferred`：通达信客户端和专业插件真实恢复后，继续逐项实测 `Fn/GP/BK/SC/GO` 并绑定业务菜单；失败冷却不得用于提升数据状态。

## 2026-08-07 预交易无效刷新移除

- `confirmed`：启动前 09:30 的市场情绪刷新不再提交到单线程历史执行器；该阶段本来必然因 `MarketSentimentWrongPhase` 跳过，旧任务会在启动后约 5.5 秒才结束并占用启动资源。
- `confirmed`：盘中和收盘后仍保留真实后台刷新；新增 premarket/intraday 回归，API 全量 `1157 passed, 1 skipped`。
- `confirmed`：真实发布冷盘 smoke 窗口/API/完整验证 `96/2105/11198ms`，信息总览 `770ms`；热启动 `62/2029/10529ms`，信息总览 `650ms`；量化真实候选 7 只、市场覆盖 85.00%，专业五类仍 `unavailable`。
- `confirmed`：最新 smoke 后测试 mock 通达信进程已释放，`127.0.0.1:17709` 未监听，持久目录保留。
- `inferred`：继续积累冷盘/热启动样本，拆分 Windows 安全扫描、PyInstaller 内读取和首次序列化耗时；专业桥恢复后再进行 `Fn/GP/BK/SC/GO` 逐字段绑定。

## 2026-08-07 5 秒刷新视觉连续性修复

- `confirmed`：信息总览启动遮罩与后台轮询状态已拆分；首次有效快照完成后，后续 5 秒刷新不会再次显示 `REAL DATA STARTUP PIPELINE`，旧行情在刷新期间持续可见。
- `confirmed`：前端全量 `476 passed`，API 全量 `1157 passed, 1 skipped`，生产构建通过；真实发布 EXE smoke 窗口/API/完整验证为 `92/2122/21787ms`，信息总览 `729ms`，量化真实候选 `7` 只、覆盖 `85.00%`。
- `confirmed`：最新 EXE SHA-256 为 `A94DB00085F5182EB529D89EBF7FB748577C6FA8E759D62EFC37DB546C9CCC83`；便携目录持久数据均保留。
- `confirmed`：后续烟测清理只允许停止本次烟测自身创建的应用进程；不得按进程名或路径主动关闭用户正在运行的通达信客户端/辅助进程。
- `observed`：本机通达信相关进程可能由用户或外部守护程序自动重启；当前不对其做任何控制，专业字段仍按真实探针结果保持 `unavailable`。

## 2026-08-07 量化分析标的卡片可读性优化

- `confirmed`：量化分析顶部标的卡片增加“标的已锁定”状态行，明确区分候选池标的与自定义标的；右侧快速切换区拆分为“快速切换 / 首次涨停候选快速切换 / 候选池标的 / 规则快照”四层，避免提示条与下拉框争抢视觉层级。
- `confirmed`：股票搜索结果下拉改为从搜索框下方展开，避免覆盖当前标的和状态信息；前端全量 `477 passed`，Vite/TypeScript 生产构建通过。
- `confirmed`：当前发布版仍在 PID `22200` 运行时，便携构建自动旁路到独立 staged 目录；被占用的持久文件（如 `data/market.duckdb`）只在复制失败时从最近一次已验证 staged 发布目录补齐，不关闭或重启用户版及通达信。新旁路 EXE 烟测：窗口 `308ms`、API `5126ms`、完整验证 `12442ms`，信息总览 `ready`，量化策略 `partial`（真实候选 0、覆盖 85%），专业五类探针仍 `unavailable`。
- `confirmed`：最终正式便携 EXE SHA-256：`6EEDCD36A792C87620450E2D961BEF592F82C450FBC2DEC032A088C9C817E23C`；正式目录烟测窗口 `83ms`、API `2461ms`、完整验证 `4590ms`，信息总览 `ready`，量化策略因隔离样本不足保持 `unavailable`；通达信 `TdxW.exe` PID `17900`、`tdxcef.exe` PID `16880/39044/42216/44904` 在前后保持不变。观测台本身仅因重建后恢复启动，未对通达信做任何控制。

## 2026-08-07 标的卡片窄屏重叠修复

- `confirmed`：修复窄窗口下“候选池标的”与“首次涨停候选快速切换”横向重叠，以及规则快照被状态说明挤压的问题；标的状态标签和右侧候选上下文改为可堆叠行，长文本允许自然换行，搜索和下拉内容不再覆盖彼此。
- `confirmed`：前端全量 `478 passed`；旁路便携 EXE 烟测窗口 `88ms`、API `3363ms`、完整验证 `6761ms`，信息总览 `ready`，量化策略在隔离样本不足时保持 `unavailable`；当前运行的修复版观测台 PID `9180`，路径为独立 staged 发布目录。
- `confirmed`：修复版 EXE SHA-256：`2AFBEFC6BB8292CB686164028B0F660E481EFF480F818FB4178622555FF7B47E`；通达信 `TdxW.exe` PID `17900` 与 `tdxcef.exe` PID `16880/39044/42216/44904` 未被关闭、重启或控制。

## 2026-08-07 正式发布资源滞后修复

- `confirmed`：复核用户截图后确认，源码与测试已包含堆叠布局，但正式 `dist/XiaoQiBao-Portable/web/assets` 仍引用旧 CSS/JS，旧资源没有 `.quant-instrument-heading.stacked`，因此用户打开正式 EXE 仍看到标签横向重叠；问题根因是发布资源滞后，不是组件结构再次失效。
- `confirmed`：重新执行完整便携构建并覆盖正式发布目录，发布 CSS/JS 已包含 `.quant-instrument-heading.stacked`、`.quant-candidate-context.stacked` 和对应新标记；持久化目录 `config/data/news/cache/logs/models/exports/backups` 全部保留。
- `confirmed`：本轮 API `1164 passed, 1 skipped`，前端 `478 passed`，生产构建通过；正式发布烟测窗口 `70ms`、API `2234ms`、完整验证 `10690ms`，信息总览 `ready`，量化策略 `partial`（真实候选 8 只、覆盖 85%），专业通达信字段继续 `unavailable`，未生成模拟数据。
- `confirmed`：本轮正式 EXE SHA-256 为 `2309AB8B56837FAF7B91E8DB07A46A0828DE23D1F9EE64F63495E97FEC67EBF0`；烟测后观测台进程已释放，通达信 `TdxW.exe` PID `17900`、`tdxcef.exe` PID `16880/39044/42216/44904` 与 `127.0.0.1:17709` 监听均保持不变。

## 2026-08-07 通达信专业桥响应复核

- `confirmed`：仅只读调用当前 `http://127.0.0.1:17709/`，探针前后 `TdxW.exe` PID `17900`、多个 `tdxcef.exe` 和端口均保持运行；没有关闭、重启或控制通达信。
- `confirmed`：`Fn193..Fn197` 返回 `ErrorId=0` 但无可验证 `Fn` 字段；`GP1..GP5` 与 `SC1..SC5` 返回空值；这些家族继续 `unavailable`。
- `confirmed`：`BK5..BK9` 返回带日期的嵌套记录，字段列含义和单位未声明；解析器现在拒绝把嵌套列表转成字符串，因此不误报可用，也不绑定板块业务字段。
- `observed`：`GO1/GO2/GO3/GO4/GO47` 对 `688318.SH` 返回标量值（含 `107.41`、`1667.00`、`0.00`、`2026.00`、`0.00`），但官方响应未声明含义和单位；目前只能记录为可解析响应，不能用于财务、交易或量化结论。
- `confirmed`：新增后端回归覆盖嵌套专业记录拒绝逻辑，避免将响应结构误当成真实字段；烟测脚本新增断言，只允许 `Stop-Process -Id $Process.Id` 清理本次应用进程，不允许按名称关闭 `TdxW.exe`/`tdxcef.exe`。
- 来源：`docs/verification/2026-08-06-sitewide-visual-evidence-redesign.md`、`apps/api/src/qibao_api/gongbu/tdx_local_professional.py`、`apps/api/tests/gongbu/test_tdx_local_professional.py`、`apps/api/tests/gongbu/test_tdx_local_overview.py`、`apps/api/tests/desktop/test_packaging.py`。

## 2026-08-11 可信决策闭环 v4.0

- `confirmed`：量化影子账本已增加评分分桶、实际命中率、Brier 误差和策略漂移检测；全局少于 20 条或单桶少于 5 条时明确显示样本不足，不宣称评分可靠。
- `confirmed`：量化候选只有同时通过市场模型、策略分、盘中触发、风险扣分、证据覆盖和硬风险六项门槛时才允许进入“可提醒”；提醒不连接下单。
- `confirmed`：新增追加式个人复盘日志和组合风险仪表盘。组合风险只使用用户手动录入持仓、本地真实日线和已核验行业证据，计算权重、HHI、相关性、机械压力和市场仓位上限；持仓保存到便携 `data/portfolio-risk.sqlite3` 并支持 GET/PUT/DELETE，空持仓不查询日线或行业数据，也没有默认模拟持仓。
- `confirmed`：公司研究已增加财务趋势、同行横向证据矩阵和透明估值机械情景；机构样本、报告时效、EPS 或同行 PE 不满足门槛时不输出区间，且明确不是目标价。
- `confirmed`：量化、公司研究和风险页面已统一数据证据水印；重复交易日、日期倒序、量额矛盾会阻断影子收益和组合风险计算，超过 35% 的收盘跳变保留原值并公开警告。
- `confirmed`：最终 API 全量为 `1241 passed, 1 skipped`，Web 为 `550 passed`，TypeScript/Vite production build、201 个修改文本文件严格 UTF-8 扫描及 `git diff --check` 通过。
- `confirmed`：正式发布数据 smoke 窗口 `320ms`、API `5143ms`、首页 `10ms`、信息总览 `4763ms`、量化 `12ms`、组合风险 `4ms`、公司研究 `4588ms`；组合风险只读 GET 诚实返回空持仓 `unavailable`，当前专业通达信插件未初始化，相关字段保持 `unavailable`，没有代理值或模拟值。
- `confirmed`：正式便携 EXE 已覆盖更新，SHA-256 为 `455A0A6A0D8B6ADCAEB2D53E131A6B3214AAE10E9C1129CB47E2FC6CB88BBFE9`；八个持久目录和持仓 SQLite 均保留，烟测后无观测台残留进程。烟测脚本只按本次应用 PID 清理，且源码不含通达信进程名，因此没有关闭、重启或控制通达信。
- 来源：`docs/verification/2026-08-11-trustworthy-decision-loop-v4.md`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 全站加载进度连续反馈

- `confirmed`：公司研究和个股观察的共享请求进度已从“响应前长期停在 1%”改为三段式：响应等待期间每 250ms 更新受限阶段估算并显示真实等待时间，最高不超过 45%；收到响应后切换真实字节；解析成功才到 100%。估算明确标注，不冒充后端完成度。
- `confirmed`：信息总览继续使用真实启动/快照阶段节点，量化候选继续优先使用后端 `processed/total`；缺少总量时不显示虚假百分比。
- `confirmed`：共享进度、公司研究和个股观察聚焦测试 `74 passed`；Web 全量 `553 passed`；API 全量 `1241 passed, 1 skipped`；生产构建、208 个变更文本文件严格 UTF-8 扫描和 `git diff --check` 通过。
- `confirmed`：构建时正式观测台正在运行，未关闭或重启用户实例。完整新版位于 `dist/XiaoQiBao-Portable-staged-d37a8871286344dab29e25f0742766b7/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 为 `3D75C1B13F19DBF21C68274BEEBF81533E2E94D1417011F12C191EF3A1B48BF8`；真实数据 smoke 窗口 351ms、API 6642ms、完整验证 20054ms。
- `confirmed`：本轮只修改前端加载反馈，已把新版 web 资源以只新增/覆盖方式同步到正式便携目录；没有替换运行中的 EXE。用户下次自行重新打开正式观测台即可加载新进度反馈。通达信进程未关闭、重启或控制。
- 来源：`docs/verification/2026-08-12-sitewide-loading-progress.md`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 性能与维护闭环 v5.0

- `confirmed`：新增统一真实任务进度契约；只有存在真实总量时才显示 `processed/total` 百分比，无总量阶段只显示状态、耗时和活动说明，终态不可回退。
- `confirmed`：公司研究重型服务从核心启动路径移出，首次访问才初始化；六区块研究任务支持旧完整缓存持续展示和真实阶段轮询。延迟包装器的业务 `get` 同名冲突已通过 RED→GREEN 回归修复。
- `confirmed`：全局运行锁已收缩为只保护写操作；所有 GET/HEAD/OPTIONS 不再互相排队。真实 EXE 量化策略请求由超过 30 秒超时恢复为 134ms，写操作仍保持串行。
- `confirmed`：实现下次启动原子更新、失败回滚和持久目录保护；实现页面/API 最近十次、P50、P95、失败率、缓存命中率；实现版本化完整快照、partial 不覆盖 complete、清理预览/确认及六类数据新鲜度策略。
- `confirmed`：最终 API 全量 `1267 passed, 1 skipped`，Web `94 files / 556 passed`，TypeScript/Vite production build、215 个变更文本文件 UTF-8/乱码扫描和 `git diff --check` 通过。
- `confirmed`：正式发布数据 EXE smoke：窗口 383ms、API 5385ms、首页 10ms、信息总览 5271ms、量化 134ms、组合风险 678ms、公司研究 11872ms、专业五类探针 1204ms；信息总览和数据源健康 ready，量化/组合风险/公司研究诚实返回 partial，专业 `Fn/GP/BK/SC/GO` 保持 unavailable，没有代理或模拟字段。
- `confirmed`：最新正式 EXE SHA-256 为 `272474B4D541D73642514C944F306D3B989199D1552EF186E8B23BCB39A62D09`；八个持久目录全部保留，烟测后无观测台或测试端口残留。用户通达信 `TdxW.exe` PID 21920 与 `127.0.0.1:17709` 监听保持运行，未关闭、重启或控制。
- 来源：`docs/verification/2026-08-12-performance-maintenance-loop-v5.md`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 事件 K 线竖线标注改版

- `confirmed`：个股事件 K 线已改为参考行情图的竖向虚线标注；事件短标题逐字纵向排列并位于虚线中部，不再只显示数字锚点，完整标题与证据仍保留在下方详情和事件记录中。
- `confirmed`：事件线继续使用与涨跌色分离的归属分类色；K 线严格保持红涨绿跌。选中事件只增强虚线宽度和文字边框，不切换成实线；同一交易日多事件合并计数，避免重叠。
- `confirmed`：API 全量 `1313 passed, 1 skipped`，Web 全量 `582 passed`，TypeScript/Vite 生产构建、聚焦 75 项关联测试、乱码扫描和 `git diff --check` 通过。
- `confirmed`：正式便携 EXE 已重建并通过真实发布数据 smoke；窗口 `338ms`、API `5369ms`、完整验证 `16293ms`，信息总览 ready，量化 partial（真实候选 1、覆盖 85%），公司研究 partial（覆盖 65%），专业通达信字段保持 unavailable。
- `confirmed`：最新正式 EXE SHA-256 为 `6C6C33F8725EA010FC5C55A36B506AC31E4EA7ACE83A4A909D66FC3C4CF4E257`；八个持久目录全部保留，未关闭、重启或控制通达信。
- 来源：`apps/web/src/features/stock-timeline/StockEventKline.tsx`、`apps/web/src/features/stock-timeline/StockEventKline.test.tsx`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 信息总览分时异动线文字修复

- `confirmed`：用户截图中的实际区域是信息总览 `OverviewMinuteChart`，此前只修改个股事件 K 线，未覆盖该组件；分时图旧配置明确使用数字 `01/02` 和顶部标签，因此看不到线中文字。
- `confirmed`：信息总览上证指数分时图现已改为竖向虚线中部显示事件简称，逐字纵排；选中事件保持虚线，仅增强线宽、亮度和文字边框。右侧异动记录继续保留编号用于对应详情，同分钟多事件以 `+数量` 合并。
- `confirmed`：相关 73 项测试、Web 全量 `582 passed`、API 全量 `1313 passed, 1 skipped`、TypeScript/Vite 构建、乱码扫描和 `git diff --check` 通过。
- `confirmed`：当前正式观测台正在运行，未关闭或控制；新版已构建到暂存发布并登记为下次启动原子更新。暂存版 smoke 窗口 `347ms`、API `5431ms`、完整验证 `14533ms`，信息总览 ready；SHA-256 为 `823F40747486022295EF1EE4D654DAD76E93EFF7D0E2EDC0ECAF26EEEAA23041`。
- 来源：`apps/web/src/features/market-overview/OverviewMinuteChart.tsx`、`apps/web/src/features/market-overview/OverviewMinuteChart.test.tsx`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 板块四象限可读性统一修复

- `confirmed`：板块精选“板块强度四象限”、板块赛道“涨幅与广度矩阵”和强度风口“强度与扩散”已统一移除固定 0-100 坐标、角落聚集的编号散点和拥挤图例，改为以当日真实样本中位数划分的 2×2 决策矩阵。
- `confirmed`：每个象限直接展示板块名称、实际涨跌幅、上涨广度、涨停数量和有效样本数；强度风口额外展示涨停密度。页面会公开当前样本阈值，卡片可以直接阅读，不再需要用编号反查图例。
- `confirmed`：板块精选语义为“主线扩散 / 核心抱团 / 普涨偏弱 / 弱势收缩”；板块赛道为“赛道领涨 / 局部抱团 / 广度修复 / 赛道退潮”；强度风口为“涨停扩散 / 龙头集中 / 跟涨扩散 / 风口退潮”。强度分大量饱和为 100 时自动回退到真实涨跌幅进行强弱分层，避免满分失真。
- `confirmed`：相关聚焦测试 `37 passed`，关联测试 `82 passed`，API 全量 `1313 passed, 1 skipped`，Web 全量 `584 passed`，TypeScript/Vite 构建、乱码扫描和 `git diff --check` 通过。
- `confirmed`：当前正式观测台仍在运行，未关闭或控制；新版已登记为下次启动原子更新，暂存发布位于 `dist/XiaoQiBao-Portable-staged-3f5f32a0a65348fba54e30d3897877b3/XiaoQiBao-Portable`。真实发布数据 smoke 窗口 `60ms`、API `3717ms`、完整验证 `10246ms`，信息总览 ready；EXE SHA-256 为 `39B50E6A4ECEA1B01F52BCBF1D877DEEE33ED8C598EC7891D2378D202F5BFA6B`。通达信未被关闭、重启或控制。
- 来源：`apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`、`apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`、`apps/web/src/features/market-overview/overview.css`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 异动统计四项同排修复

- `confirmed`：异动统计透视只有四项，但共用统计组件固定为三列，导致“关联题材”单独掉到第二行并产生大块空白；根因不是数据缺失。
- `confirmed`：仅为四项异动统计增加桌面端四列等宽布局，保留其他六项复盘统计的三列结构；小于 650px 时按 2×2 自适应，避免窄屏挤压。
- `confirmed`：新增回归先验证旧结构缺少四列类，再完成修复；聚焦测试 `38 passed`，Web 全量 `585 passed`，API 全量 `1313 passed, 1 skipped`，TypeScript/Vite 构建、乱码扫描和 `git diff --check` 通过。
- `confirmed`：正式观测台运行中未被关闭；新版已登记为下次启动原子更新。暂存版 smoke 窗口 `321ms`、API `5603ms`、完整验证 `16703ms`；EXE SHA-256 为 `0400F7CB0B64A01CF6B3B330126D12E3DFB68A1FB116568A8A9F0F5352865B39`。通达信未被关闭、重启或控制。
- 来源：`apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`、`apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`、`apps/web/src/features/market-overview/overview.css`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 信息总览同排卡片等高修复

- `confirmed`：百日新高趋势、个股异动、游资追踪、游资动向、龙虎榜等工作区的同排双栏此前使用 `align-items: start`，短卡片不会随同排长卡片拉伸，因而露出网格底色并形成明显高低差。
- `confirmed`：信息总览通用工作区网格已改为桌面端同排卡片自动等高；小于 650px 的单列布局恢复自然内容高度，个股档案证据区原有紧凑例外继续保留。
- `confirmed`：Web 全量 `586 passed`，API 全量 `1313 passed, 1 skipped`，TypeScript/Vite 生产构建、乱码扫描和 `git diff --check` 通过。
- `confirmed`：正式便携 EXE 已重建并通过真实发布数据 smoke；窗口 `64ms`、API `1941ms`、完整验证 `9697ms`，信息总览 ready；EXE SHA-256 为 `280629AC29C649FF9601579007E6D0BB07E760637995CC6BF6EACF749CB5B9C9`。通达信未被关闭、重启或控制。
- 来源：`apps/web/src/features/market-overview/overview.css`、`apps/web/src/app/layout-safety.test.ts`、`apps/web/src/features/market-overview/MarketOverviewView.test.tsx`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 七大人气榜主次纵向布局

- `confirmed`：七大人气榜的“重复上榜矩阵”是主要股票数据，“榜单口径说明”只是审计信息；旧版把两者各占半行并强制等高，导致审计区下方出现大片无意义留白，也压缩了矩阵展示宽度。
- `confirmed`：该页面改为三段整行结构：七大人气榜单、重复上榜矩阵、榜单口径说明依次各占完整一行；主数据可铺满窗口，审计说明保留在下一行，不影响其他确实需要双栏对比的页面。
- `confirmed`：Web 全量 `587 passed`，API 全量 `1313 passed, 1 skipped`，TypeScript/Vite 构建、乱码扫描和 `git diff --check` 通过。
- `confirmed`：正式便携 EXE 已重建并通过真实发布数据 smoke；窗口 `346ms`、API `5497ms`、完整验证 `14721ms`，信息总览 ready；EXE SHA-256 为 `29862CB406DC544818BD8B56F04795FEA24E08F5B9467B50A9230B3009427A66`。通达信未被关闭、重启或控制。
- 来源：`apps/web/src/features/market-overview/workspaces/workspaceRegistry.ts`、`apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 信息总览多页面主次布局审计

- `confirmed`：根据 13 张最大化窗口截图，确认多个页面把主表、矩阵、图表与短审计卡机械地放在同一半行，等高后产生大片灰色空区；问题属于内容层级与栅格跨度不匹配，不是数据缺失。
- `confirmed`：AI+题材、隔夜单/抢筹、竞价选股、板块赛道、连板表现、龙头晋级、炸板、昨涨停、连板梯队、首板梯队、放量突破、突破前高、低位放量和龙虎榜均改为主数据优先整行，摘要与审计随后独立整行；热点解读改为原始资讯整行，题材归因与行情验证双栏，完整证据链收尾整行。
- `confirmed`：竞价封单改为开盘强度对照先占整行，竞价封板状态与字段审计只在信息量接近时并排，强势股票清单再占整行。
- `confirmed`：非研产业库的产业主题地图从固定五列跨栏改为三列密集自动填充，中心主题卡跨两行，其余主题卡自动补位，不再在尾行保留空单元格。
- `confirmed`：聚焦布局测试 `90 passed`；Web 全量 `591 passed`，API 全量 `1313 passed, 1 skipped`，TypeScript/Vite 构建、乱码扫描和 `git diff --check` 通过。
- `confirmed`：正式便携 EXE 已重建并通过真实发布数据 smoke；窗口 `314ms`、API `5418ms`、完整验证 `14512ms`，信息总览 ready；EXE SHA-256 为 `98034F465AF516A0F72C01B6D665F7ECDE4927D7A524110D90663587A10534E0`。通达信未被关闭、重启或控制。
- 来源：`apps/web/src/features/market-overview/workspaces/workspaceRegistry.ts`、`apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`、`apps/web/src/features/market-overview/overview.css`、`apps/web/src/app/layout-safety.test.ts`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 首次涨停明细筛选与固定详情

- `confirmed`：首次涨停摘要中的“已识别涨停、规则合格、回撤窗口、涨停日禁买”已由静态数字改为可点击筛选入口；点击后自动切换到正确分组，只展示对应真实股票，并自动打开首只股票的完整规则证据。列表标题明确显示当前筛选和匹配数量，可一键“查看全部”。
- `confirmed`：筛选口径与后端统计保持一致：规则合格来自本次识别结果的 `selection_status=qualified`，回撤窗口来自历史观察池的 `stage=pullback_window`，涨停日禁买来自本次识别结果的 `action=no_buy`；不跨批次拼接或生成替代数据。
- `confirmed`：桌面端候选列表改为独立滚动区，右侧详情保持固定可见且自身可滚动；窄窗口恢复单列自然布局，避免双滚动和内容截断。
- `confirmed`：API 全量 `1313 passed, 1 skipped`，Web 全量 `593 passed`，TypeScript/Vite 生产构建、聚焦测试、UTF-8 乱码扫描和 `git diff --check` 通过。
- `confirmed`：正式便携 EXE 已重建并通过真实发布数据 smoke；窗口 `324ms`、API `5446ms`、完整验证 `16209ms`，信息总览 ready，量化 partial（真实候选 6、覆盖 85%），公司研究 partial（覆盖 65%），专业通达信字段保持 unavailable。EXE SHA-256 为 `1A649444727776044D8EECA7EC72596E5D62CC5C3B7B5225D43545D6304528FA`，八个持久目录全部保留，烟测后无观测台测试进程或端口残留；未关闭、重启或控制通达信。
- 来源：`apps/web/src/features/first-limit-up/FirstLimitUpView.tsx`、`apps/web/src/features/first-limit-up/FirstLimitUpView.test.tsx`、`apps/web/src/app/theme.css`、`apps/web/src/app/layout-safety.test.ts`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 信息总览平铺菜单与自适应密度统一

- `confirmed`：信息总览继续保留 50 个一级平铺菜单的既有名称、顺序和路由键，不重新分类、不增加层级；此前用于界面显示的“开盘检查、条件选股、高开缺口”等别名已撤销，能力边界说明只保留在提示信息中。
- `confirmed`：信息总览内容区新增宽度驱动的统一密度规则。菜单等宽自动换行；普通指标卡、洞察卡、空状态和排名图取消无必要的固定高空白；表格使用 `clamp` 高度与内部滚动；窄窗口按双列或单列降级，不改变页面数据和业务结构。
- `confirmed`：首板分布仪表改为紧凑 2×2 横向指标卡，派生数值统一最多保留两位小数；桌面端和窄窗口均有布局回归测试。
- `confirmed`：Web 全量 `101 files / 596 passed`，TypeScript/Vite 生产构建、乱码扫描和 `git diff --check` 通过。
- `confirmed`：正式便携 EXE 已重建并通过真实发布数据 smoke；窗口 `355ms`、API `5475ms`、完整验证 `16312ms`，信息总览 ready，量化 partial（真实候选 6、覆盖 85%），公司研究 partial（覆盖 65%），专业通达信字段保持 unavailable。EXE SHA-256 为 `C8D879B8586BBAA5FEEB0787007867760EAE4347C8C0A82A44411670CCEC471B`，八个持久目录全部保留；未关闭、重启或控制通达信。
- 来源：`apps/web/src/features/market-overview/featureCatalog.ts`、`apps/web/src/features/market-overview/overview.css`、`apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`、`apps/web/src/app/layout-safety.test.ts`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 个股异动主次纵向布局

- `confirmed`：个股异动页左侧榜单下方大片空白并非数据缺失，而是“个股异动榜”与较长的“个股异动解释线索”共用半宽同排且被等高规则拉伸；新闻高度撑开整排后，短榜单暴露出无意义空区。
- `confirmed`：页面现改为三段整行结构：振幅-涨幅异动矩阵、个股异动榜、个股异动解释线索依次各占完整一行；不修改数据源、业务逻辑或全站通用等高规则。
- `confirmed`：聚焦测试 `44 passed`，Web 全量 `101 files / 597 passed`，TypeScript/Vite 生产构建、UTF-8 检查和 `git diff --check` 通过。
- `confirmed`：正式观测台运行中未被关闭；新版已登记为下次启动原子更新。暂存版真实发布数据 smoke 窗口 `338ms`、API `5804ms`、完整验证 `17249ms`，信息总览 ready；EXE SHA-256 为 `7A82F719868B4CAE30B63105B74C0A39E31CB9AF2DD2CD47D1EBFEDFA0CC4879`。八个持久目录全部保留，通达信未被关闭、重启或控制。
- 来源：`apps/web/src/features/market-overview/workspaces/workspaceRegistry.ts`、`apps/web/src/features/market-overview/workspaces/DistinctMarketWorkspace.test.tsx`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。

## 2026-08-12 信息总览菜单位置交换

- `confirmed`：信息总览一级平铺菜单中，“板块资金动图”与“隔夜单/抢筹”已精确交换位置；菜单名称、稳定键、页面内容和数据逻辑均未改变。
- `confirmed`：由于旧元数据默认继承所在行分类，本轮为两项菜单显式保留真实业务归属：“隔夜单/抢筹”仍属于竞价与盘中，“板块资金动图”仍属于题材、板块与资金，避免仅换位置后语义串类。
- `confirmed`：Web 全量 `101 files / 597 passed`，TypeScript/Vite 生产构建、UTF-8 检查和 `git diff --check` 通过。
- `confirmed`：正式便携 EXE 已重建并通过真实发布数据 smoke；窗口 `318ms`、API `5561ms`、完整验证 `16573ms`，信息总览 ready。EXE SHA-256 为 `2779664F58149DDB08B089BD0330BA5CA4F5CB3C4C9E346492D4945EFD810E53`，八个持久目录全部保留，烟测端口已释放；通达信未被关闭、重启或控制。
- 来源：`apps/web/src/features/market-overview/featureCatalog.ts`、`apps/web/src/features/market-overview/featureCatalog.test.ts`、`task:019f59b1-db6e-78f2-9b0f-9c46e36657f1`。
