---
type: project-memory
status: confirmed
updated: 2026-09-04
project_path: "D:/Users/90090/Documents/ChatGPT/A股平台"
sources: ["task:01a03785-a8a0-7a42-88d4-836458a08fb1", "project:金融财经-read-only-reference"]
tags: [project-memory, finance, a-share, desktop, tauri]
---

## 2026-09-03 独立 Walk-forward 验证链路

`confirmed`：量化分析页新增独立按需 Walk-forward 链路。Rust 用例 `run_walk_forward.rs` 复用本地通达信日线读取、统一交易成本和时间顺序 70%/30% `chronological_holdout` 领域函数；Tauri `run_walk_forward` 命令只负责平台根目录解析与调用。前端 `quant-walk-forward-store.ts` 负责参数门禁、同请求 Promise 去重、失败时保留 last-good 并标记 `stale`、响应隔离；`WalkForwardPanel.svelte` 仅提供“运行验证”按钮和状态展示，不新增轮询或网络请求。

`confirmed`：历史不足、来源不可用和成本/交易日历缺失继续保留 `missing/unavailable/partial` 真实状态，不生成随机验证结果；回测页仍可独立运行，Walk-forward 不再只能被动读取回测结果里的内嵌字段。

`confirmed`：新增前端 Store 单元测试和跨层合同测试；`quant-walk-forward-store.test.ts` 3 项通过，`quant-walk-forward-contract.test.mjs`、TypeScript 编译、Rust `cargo check -p yishu-desktop --offline`、定向 Rust 测试、`cargo fmt --all -- --check`、文件登记检查和 `git diff --check` 均通过。未修改参考项目、用户数据，未执行 Git 提交。

`observed`：量化策略目录和量化研究快照仍是 feature-map 标记的未接线缺口，后续应继续新增独立 Store/IPC，不应把研究逻辑并入 Walk-forward 文件。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/quant-analysis/quant-walk-forward-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/run_walk_forward.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/quant-walk-forward-contract.test.mjs`。

## 2026-09-03 设置页原生目录选择器跨平台接线

`confirmed`：设置页“通达信只读目录”新增平台中立的“选择目录”入口，前端通过 `select_directory` 唯一 IPC 请求目录，不直接接触 Windows/macOS API；手动粘贴路径仍保留为后备方式。Windows 实现收拢在平台层并调用隐藏 PowerShell `System.Windows.Forms.FolderBrowserDialog`，macOS 实现调用 `osascript choose folder`，统一校验绝对路径、目录存在性和取消状态。

`confirmed`：新增目录选择器客户端、Vitest 测试、Rust 平台适配和架构合同；命令使用 `spawn_blocking`，不会阻塞 UI 线程。定向 Node 合同、前端客户端测试、Rust 平台测试和 Vite 构建通过；文件注册表已登记新增生产源文件。未修改参考项目，未执行 Git stage/commit/push，未生成安装包或 ZIP。

`observed`：当前环境只对 Windows 代码路径完成编译测试，macOS 适配代码通过条件编译保留但尚未进行 macOS 实机验证；系统策略禁用 PowerShell 或用户取消时，界面保留可见错误并允许手动输入。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/shared/settings/directory-picker-client.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/platform/directory_picker.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/settings/SettingsPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/settings-directory-picker-contract.test.mjs`。

## 2026-09-03 市场脉冲同刻事件版本门禁修复

`confirmed`：统一行情脉冲前端事件门禁不再只依赖 `observedAt` 严格递增。时间更晚的有效快照直接接受；同一时间戳下仅当快照内容发生变化时接受，完全重复事件仍拒绝，空载荷和非法时间继续拒绝。这样可避免后端在同一秒内连续发出不同真实快照时被前端丢弃，同时不引入额外请求或轮询。

`confirmed`：新增同刻内容变化回归测试，定向事件测试 3 项通过；文件登记已同步更新。后续若需要更低的序列化开销，可在跨层契约增加单调 `sequence` 字段，但当前实现保持兼容既有事件格式。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/market-pulse-events.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/market-pulse-events.test.ts`。

## 2026-09-03 核心指数核验默认折叠复核

`confirmed`：本轮独立复核确认 `GlobalMarketPulse.svelte` 的核心指数双来源核验默认状态仍为关闭；浏览器重新加载 `market-overview` 后，外层行情详情、来源详情、告警和其他 `details` 均未自动展开。展开外层行情详情时，内层核验状态会被重置为关闭；只有用户主动点击核验标题才显示五个指数的腾讯/东方财富明细。真实数据对比链路和五态状态未改变。

`confirmed`：本轮验证通过：双来源折叠合同、前端 Vitest 219 个文件/880 项、Vite 生产构建 4033 个模块、Rust `cargo check -p yishu-desktop --offline`、架构命令合同、文件登记、UTF-8 编码扫描、`cargo fmt --all -- --check` 和 `git diff --check`。未修改参考项目、用户数据或运行时缓存，未执行 Git stage/commit/push，未生成安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-index-confirmation-fold-contract.test.mjs`。

## 2026-09-03 量化决策日志真实闭环

`confirmed`：量化分析页已移除“暂无日志”占位，新增独立量化决策日志模块。前端由 `QuantDecisionJournalPanel.svelte`、类型、IPC client 和 Store 分工负责；支持用户手工新增、编辑、删除和读取最近日志。日志不自动生成研究结论，状态保留 `ready/partial/stale/missing/unavailable`。

`confirmed`：后端新增跨端 DTO、SQLite `0006_quant_decision_journal` 迁移、参数化 CRUD 存储、输入校验和四个 Tauri IPC 命令；用户业务数据库与程序目录继续隔离。修复创建记录误用 `execute` 返回值导致 ID 重复的缺陷，改用 SQLite `last_insert_rowid()`，连续新增记录回归测试通过。

`confirmed`：量化日志合同、Rust contracts 测试、桌面库单元测试、前端 client 测试、桌面生产构建、架构登记、编码扫描、格式检查和差异检查通过。一次完整桌面测试的二进制链接阶段曾受 Windows 页面文件 OS 1455 阻断，随后使用 `--lib` 定向测试完成日志数据库行为验证；该环境限制不改变源码编译结果。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/quant-analysis/QuantDecisionJournalPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/database/quant_decision_journal.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/quant-decision-journal-contract.test.mjs`。

## 2026-09-03 功能地图与真实 IPC 接线闭合

`confirmed`：`docs/architecture/feature-map.yaml` 已补齐量化、风险、历史、监控、设置、运维和可转债菜单的实际 Tauri 命令，并移除数据大屏已不存在的 `load_market_attention` 命令。复合用例、Store 行为、前端投影和内部副作用通过 `implementation_notes` 明确标注，避免把一个复合命令误写成多个独立 IPC。

`confirmed`：`tests/architecture/feature-map-command-contract.test.mjs` 现在要求全部 15 个主菜单声明实现命令，并要求每个 `use_case` 要么对应直接命令，要么在复合/投影/未实现说明中明确记录；所有登记命令均在 Tauri `lib.rs` 注册。监控刷新只对 `ready/partial` 且存在真实快照的行情执行规则评估，缺失字段不会推进恢复状态或写入伪审计。

`observed`：公司研究后台任务、尾盘 AI 分析、量化决策日志、设置页系统目录对话框和运维性能独立面板仍是明确的未实现或复合替代边界，地图已记录原因，后续应按独立模块继续补齐。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/feature-map.yaml`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/architecture/feature-map-command-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_movements.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/evaluate_monitor_rules.rs`。

## 2026-09-03 核心指数核验截图默认折叠状态收口

`confirmed`：核心指数双来源核验明细新增组件级 `indexConfirmationOpen = false` 状态，并通过 Svelte `bind:open` 控制原生折叠面板；外层行情详情由 `marketDetailOpen` 管控，每次重新打开行情详情时都会先重置内层核验为关闭。页面首次渲染、路由复用或截图采集时均默认关闭，仅保留一致数量摘要和真实双源自动对比说明；用户主动点击后才展开五个指数的腾讯/东方财富明细。未新增请求、不改变真实数据和状态语义。

`confirmed`：新增回归合同覆盖默认关闭状态、无 `open` 属性误展开和按需明细结构；定向合同、桌面端生产构建（4025 个模块）、UTF-8 扫描及 `git diff --check` 通过。预览页在数据源不可用时未渲染虚假明细，保持真实 `unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-index-confirmation-fold-contract.test.mjs`。

## 2026-09-03 全局行情刷新按路由生命周期节流

`confirmed`：`App.svelte` 为实时行情相关菜单建立 `liveMarketRoutes`，`GlobalMarketPulse.svelte` 新增 `live` 生命周期属性。非行情菜单仍显示最近一次有效行情快照，但会暂停共享行情脉冲自动刷新；进入行情、研判、个股、监控等相关菜单时恢复刷新，组件销毁时恢复默认刷新所有权。此改动不新增请求，不改变真实状态语义，降低后台页面的网络、CPU 与 IPC 消耗。

`confirmed`：新增并登记 `tests/features/global-market-pulse-route-lifecycle-contract.test.mjs`，全量测试 218 个文件/878 项通过，桌面端生产构建处理 4025 个模块通过，架构登记 1904 条、编码扫描和 `git diff --check` 通过。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/App.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/global-market-pulse-route-lifecycle-contract.test.mjs`。

## 2026-09-03 核心指数双来源核验独立折叠

`confirmed`：信息总览中的“核心指数双来源核验”已从行情详情内容中独立为二级折叠区，默认只显示“一致数量/总数”和“项目自动对比腾讯与东方财富真实数据”摘要；用户主动展开后才渲染五个指数的主源、副源、差异与缺失字段明细。未改变真实数据对比、状态语义或刷新链路，不新增请求。

`confirmed`：新增并登记 `tests/features/overview-index-confirmation-fold-contract.test.mjs`，字号旧合同已统一到当前 `--font-body: 13px` 设计；定向合同、全量测试（218 个文件/878 项）、架构登记（1903 条）、UTF-8 扫描、`git diff --check` 和桌面端 Vite 构建（4025 个模块）均通过。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-index-confirmation-fold-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/file-registry.yaml`。

## 2026-09-03 信息总览动效、滚动与 Windows x64 阶段验收

`confirmed`：信息总览已采用页面级纵向滚动、家族标签与贴纸式工作区导航；通用表格只保留必要的横向滚动。默认折叠来源诊断、工程状态、次级行情与证据信息，首屏优先保留情绪、核心行情、事件与工作区入口。背景包含低干扰粒子、科技网格、缓慢扫描线及四角装饰；数据更新采用数字跳动、行闪烁和图表平滑过渡。视觉效果遵从页面可见性与 `prefers-reduced-motion` 降级，未引入重型 UI 库或额外行情轮询。

`confirmed`：监控规则评估复用共享 `load_market_movements` 真实异动快照，不增加行情请求或定时器；仅投影可靠的价格、涨跌幅和换手率，缺失值保持缺失，`stale/missing/unavailable` 快照不产生新告警。更新器的健康检查提示改为“新版本进程在健康确认前退出”，避免把未完成健康确认误称为版本启动失败。

`confirmed`：Windows x64 EXE-only 构建、更新器文案合同、桌面 Vitest、架构登记、UTF-8 扫描、差异检查及启动/激活/回滚烟测已在本次任务中重新执行。构建日志包含既有 Rust unused/deprecated 警告，但命令无错误退出。后续阶段验收目录应只引用与当前 `target/release` 哈希一致的副本；不生成安装包或 ZIP，未执行 Git stage/commit/push。

`observed`：真实行情的更新频率继续受已接入数据源与市场时段约束；开发模式的显式预览模拟器不会作为实时事实展示。完整交易所逐笔、多源原子快照、完整 AI 外部可用性和 macOS 实机验证仍保持 `partial/stale/missing/unavailable` 的真实边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/theme.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/bin/yishu-updater.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/run-windows-smoke.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/smoke-updater.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/updater-health-message-contract.test.mjs`。

## 2026-09-03 信息总览首屏紧凑化与滚动归属复核

`confirmed`：信息总览核心行情带保留情绪值与四项核心市场指标，搜索和来源状态收纳到紧凑状态栏；来源诊断、指数/指标/双源核验默认折叠。中等宽度自动三列换行并移除横向滚动陷阱；工作区贴纸导航和工具栏在 1280x720 首屏可达。浏览器实测页面无横向溢出，业务面板未捕获纵向鼠标滚轮，仅侧栏和必要宽表保留滚动。

`confirmed`：新增并登记 `tests/features/overview-scroll-ownership-contract.test.mjs`，已接入根 `pretest` 与 `test`；首屏紧凑、滚动归属、视觉、全息动效、图表动效、工作区运行时和监控刷新合同均通过。架构登记 1900 条，UTF-8 扫描通过，桌面端生产构建处理 4025 个模块，前端 Vitest 全量通过。

`confirmed`：最新 Windows x64 EXE-only 验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260903-125700`，包含主程序、更新助手和后台采集器三个 PE `0x8664` EXE 及 `BUILD-INFO.txt`。启动 smoke、更新器激活、用户配置保留和失败回滚 smoke 通过；未生成安装包或 ZIP，未修改参考项目、用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：`scripts/run-windows-smoke.ps1` 的控制台会显示“新版本启动失败: exit code: 0”提示，但脚本整体退出成功，且后续更新器状态表明确显示 committed 与 rolled_back 两条路径通过；需后续清理该提示文案以避免误导。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-scroll-ownership-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/file-registry.yaml`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260903-125700/BUILD-INFO.txt`。

## 2026-09-03 Windows x64 EXE 阶段验收产物

`confirmed`：基于当前源码完成 Windows x64 EXE-only release 构建，验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260903-001500`。主程序 `yishu-desktop.exe` 为 33,264,640 bytes，SHA-256 `C67DAFE0E250DC5E9CE70E0989CCC34C161B23252558CE0E16DABAE3B6466000`；更新助手 `yishu-updater.exe` 为 675,840 bytes，SHA-256 `56F3D777048258CD48AFDC4CF652117AFB8D12B4C673659A536A68892AFDF473`；后台快讯采集器 `yishu-news-collector.exe` 为 7,112,192 bytes，SHA-256 `B6D9B5C436FCC7F9BAF3D50B7C35403DB0A21A14A6FDCAE3631B7A5403E7E559`。三件 PE machine 均为 `0x8664`。

`confirmed`：Windows EXE-only 合同、Rust/Tauri release 构建、前端生产构建（4025 modules）、前端 Vitest（218 文件/878 项）、架构登记、UTF-8 扫描、`git diff --check`、主程序启动 smoke、更新器激活/用户配置保留/失败回滚 smoke 均通过。仅生成三个 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP；参考项目、用户配置、缓存和业务数据未修改，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260903-001500/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/run-windows-smoke.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`。

## 2026-09-03 个股观察秒级行情快照通道

`confirmed`：参考会话中的后台轮询与内存快照方案已落到当前项目。新增 `StockRealtimeQuoteService`，后台按 3 秒周期批量读取当前活跃股票，前端请求只读内存，不在请求线程重复访问上游；同一股票重复观察会合并为一个活跃订阅，活跃订阅超过 180 秒未触碰会自动回收。

`confirmed`：腾讯行情源新增最多 60 只股票的批量读取，并保持 GBK 严格解码。新增 `/api/v1/a-shares/{symbol}/quote-pulse` 轻量接口和 `stock_quotes` SSE 主题，仅推送价格、涨跌、成交量、换手率、市值及观测时间。上游短暂失败时保留最近一次有效快照并标记 `stale`，没有成功快照时明确标记 `unavailable`，不伪造行情。

`confirmed`：个股观察首次完整研判仍按原流程加载；秒级通道只更新行情字段，不触发财务、新闻、历史走势和 AI 重算。SSE 断线时前端每 3 秒请求轻量接口作为保底，组件卸载会取消请求和定时器。

`confirmed`：后端 1779 项测试通过（含新增快照服务与路由测试），前端 139 个测试文件/846 项通过，Ruff、TypeScript、Vite 生产构建和 `git diff --check` 通过。便携 EXE 已重建至 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`；最终冷启动烟测通过，窗口 384ms 可见、API 5958ms 就绪、14 菜单检查通过，退出后无 `xiaoqibao.exe` 残留。未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：真实行情可用性仍受腾讯上游和交易时段影响；秒级表示后台快照与界面响应路径，不代表上游供应商在非交易时段持续产生新成交。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/api/src/qibao_api/a_shares/stock_realtime.py`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/api/src/qibao_api/gongbu/tencent_quotes.py`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-03 板块广度与主线变化高亮

`confirmed`：数据大屏左侧“板块广度与主线”对实时市场快照的前十板块建立内容签名，比较名称、领涨股、涨跌幅、涨跌家数和成交额等字段；首次载入只建立基线，不触发全量高亮。后续仅发生变化或新出现的板块逐项进入高亮状态，独立持续 10 秒后自动恢复普通样式；同一板块在 10 秒内再次变化会重置计时，组件卸载会清理计时器。高亮使用金色边框与轻微内发光，避免长期挂屏刺眼闪烁。

`confirmed`：前端 Vitest 139 个文件/845 项通过；Vite 生产构建通过；便携 EXE 已重建至 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`；冷启动烟测通过，窗口 109ms 可见、API 2758ms 就绪、14 菜单检查通过，退出后无 `xiaoqibao.exe` 残留。未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：烟测中的部分真实数据源仍可能返回 `unavailable/partial`，这是数据源状态边界，不等同于高亮逻辑异常；视觉高亮不伪造实时行情。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/sectorHighlights.ts`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。
## 2026-09-02 23:01 最新滚动收口版 Windows x64 EXE

`confirmed`：包含个股详情内层滚动收口和功能地图命令合同的最新源码已完成 EXE-only release 构建，验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-230125`。`yishu-desktop.exe` 为 33,264,640 bytes，SHA-256 `7BE5D0B8E824905D5CA83D2301BF9B599ACF524B66ADFC42CFE8224DBAD6B54D`；`yishu-updater.exe` 为 675,840 bytes，SHA-256 `D3B901EC012DFCE72E7DE0B1E44D1AB11E64EE245754EB5C6A056A27D1633953`；`yishu-news-collector.exe` 为 7,112,192 bytes，SHA-256 `92127966FE04971097A968A3D2164278A994987DD7FDA3C6F25BA3A162B7EDDD`。三件 PE machine 均为 `0x8664`。

`confirmed`：主程序启动 2500ms 后保持存活且主窗口句柄有效；更新器激活、用户配置保留和失败回滚 smoke 通过；前端 218 个测试文件/878 项测试通过，生产构建处理 4025 个模块；功能地图命令合同、架构登记、编码扫描和 `git diff --check` 通过。未生成安装包或 ZIP，参考项目和用户数据保持不变，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-230125/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/smoke-updater.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/architecture/feature-map-command-contract.test.mjs`。

## 2026-09-02 22:55 功能地图命令登记闭合

`confirmed`：新增 `tests/architecture/feature-map-command-contract.test.mjs`，逐项校验 `docs/architecture/feature-map.yaml` 中的 `implementation_commands` 是否在 Tauri `lib.rs` 注册，并校验前端投影路径存在。修正数据大屏登记：移除不存在的 `load_market_attention` 命令，改为由 `load_market_overview`、`load_market_movements`、`load_market_limit_ecology` 提供数据，`market-attention-store.ts` 负责共享状态投影，避免重复网络请求。

`confirmed`：`pnpm check:architecture`、功能地图专门合同、`pnpm check:encoding`（4645 个文本文件）和 `git diff --check` 通过。未修改参考项目、用户配置、缓存或业务数据，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/feature-map.yaml`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/architecture/feature-map-command-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/package.json`。

## 2026-09-02 22:49 个股详情内层滚动收口

`confirmed`：个股观察与公告详情相关子面板已清理业务内层纵向滚动：TDX 分笔、成交明细、复权日线、事件影响事实列表、事件证据列表和公告正文均改为页面级纵向滚动；宽表仍保留必要的横向滚动，侧栏滚动保持不变。这样鼠标滚轮不会在多个嵌套容器之间误切换。

`confirmed`：前端 218 个测试文件、878 项测试通过；`pnpm check:encoding`（4644 个文本文件）、`pnpm check:registry`（1896 条登记）和 `git diff --check` 通过。未修改参考项目、用户配置、缓存或业务数据，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/theme.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-tdx-transaction.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-trade-detail.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/AnnouncementDetailPanel.svelte`。

## 2026-09-02 22:34 Windows x64 阶段验收 EXE

`confirmed`：基于当前源码完成 Windows x64 EXE-only release 构建，验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-223414`。主程序 `yishu-desktop.exe` 为 33,264,640 bytes，SHA-256 `1FEFBBF42B188FCE1CE3101906EE04D85C7EDB45D09CD0CF2C359D206DE23310`；更新助手 `yishu-updater.exe` 为 675,840 bytes，SHA-256 `7FAB74B9A7B95C2E2C665AE2A94BA0B81DF89776302A24400728C0E37412D928`；后台快讯采集器 `yishu-news-collector.exe` 为 7,112,192 bytes，SHA-256 `8C7A9871D8F779C5A020F0F39494EDD5E6415F82C664A7E5E114BBC688C6552C`。三件 PE machine 均为 `0x8664`。

`confirmed`：EXE-only 构建合同、更新器激活与失败回滚 smoke 均通过；主程序从独立验收目录启动 2500ms 后进程存活且主窗口句柄有效，随后已清理无残留。验收目录仅包含三个 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP；参考项目、用户配置、缓存和业务数据未修改，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-223414/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/smoke-updater.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`。

## 2026-09-02 18:05 更新助手 release smoke 路径修复

`confirmed`：`scripts/smoke-updater.ps1` 现在优先使用 `target/release/yishu-updater.exe`，仅在 release 不存在时回退 `target/debug/yishu-updater.exe`；当前 release 更新助手成功激活与健康超时回滚 smoke 均通过，用户配置保持不变。随后 `scripts/run-windows-smoke.ps1` 的主程序启动和更新子步骤全部通过，临时目录已清理。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/smoke-updater.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/run-windows-smoke.ps1`。

## 2026-09-02 14:10 全息卡片性能与行情状态终审修复

`confirmed`：共享卡片主体已移除每卡常驻双动画、10px 背景模糊和 `filter` 竞争；霓虹边框与呼吸辉光隔离到伪元素，顶层/显式重点卡片保持持续动效，普通子卡片仅在悬停或键盘焦点时启动，呼吸只动画透明度与阴影。顶层 `.surface` 模糊降至 4px，低动态偏好会显式停用两个装饰层。

`confirmed`：全局行情条已区分 `missing`（暂无数据）与 `unavailable`（数据源不可用）；行情数字只在情绪、覆盖率、核心统计、指数/涨跌、关键指标和双来源报价/涨跌节点上使用精确动画标记，股票代码与观测时间不参与数字跳动。

`confirmed`：两份直接合同、TypeScript、Vite 生产构建（4013 个模块）、文件登记（1876 条）、UTF-8 编码扫描（4609 个文本文件）和 `git diff --check` 通过。未修改数据源、Store、IPC、定时器、依赖、参考工程或用户数据，未执行 Git 写操作。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/theme.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/final-review-motion-performance-fix-report.md`。

## 2026-09-02 11:13 Windows x64 当前进度 EXE 验收

`confirmed`：基于当前源码执行 EXE-only release 构建，前端 Vite 生产构建处理 4002 个模块，Rust/Tauri release 构建退出码为 0。阶段验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-111312`，主程序 `yishu-desktop.exe` SHA-256 `41AEA068F60F060D8F4CC3AD43159F04C539BDB805CB1D29FBDBF06BD8E19980`（33,113,600 bytes），更新助手 `yishu-updater.exe` SHA-256 `41F7DC59F0961C7D2D5F6B3B406D373B8881603C44770876E825092A64EC9E33`（675,840 bytes），后台快讯采集器 `yishu-news-collector.exe` SHA-256 `B40205F40804ABCFA7D7CE3192CE305F0143FD27B1DD4B985C76FE95682682B9`（7,127,552 bytes）。

`confirmed`：主程序 PE machine 为 `0x8664`；从独立验收目录启动 2500ms 后进程存活且主窗口句柄有效，清理后无同路径残留进程。EXE-only 发布合同、编码扫描（4582 个文本文件）和 `git diff --check` 通过。本轮仅生成三个 EXE，未生成安装包或 ZIP，未修改参考项目、用户配置、缓存或业务数据，未执行 Git commit/stage/push。

`observed`：release 编译仍包含既有 unused/deprecated 警告，但没有构建错误；远程更新服务完整配置、完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-111312/yishu-desktop.exe`。

## 2026-09-02 10:20 数据大屏钻取与 Windows x64 EXE 验收

`confirmed`：数据大屏的盘中异动雷达、今日涨停和活跃行情三个股票列表均已接入个股观察钻取。页面复用统一六位股票代码规范化工具，只对合法代码派发既有 `navigate` 事件；列表使用可聚焦按钮并提供悬停和键盘焦点反馈。共享实时刷新链路同时完成异常隔离：单一来源拒绝不会阻断其他成功来源，失败来源保留真实 `stale/unavailable`，加载状态可正常清零。未新增网络、IPC、轮询或重复业务逻辑。

`confirmed`：基于当前源码完成 Windows x64 EXE-only release 构建。验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-102017`。主程序 `yishu-desktop.exe` SHA-256 `2C98CEC982FDFA8FAB776D58CABD111059E745D4E82B629F9F07D010D8F3B5B1`（33,109,504 bytes），更新助手 `yishu-updater.exe` SHA-256 `6C1D7EC3A1515FB30E1005A86BC0EDE147D7C562FFF9A572D1684FFE558A3F51`（675,840 bytes），后台快讯采集器 `yishu-news-collector.exe` SHA-256 `4469D5569FB83B8741D97818B823840F0A3D881BFBBD13D90529D039A7BB04AE`（7,127,552 bytes）。三件 PE machine 均为 `0x8664`；主程序从独立目录启动 2000ms 后窗口句柄有效，清理后无残留进程。

`confirmed`：前端全量 Vitest 211 个文件/828 项通过，Rust workspace 890 项通过、1 项按设计忽略，Vite 生产构建处理 4002 个模块；EXE-only 合同、`cargo fmt --check`、架构登记 1863 条、编码扫描 4575 个文本文件和 `git diff --check` 通过。验收目录仅包含三个 EXE 与 `BUILD-INFO.txt`，无安装包或 ZIP；参考项目、用户配置、缓存和业务数据未修改，未执行 Git commit/stage/push。

`observed`：Rust release 仍保留既有 unused/deprecated warnings；远程更新服务完整配置、交易所级逐笔、完整远程数据覆盖、完整 AI 供应商接入和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/DataScreenPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/data-screen-navigation.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-movements-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-102017/BUILD-INFO.txt`。

## 2026-09-02 09:39 Windows x64 EXE 阶段性验收

`confirmed`：按最新源码完成 `scripts/build-windows-exe.ps1` 的 EXE-only release 构建。三件可执行文件复制到 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-093927`：主程序 `yishu-desktop.exe` SHA-256 `4772F1B77C84A0DFE0743F99FEDAEE64F6C1580ABF750966DDCE1C63306646C6`（33,109,504 bytes），更新助手 `yishu-updater.exe` SHA-256 `13968907F4326B3DB3C6839A674C612BF5C403A1671224785B790AEF0A199708`（675,840 bytes），后台快讯采集器 `yishu-news-collector.exe` SHA-256 `58FEECE80D4B2D85F056A0D9A8CE8819E6F6B8C02092930FAA1705D0A7B33903`（7,127,552 bytes）。

`confirmed`：Rust workspace 890 项通过、1 项按设计忽略；前端 Vitest 210 个文件/824 项通过；Vite 生产构建处理 4001 个模块；`cargo fmt --check`、EXE-only 合同、架构登记（1861 条）、编码扫描（4571 个文本文件）和 `git diff --check` 通过。复制后的主程序 PE machine 为 `0x8664`，从独立验收目录启动 2000ms 后主窗口句柄有效，清理后无残留进程。

`observed`：本轮仅生成三个阶段性 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP；参考项目、用户配置、缓存、业务数据目录未修改，未执行 Git commit/stage/push。远程更新服务完整配置、完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界；Rust release 保留既有 unused/deprecated warnings。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-093927/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

## 2026-09-02 09:10 Windows x64 EXE 阶段性验收

`confirmed`：按 `scripts/build-windows-exe.ps1` 完成当前源码的 Windows x64 EXE-only release 构建。三件可执行文件复制到 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-091059`：主程序 `yishu-desktop.exe` SHA-256 `769C62A4EF85EE62CFE60C64099080E341BDD91D7B2715F686C41A22E7A41E8C`（33,109,504 bytes），更新助手 `yishu-updater.exe` SHA-256 `EF281EEE6055A24326CEDFCA365E9F8E3D390B1FC2AA349A6B7445853F1C4A07`（675,840 bytes），后台快讯采集器 `yishu-news-collector.exe` SHA-256 `BFC13E19A5725868732DEC7E8540FD388B5CBC9E3319D56DF65A5FF2496647F1`（7,127,552 bytes）。

`confirmed`：Rust/Vite 构建退出码为 0，前端生产构建处理 4001 个模块；复制后的主程序 PE machine 为 `0x8664`，从独立验收目录启动 2000ms 后主窗口句柄有效，随后清理无残留进程；EXE-only 合同测试和 `git diff --check` 通过。目录只包含三个 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP，未触碰参考项目、用户配置、缓存或业务数据，未执行 Git commit/stage/push。

`observed`：Rust release 仍有既有 unused/deprecated warnings，不影响本次产物；远程更新服务完整配置、完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260902-091059/BUILD-INFO.txt`。

## 2026-09-01 22:29 Windows x64 阶段性 EXE 验收

`confirmed`：基于第 29 异动题材排行最新源码重新完成 Windows x64 EXE-only 构建。三件可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-222926`：主程序 `yishu-desktop.exe` SHA-256 `2AB18C4A1925857F44C9306028BC7EE1A7F83E337C8BA31AA2D6C97E1F915F4C`，更新助手 `A65E58A72AF8665C3BA95D088AFCF30C3EFA9ECA1139BA087E86331317264CFB`，后台快讯采集器 `FA6592B76EDFC056A35BEFDA066FA084EF3010A1608086E034304988223606C0`。

`confirmed`：EXE-only 合同、前端 Vitest 210 文件/820 项、平台与品牌图标契约、文件登记 1860 条、编码扫描 4566 个文本文件、架构检查和 `git diff --check` 通过；主程序 1200ms 独立启动烟测保持运行并清理，无残留进程。性能采样首帧 83.53-106.19ms，空闲 CPU 0.074%，工作集峰值 36,192,256 bytes，GPU 本地显存计数为 0。

`observed`：更新助手烟测按设计执行了成功与回滚场景，但失败场景会输出诊断文本；远程更新服务真实配置、完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证仍保持 `partial/stale/missing/unavailable` 边界。本轮未生成安装包或 ZIP，未修改参考项目、用户配置、缓存或业务数据目录，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/measure-windows-performance.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-222926/BUILD-INFO.txt`。


## 2026-09-01 AI 选股回放覆盖审计增强

`confirmed`：AI 选股跨日回放效果汇总在已有 1/5/20 日有效收益、正负收益和平均收益之外，新增每个 horizon 的预期候选数、有效样本数、缺失样本数和覆盖率。统计只读取冻结回放快照的 `candidates[].outcomes`，`null`/非有限收益不计入样本，零收益不计入涨跌；无快照时返回空统计并保留原 `unavailable/missing` 状态。未新增网络、IPC、数据库、计时器或依赖。

`confirmed`：前端 Presenter、类型、回放面板和样式完成 TDD；Vitest 4 项、TypeScript、AI 回放 Node 合同、文件登记、编码扫描和 `git diff --check` 通过。参考工程只读，未执行 Git commit/stage/push，未生成 EXE。

`observed`：长期效果归因、第二行情来源、交易所原子快照、完整历史回填和自动捕获所有候选跨日结果仍未完成，工作区和产品总体继续保持 `partial`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ai-selection-replay-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ai-selection-replay-types.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/AiSelectionReplayPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/ai-replay-next-report.md`。

## 2026-09-01 数据大屏独立菜单接线与 Windows x64 阶段性 EXE（17:44）

`confirmed`：当前项目正式登记 15 个一级菜单，新增“数据大屏”独立路由 `/data-screen`，完成页面懒加载、导航图标、feature-map、source-inventory 和双文件登记；数据大屏类型兼容共享异动/涨停证据的扩展字段，保持展示层只读取需要的字段。

`confirmed`：前端全量测试 205 个文件、799 项通过；Rust workspace 885 项通过、1 项按设计忽略；TypeScript、编码扫描 4529 个文本文件、文件登记 1827 条、架构验证、rustfmt 和 `git diff --check` 均通过。最新 Windows x64 阶段性验收产物位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-174440`，主程序 SHA-256 `CAE445C729FC9A9A619A5C506983B72072F749238DF2ABBB4104454784062DC1`，更新助手 `7B9BA3D31E3C69D89D065C8D017C3DEA4E7D0B86E4D419C6A9E47346953EB918`，后台快讯采集器 `A8E002E86E82192F0477F48202ACC4A7C545F097C6EF3AF302B15683F18C7E6B`；主程序独立启动 8 秒保持运行后由烟测结束，无残留进程。

`observed`：本次只生成阶段性 EXE，不生成安装包或 ZIP；参考项目、用户配置、缓存、业务数据目录未触碰，未执行 Git commit/stage/push。远程数据完整性、交易所级逐笔、完整 AI 供应商接入和历史回填仍保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/routes.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/page-loaders.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/DataScreenPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-174440/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

## 2026-09-01 逐条新闻行业分类证据阶段

`confirmed`：新闻工作台新增独立行业分类证据链。用户选中单条资讯后，后端按冻结事件 ID 与六位股票代码复用既有东方财富行业分类来源、六小时缓存、请求去重和熔断器；前端由独立 client/store/presenter/panel 接线，按事件与代码隔离缓存，保留 `ready/partial/stale/missing/unavailable`、last-good 和晚到响应门禁。该链路只展示来源明确给出的股票行业与板块字段，不从标题、涨跌幅或 AI 推断新闻语义、利好/利空、因果或收益。

`confirmed`：新增合同、领域投影、按需用例、Tauri 命令、前端模块、Rust/Vitest/Node 跨层测试和双份文件注册表登记；`cargo test --workspace --offline` 通过（849 passed，1 ignored），`pnpm test` 通过（191 files，720 tests），生产构建、架构登记、UTF-8 编码检查和 `git diff --check` 通过。普通网页预览无 Tauri 服务时保持真实 `unavailable/missing`。

`observed`：行业分类证据不等同新闻与行业主题的语义关联，市场反应归因、交易所级时间核验、完整实体关系和离线全天采集仍未完成；新闻菜单与产品总体继续保持 `partial`。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/news_industry_attribution.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/news/news_industry_attribution.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_news_industry_attribution.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/news_industry_attribution.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/NewsIndustryAttributionPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/news-industry-attribution-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-news-industry-attribution.md`。

## 2026-08-31 可转债十字段条款覆盖审计阶段

`confirmed`：可转债条款 Presenter 现对发现池中的十个已定义字段逐项统计有值数、缺失数和覆盖率，字段包括正股代码、上市日、到期日、转股价、转股价值、转股溢价率、剩余规模、转股起始日、赎回窗口起始和回售窗口起始。条款面板新增逐字段覆盖网格，继续只投影现有 Store 快照。

`confirmed`：基础 `complete` 判定仍只使用八个基础字段；赎回/回售窗口是可能不适用的可选条款，只作覆盖观察，不把空值伪装成缺失风险或默认日期。空发现池仍为 `missing`，未新增网络请求、IPC、数据库、计时器或依赖。

`observed`：完整条款文本、更多条款来源、正股第二来源、交易所原子快照和更多可转债来源仍未完成，菜单与产品总体继续保持 `partial`。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/convertible-bond-terms-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/convertible-bond-terms-presenter.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/ConvertibleBondTermsPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/convertible-bonds-contract.test.mjs`。

## 2026-08-31 新闻事件严格同股门禁阶段

`confirmed`：新闻工作台 Store 在事件影响请求进入缓存、请求去重或 IPC 前，先规范化事件代码并与当前查询标的比较。跨股票事件会清除选中事件，保持 `missing` 证据信封并返回拒绝警告，不发起事件影响读取。

`confirmed`：新增 Store 回归测试和新闻跨层合同断言；原有同事件去重、换股晚到响应隔离、last-good 回退及缓存上限行为保持不变。新增计划已登记到 YAML/Markdown 文件注册表。

`observed`：新闻三源覆盖、公告正文完整语义、逐条行业归因和市场反应归因仍保持 `partial/unavailable`；参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/news-workbench-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/news-workbench-store.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/news-workbench-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-31-news-workbench-stock-guard.md`。

## 2026-08-31 开盘冻结状态回显修复

`confirmed`：开盘检查单 Presenter 已复用 `marketOpenFreeze` 证据信封。冻结记录形成后，主检查单按快照状态、就绪项计数、冻结时间和来源回显；未形成记录保持 `missing`，读取失败保持 `stale/unavailable`。该改动只连接已有 Store，不新增 IPC、网络请求或定时器。

`observed`：竞价缺口、委托队列和交易所原子快照仍缺失；冻结只是当前七项事实的时间点封存，不代表所有检查项 ready、开盘方向或交易建议。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-open-types.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-open-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/MarketOpenPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-open-presenter.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-open-contract.test.mjs`。

## 2026-09-01 可转债按需完整条款证据

`confirmed`：新增独立可转债条款 DTO、东方财富 `RPT_BOND_CB_LIST` 与 `RPT_BOND_BS_INFO` 双报告读取器、纯解析器、6 小时两级缓存用例、请求去重、独立 `convertible_bond_clause_breaker`、Tauri 命令，以及前端 client/store/presenter/panel。解析器按两份报告精确校验债券代码，响应上限 512 KiB、字段值上限 512 字符、原始证据字段最多 64 项；不写入永久业务数据库，不从条款文本推断方向或风险。

`confirmed`：条款面板已挂载到可转债页面，展示转股价、到期日、剩余规模、转股起始日、强赎/回售原文和来源字段；缺失或来源失败保持 `partial/stale/missing/unavailable`。合同测试通过，Rust 定向测试 5 项通过，桌面前端测试 716 项通过，生产构建和架构登记 1737 项通过。

`observed`：普通网页预览没有 Tauri 桌面数据服务，输入精确债券代码前显示真实空态；远程条款报告实时性、交易所原子快照和历史版本完整性仍未宣称为 `ready`。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/convertible_bond_clause.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/convertible_bond_clause.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_convertible_bond_clause.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/ConvertibleBondClausePanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/convertible-bond-clause-contract.test.mjs`。

## 2026-09-01 可转债流动性门禁过期单债边界修复

`confirmed`：可转债生产命令确认接入 `execute_with_secondary_and_liquidity`，全池成交额按 100 个代码分批、最多 4 批并发读取；候选面板展示批量覆盖率和 2,000 万元门槛。

`confirmed`：精确查询时仅复用非 `stale` 的单债主行情成交额。过期单债行情中的高成交额不会绕过批量门禁；批量不可用或过期时，候选行保持 `observe_only`，并保留真实警告。新增 Rust 回归测试 `stale_exact_quote_turnover_does_not_release_a_strict_candidate`，可转债用例 9 项定向测试通过。

`observed`：腾讯公开批量报价仍不能证明交易所原子同刻成交额，第三行情来源、完整条款文本和交易所级快照仍为后续缺口。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_convertible_bonds.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/ConvertibleBondCandidatesPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-31-convertible-bond-candidate-liquidity.md`。

## 2026-09-01 可转债条款状态与字段覆盖一致性修复

`confirmed`：条款证据切片现在统一复用 `missing_clause_fields`：七个必需字段任一缺失即为 `partial`，全部存在才为 `ready`，`stale` 优先级不变。新增用例测试覆盖不完整快照和完整快照两条路径，7 项条款 Rust 定向测试通过。

`observed`：条款适用性仍以来源原文为准，缺失字段不被推断为风险或方向；参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_convertible_bond_clause.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/convertible_bond_clause.rs`。

## 2026-09-01 可转债正股历史远程补齐

`confirmed`：可转债正股历史链路先读取用户目录 `business.sqlite3` 的永久日线；本地覆盖不足请求数量时，才按需并发复用东方财富与新浪未复权日线来源。合并按交易日去重，本地记录优先，远程按东方财富后新浪补齐，并按请求上限裁剪。

`confirmed`：远程读取复用既有缓存、请求去重和独立来源熔断器，结果只作为可重建证据，不写入永久业务数据库，也不覆盖实时正股或债券字段。前端展示来源摘要、缺失字段和警告；远程补齐保持 `partial`，远程旧值参与展示保持 `stale`。

`confirmed`：新增 Rust 合并/编排测试、Presenter 来源摘要测试和跨层合同；合同已移除会扫描 `#[cfg(test)]` SQLite fixture 的粗粒度 `INSERT INTO` 断言。计划、生产文件和测试已登记到双份文件注册表。

`observed`：远程历史仍不代表交易所原子快照、复权数据、完整交易日历或实时历史流；来源长期可用性需发布环境持续核验。参考项目只读，未执行 Git 写操作，未生成 EXE、安装包或 ZIP。本地网页预览保持运行于 `http://127.0.0.1:1420/news-intelligence`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_convertible_bond_linked_stock_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/convertible_bond_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/convertible-bond-linked-stock-history-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/convertible-bond-linked-stock-history-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-convertible-bond-linked-stock-remote-history.md`。

## 2026-09-01 更新版本比较边界修复

`confirmed`：更新核心版本门禁改为有限 SemVer 比较，核心数字段按数值比较；同一核心版本中正式版高于 alpha/beta/rc，预发布标识按数字/文本和分段顺序比较，构建元数据不参与优先级。这样不会阻止从 `1.0.0-beta.2` 更新到 `1.0.0`，也不会把正式版错误降级到预发布版本。

`confirmed`：新增回归测试覆盖正式版/预发布版边界；更新签名、包哈希、用户目录隔离、原子交换、健康检查与回滚流程保持不变。更新核心定向测试 13 项通过，Rust workspace 824 项通过、1 项既有性能测试忽略，格式检查通过。

`observed`：远程签名清单、公钥和包服务仍需发布环境提供真实配置；本阶段未生成 EXE、安装包或 ZIP，未修改参考工程，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/updater-core/src/lib.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/crates/updater-core/src/activation.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/crates/updater-core/src/journal.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/bin/yishu-updater.rs`。

## 2026-08-31 临时公告观测时间排序修复

`confirmed`：临时交易公告叠加日历时，基线和公告的 `observedAt` 先解析为 RFC3339 绝对时间点再比较，跨时区偏移不再依赖字符串字典序；新增回归测试覆盖较早的 `+08:00` 文本与较晚的 `Z` 文本。

`confirmed`：临时公告领域定向 Rust 测试 8 项、交易日历跨层合同和 rustfmt 通过；未新增来源、缓存前缀、数据库表、定时器或依赖。

`observed`：临时公告来源仍要求用户配置并通过 SSE/SZSE 官方 HTTPS 校验；缺少配置时保持 `partial/unavailable`，不推断未发布的临时开市或休市。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/trading_calendar_notices.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/trading_calendar_notices_tests.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-30-temporary-trading-notices.md`。

## 2026-08-31 新闻工作台显式提交刷新边界

`confirmed`：新闻页面新增 `submittedSymbol` 状态，只有用户提交后才更新查询代码。自动刷新、焦点恢复、联网恢复和生命周期首次刷新均只使用最近一次已提交的规范化代码；用户编辑输入框但未提交时，后台刷新不会提前读取新代码或覆盖输入。无效提交会清空已提交代码并清除当前资讯状态。

`confirmed`：持久化默认代码仅在输入框没有并发编辑时初始化为已提交代码。新增新闻跨层合同，新闻目录 32 项定向测试和桌面生产构建通过；普通网页预览已保持在 `http://127.0.0.1:1420/news-intelligence`，无 Tauri 服务时显示真实 `unavailable/missing`。

`observed`：交易所级实时流、逐条行业归因和市场反应因果识别仍未完成；参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/NewsPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/news-workbench-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-31-news-workbench-stock-guard.md`。

## 2026-08-31 个股事件证据跨日缓存门禁

`confirmed`：个股事件证据 Store 在缓存命中前读取当前上海交易日并比较热点快照的 `tradingDate`。跨日时不直接复用前一交易日题材，而是发起当天的既有新闻/热点并行读取；旧快照仍由 `keepLastGood` 保护，失败时保留真实 `stale` 语义。新增跨日回归测试与跨层合同，未增加网络源、IPC、定时器、数据库或依赖。

`observed`：历史题材自动加载、完整法定交易日历、交易所逐笔事件时间和原子同刻多源快照仍未完成，个股观察与产品总体继续保持 `partial`。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-event-evidence-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-event-evidence-store.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/stock-event-multisource-evidence-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-31-stock-event-evidence-date-guard.md`。

## 2026-08-31 个股历史日线第二来源确认阶段

`confirmed`：个股驾驶舱在本地日线少于 60 根时并发读取东方财富与新浪 `scale=240` 未复权日线。新浪适配层以回调名携带的股票代码做身份校验，限制响应 512 KiB、400 根记录，并严格验证日期窗口、重复交易日、OHLC 关系和成交量；新浪接口不提供成交额，金额保持缺失。

`confirmed`：新浪历史日线使用独立 6 小时内存/持久缓存、请求去重和熔断器；纯 Rust 确认域按同代码、同窗口、同交易日比较 OHLC 0.15% 和成交量 5% 容差，至少 20 个共同交易日且无来源独占日期才标记 `confirmed`。超差、覆盖不足、单源和双空分别保留 `divergent/time_unverified/primary_only/secondary_only/unavailable`；新浪不覆盖本地 TDX 或东方财富主日线。

`confirmed`：前端新增专用类型、Presenter 和“历史日线双源核验”面板，只投影后端证据，不发起 IPC、网络或定时器；双文件注册表、功能矩阵、完成审计和根级 `pretest` 已同步。

`observed`：两路公开 HTTP 日线的来源观测时间不代表交易所原子快照，复权、完整交易日历、可核验成交额、第三远程来源和交易所级原子覆盖仍缺失；个股观察与产品总体保持 `partial`。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/stock_daily_confirmation.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/sina_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/stock_daily_confirmation.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_stock_daily_confirmation.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/StockDailyConfirmationPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/stock-daily-secondary-confirmation-contract.test.mjs`。

## 2026-08-31 可转债候选风险门禁阶段

`confirmed`：可转债候选池的规则唯一实现已下沉到 Rust `domain/bonds/convertible_bond_candidate.rs`。除转股溢价率不高于 50%、剩余规模不低于 0.5、剩余期限不少于 30 天和基础字段完整外，临近到期（180 天内）或已进入赎回窗口的记录标记为 `excluded`，进入回售窗口的记录标记为 `observe_only`；每行通过 `riskFlags` 保留可审计风险标记。

`confirmed`：前端 `convertible-bond-candidates-presenter.ts` 只投影 Rust `candidatePool` DTO，不重新实现规则；候选面板展示风险标记和真实缺口。该阶段不增加 IPC、网络请求、数据库表或定时器，普通网页预览仍保持真实 `missing/unavailable`。

`observed`：全池成交额门禁尚未接入，原因是现有成交额仅在单只债券行情查询中可用，缺少可审计的批量同日成交额来源；不使用单只结果推断全池流动性。完整条款文本、正股第二来源、交易所原子快照和更多可转债来源仍保持 `partial` 缺口。参考工程只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/bonds/convertible_bond_candidate.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/convertible-bond-candidates-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/ConvertibleBondCandidatesPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/convertible-bonds-contract.test.mjs`。
type: project-memory
status: confirmed
updated: 2026-09-01
project_path: "D:/Users/90090/Documents/ChatGPT/A股平台"
sources: ["task:01a03785-a8a0-7a42-88d4-836458a08fb1", "project:金融财经-read-only-reference"]
tags: [project-memory, finance, a-share, desktop, tauri]
---

## 2026-08-31 市场异动失败状态事件广播修复

`confirmed`：异动 Tauri 命令 `load_market_movements` 在每次聚合尝试后均广播完整证据信封，包含 `partial/stale/missing/unavailable`，不再以 `envelope.data.is_some()` 静默丢弃失败状态；前端仍按版本门禁和 last-good 规则处理事件。

`observed`：事件仍由按需 HTTP 聚合触发，尚未接入交易所级 SSE/逐笔行情；参考工程只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_movements.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-movement-event-bridge-contract.test.mjs`。

`observed`：全量 Vitest 并行编译所有总览懒加载面板时，20 秒固定超时可能受 Windows 负载影响；隔离测试通过后已将该测试等待上限调整为 60 秒，断言范围不变。

## 2026-08-31 本地备份容量治理阶段

`confirmed`：永久数据库创建备份后，`backup.rs` 只枚举用户备份目录内名称符合 `business-*.sqlite3` 的普通文件，按文件名时间序保留最近 8 份并删除更旧备份；无关文件、目录和符号链接不触碰。清理动作发生在新备份成功写入之后，清理失败不会回滚或覆盖刚生成的有效备份。既有只读完整性校验、恢复到临时新路径和业务库不覆盖边界保持不变。

来源：`apps/desktop/src-tauri/src/infrastructure/database/backup.rs`、`apps/desktop/src-tauri/src/commands/operations.rs`、`apps/desktop/src-tauri/src/application/use_cases/operations_safety.rs`、`docs/verification/feature-completion-audit.md`。

## 2026-08-31 应用关闭期间全球快讯采集阶段

`confirmed`：应用关闭期间的调度器与一次性采集器已接入。Windows 适配层通过 `schtasks.exe` 注册用户级任务，macOS 适配层通过 `~/Library/LaunchAgents` 与 `launchctl` 注册用户级任务；两个适配层之外的业务代码不出现系统 API 或系统路径。独立 `yishu-news-collector` 只接受 `--once`（无参数也执行一次），复用既有网络客户端、两级缓存、请求去重、东财/新浪独立熔断器和投资日历资讯归档用例，单轮 55 秒超时后退出。

`confirmed`：用户设置新增“应用关闭时继续归档”开关，默认启用；启动和保存设置后异步同步计划，调度失败显示 `unavailable` 且不阻断 UI。程序安装目录和用户配置、缓存、业务数据库保持物理隔离，采集失败不清空 last-good 数据，也不生成假快讯。

`observed`：系统休眠、用户权限拒绝、调度器不可用、公开来源失败、交易所级发布时间核验、逐条行业归因和市场反应因果识别仍可能降级或缺失，全球快讯和产品总体继续保持 `active/partial`。定向 Rust/Node 合同和前端构建已通过；本阶段未修改参考工程、未执行 Git commit/push、未生成 EXE/安装包/ZIP。

来源：`docs/superpowers/plans/2026-08-31-background-news-collector-when-closed.md`、`apps/desktop/src-tauri/src/platform/background_collector_scheduler.rs`、`apps/desktop/src-tauri/src/platform/windows_scheduler.rs`、`apps/desktop/src-tauri/src/platform/macos_scheduler.rs`、`apps/desktop/src-tauri/src/headless_news_collector.rs`、`apps/desktop/src-tauri/src/bin/yishu-news-collector.rs`、`apps/desktop/src/shared/settings/background-news-schedule-client.ts`、`tests/features/background-news-scheduler-contract.test.mjs`、`tests/features/background-news-collector-binary-contract.test.mjs`、`tests/features/background-news-schedule-settings-contract.test.mjs`。

## 2026-08-31 市场快讯新浪第二来源阶段

`confirmed`：全球快讯市场工作区新增新浪财经直播第二来源。Rust 基础设施以独立 `sina_fast_news.rs` 请求并解析新浪 JSONP/JSON，字段清洗、链接校验、稳定 ID、六位代码和异动词提取复用 `breaking_news_support.rs`；应用用例对东方财富与新浪分别使用 60 秒两级缓存、请求去重和独立熔断器，并通过 `futures_util::future::join` 并发读取。标题与发布时间完全一致的记录合并为一行并标记 `multi_source`，未匹配记录保持 `single_source`；任一来源失败保留另一来源真实数据并降级覆盖，双源均无数据保持 `missing/unavailable`，不生成模拟事件。前端只通过 Presenter 展示“多源一致/单一来源”证据标签，不新增 IPC、网络或轮询。

来源：`apps/desktop/src-tauri/src/infrastructure/sources/sina_fast_news.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/breaking_news_support.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_breaking_news_alerts.rs`、`apps/desktop/src/feature/market-overview/BreakingNewsPanel.svelte`、`docs/superpowers/plans/2026-08-31-breaking-news-secondary-source.md`。

`observed`：新浪直播源的交易所级发布时间、离线全天采集、逐条行业归因和市场反应因果识别仍未完成；市场快讯、热点播报、投资日历与产品总体继续保持 `active/partial`。本阶段未修改参考工程、未执行 Git commit/push、未生成 EXE/安装包/ZIP。

## 2026-08-31 投资日历归档双熔断接线阶段

`confirmed`：投资日历跨日资讯归档新增 `execute_with_breakers`，命令层同时传入东方财富与新浪财经独立熔断器，归档不再因复用同一熔断器而让两路来源互相影响。归档外层证据继承全球快讯当前覆盖率：双源都有可用记录时为 `1.0` 并移除 `multi_source_confirmation` 缺失；单源、空窗、陈旧和不可用状态继续真实表达。归档限制文案同步改为东财/新浪双源口径，未修改参考工程、未执行 Git commit/push。

来源：`apps/desktop/src-tauri/src/application/use_cases/load_investment_calendar_news_archive.rs`、`apps/desktop/src-tauri/src/commands/investment_calendar.rs`、`apps/desktop/src-tauri/src/infrastructure/cache/investment_calendar_news_archive.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_investment_calendar_news_archive_tests.rs`。

`observed`：应用未运行时全天采集、官方事项第二来源、交易所级发布时间核验和逐条行业/市场反应因果归因仍未完成；投资日历、新闻热点和产品总体继续保持 `active/partial`。本阶段未生成 EXE、安装包或 ZIP。

## 2026-08-31 盘口来源时间审计

个股观察双源盘口现在在腾讯与新浪五档证据上输出来源时间差毫秒值 `observationDeltaMs` 和 `timingStatus`：`same_source_second`、`within_five_seconds`、`outside_window`、`missing_source_time`。时间仅由来源自身 RFC3339 时间解析，缺失时保持不可用，不补造当前时间。前端面板展示时间状态并明确“公开 HTTP 两源不保证交易所原子快照”。交易所原子瞬时采样、逐笔时间、完整委托队列和第三来源裁决仍为 `partial` 缺口。

来源：`docs/superpowers/plans/2026-08-31-atomic-order-book-snapshot.md`、`crates/contracts/src/stock_order_book_confirmation.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_stock_order_book_confirmation.rs`、`apps/desktop/src/feature/stock-observation/stock-order-book-confirmation-presenter.ts`。

# 一树-A股观测台

## 2026-08-31 远程历史日线补齐阶段

`confirmed`：个股驾驶舱在本地 TDX 日线少于 60 根时按需读取东方财富未复权日线；本地日线优先，远程结果按交易日合并，仅进入可重建缓存，不写入永久业务数据库。来源使用独立 6 小时缓存、请求去重和独立熔断器，严格校验股票代码、日期窗口、OHLC 关系、重复日期和响应上限，失败时保留本地数据并维持真实状态。

`observed`：复权、交易日历、第二远程来源、交易所级完整覆盖和普通网页预览的非空远程证明仍未完成；个股观察与产品总体保持 `partial`。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/stock_remote_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_stock_remote_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/stock-remote-daily-contract.test.mjs`。

## 2026-08-31 信息总览共享刷新控制阶段

`confirmed`：信息总览的自动刷新开关现在通过独立 `overview-refresh-controller.ts` 同时控制市场脉冲和异动/热点/快讯共享 Store；手动刷新也以一次用户动作并发触发两条已有共享链路，不复制网络请求或定时器。

`confirmed`：异动 Store 增加 `setAutoRefresh(enabled)`。关闭时清除后台计时器并阻止可见性恢复、刷新偏好变化和刷新完成后的重新排程；显式 `refresh()` 仍可执行。开启时仅在已有订阅且页面可见时触发一次刷新。

`observed`：定向 Store/控制器测试与 Vite 构建通过；交易所级 SSE/逐笔行情、原子同刻多源快照和完整因果证据仍为后续缺口。参考项目只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`apps/desktop/src/feature/market-overview/market-movements-store.ts`、`apps/desktop/src/feature/market-overview/overview-refresh-controller.ts`、`apps/desktop/src/feature/market-overview/OverviewWorkspaceHub.svelte`、`apps/desktop/src/feature/market-overview/market-movements-store.test.ts`、`apps/desktop/src/feature/market-overview/overview-refresh-controller.test.ts`。

## 2026-08-31 运行期间全球快讯后台采集阶段

`confirmed`：新增 `apps/desktop/src-tauri/src/application/news_collection_lifecycle.rs`，Tauri 启动后延迟 5 秒，以单个 `tokio::time::sleep` 循环复用既有双源投资日历快讯归档用例。任务只持有共享网络客户端、内存/持久缓存、请求去重器和独立熔断器；网络请求及 SQLite 写入不阻塞 UI 首帧，也不复制新闻解析或归档逻辑。

`confirmed`：用户配置新增 `backgroundNewsCollectionEnabled` 和 `backgroundNewsCollectionIntervalSeconds`，默认启用、默认 300 秒、规范化范围 60–3600 秒。设置保存通过 `watch` 通道即时更新唯一后台任务；关闭、缺少网络或缺少持久缓存时不发起请求。普通网页预览仍只显示真实桌面服务不可用状态。

`observed`：该阶段只覆盖应用持续运行期间的低频采集；应用完全退出期间的全天采集、交易所级发布时间、完整行业归因和市场反应因果识别仍未完成。参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

### 2026-08-31 关闭期间采集器发布布局复核

`confirmed`：关闭期间采集器已完成发布资源布局接线。Windows 发布配置把 `yishu-news-collector.exe` 放入桌面程序 `resources`，macOS 发布配置把无扩展名采集器放入 `.app/Contents/Resources`；便携包脚本同步复制并校验资源，开发配置仍保持仅更新助手，避免开发预览依赖未构建的采集器。Windows 任务计划间隔采用向上取整（61 秒为 2 分钟），macOS LaunchAgent 参数统一 XML 转义。

`confirmed`：定向 Rust 调度器测试、macOS 更新合同、后台调度器合同和架构登记检查通过；参考工程保持只读，未执行 Git commit/push。

`observed`：尚未生成安装包、便携包或 ZIP；系统休眠、权限拒绝、调度器不可用、公开来源失败、交易所级发布时间核验、逐条行业归因和市场反应因果识别仍可能降级为 `partial/unavailable`。

来源：`docs/superpowers/plans/2026-08-31-background-news-collector.md`、`apps/desktop/src-tauri/src/application/news_collection_lifecycle.rs`、`apps/desktop/src-tauri/src/commands/core_menu.rs`、`apps/desktop/src-tauri/src/commands/settings.rs`、`apps/desktop/src/shared/settings/user-settings-types.ts`、`apps/desktop/src/feature/settings/SettingsPage.svelte`、`tests/features/background-news-collector-contract.test.mjs`。

## 目标与成功标准

在 Windows x64 优先交付一款高性能桌面 A 股观测台，用全新 Rust/Tauri/Svelte 架构复刻参考项目的菜单、功能边界和信息展示；业务层跨平台，Windows/macOS 差异只出现在适配层。参考项目只读，不复制源码、运行数据或凭据，不执行 Git 提交。

## 当前读取摘要

- `confirmed`：十四个一级菜单和 50 个信息总览工作区已有独立入口；一级页面按路由动态加载，生产源码继续登记到 YAML/Markdown 双注册表。
- `confirmed`：新闻/公告、公司研究、个股观察、AI+选股和交易日历已形成跨层真实证据链；缺失、陈旧、冲突或覆盖不足继续显示 `partial/stale/missing/unavailable`，不生成假数据、方向判断或交易建议。
- `confirmed`：个股驾驶舱已统一基础行情刷新，并接入第二行情/盘口来源、事件 K 线、事件影响和公告正文；研究证据独立低频加载，不随高频行情重复请求或清除。
- `confirmed`：AI+选股解释绑定冻结候选和完整证据，跨日回放只读取实际后续日线；SSE/SZSE 官方交易日历使用独立缓存、哈希重验和严格双源裁决，并在应用持续运行且已配置来源时以默认 6 小时单次调度重新核验。
- `confirmed`：公告正文面板在既有代码、日期、金额和章节线索之外，按独立标题行提取最多 12 个章节原文摘要，每段最多 240 字符；摘要仅展示直接原文，不生成方向、评分、推荐或因果结论。
- `confirmed`：新闻热点页新增独立来源状态矩阵，复用三源状态信封汇总固定五态、三源覆盖率、有效/丢弃记录和未查询/确认空窗/旧值回退/不可用边界；Presenter 与组件不新增 IPC、网络、计时器或依赖，文件已登记到 YAML/Markdown 双注册表。
- `confirmed`：个股成交明细 Presenter 对通过字段校验的腾讯 3 秒聚合最新页记录汇总可见成交额；面板与数量、B/S/M 来源标记并列显示，无有效记录保持 `--`，不把无证据当作零。
- `confirmed`：最近一次覆盖盘口双源阶段的完整门禁为前端 143 个 Vitest 文件/578 项、Rust workspace 699 项通过且 1 项既有性能测试忽略、Vite 3,879 个模块和 1,464 项文件登记。随后驾驶舱统一刷新取得定向 Store/架构测试与构建证据。
- `observed`：新闻严格同股、状态矩阵、显式提交和 `execute` 行为测试仍有审计缺口；个股事件未选择状态和两处注册表依赖登记问题已在后续阶段修正（原风险结论 obsolete）。相关工作区不能据文档口径提前视为完成。
- `observed`：交易所逐笔成交、原子同刻多源快照、独立临时公告流、跨重启日历同步、复权/基准收益和完整因果归因仍未关闭，项目总体保持 `active/partial`。
- `observed`：当前 Git 仓库没有初始提交，工程文件全部未跟踪；参考项目保持只读。按用户约束，本阶段不执行项目 Git 写操作，也不生成 EXE、安装包或 ZIP。

以下阶段状态仅用于历史追溯，默认读取到本摘要、风险和下一步即可。

## 历史阶段状态（仅追溯时读取）

- `confirmed`：新工作区已建立 Rust workspace、Tauri 2 桌面壳、Svelte 5/Vite UI、跨平台路径层、配置/日志/恢复、网络、SQLite/WAL、来源契约和文件登记库。
- `confirmed`：已接入信息总览、今日研判、个股观察、公司研究四个独立页面、共享证据状态组件、前端 DTO 和 Tauri IPC 命令；无数据时显示 `unavailable/missing`，不伪造行情。
- `confirmed`：其余一级菜单均有独立页面入口和明确待接入状态，不再把所有功能堆在根组件。
- `observed`：2026-08-25 当前“个股观察”仍只读取腾讯快照；永久库已有 `daily_bars` 表但尚无读取用例。本日已写契约测试并开始实现只读日线查询、跨层 DTO、个股 IPC 与公告时间线 UI，尚未将该链路标记为完成。
- `confirmed`：2026-08-25 本轮将首次涨停、尾盘选股、量化分析、新闻热点、风险提醒、历史复盘、监控中心、设置、本地运维和可转债全部替换为独立交互工作台；缺失来源继续显示不可用/待证据，不使用模拟行情。
- `confirmed`：设置页已接入 `load_settings/save_settings`，配置写入用户数据目录并保留 `.bak`；本地运维页已接入目录探针、来源健康、过期缓存清理、数据库优化和本地备份 IPC。
- `confirmed`：前端 `pnpm test`、架构检查、生产构建、`cargo check --workspace` 和 `cargo test --workspace` 均通过；当前开发预览为 `http://127.0.0.1:1420/`。
- `confirmed`：Visual Studio 2022 Build Tools 的 MSVC x64 环境可用，Windows release EXE、NSIS 安装包和便携 EXE 均已构建。
- `confirmed`：`yishu-updater-core` 已实现协议版本、HTTPS 元数据、Ed25519 签名、SHA-256 完整性和用户目录重叠保护，并通过 3 项单元测试。
- `confirmed`：最新交付产物已复制到 Codex outputs；安装包 SHA-256 为 `63CF937AF2B8A3636F5BFBF39306A8D6F740131BD6AFF3BA8911C5AE4CA202F7`，便携 EXE SHA-256 为 `A461AD030F02D67D4C4B5FC737B8D4CD4693B2A3EE68D3BFB580FACBD866CE76`；包含更新检测 IPC，release EXE 启动 smoke 通过。
- `confirmed`：本轮验证通过前端构建、Vitest、`cargo test --workspace --offline`、14 菜单/文件登记/来源清单检查、UTF-8 乱码扫描和更新成功/回滚烟测；PowerShell 烟测改用 Node UTF-8 解析更新日志，兼容 Windows 路径。
- `confirmed`：本轮生成 Windows x64 NSIS 安装包，SHA-256 为 `D3344014AEC5D9C99B61CF994F592D44FD7680BDF1D86A7D8B4C966330F7E77D`；生成纯程序便携 ZIP，SHA-256 为 `C278EBF4B865C96F9EE37BA8B76EBC2C2D32BFDC4E4D2CF5BEA8035385178B82`，便携 EXE SHA-256 为 `04B657DE55E0D075969147691F2C3B631F2C2B2B7F0A0DCB3AFA066A077AD3BC`；包内只有主程序和更新助手，不含用户数据。
- `confirmed`：后续增量新增通达信 `.day` 递归发现/解析器、首次涨停规则快照、尾盘腾讯实时筛选、持仓风险快照和监控规则用户目录持久化；页面已接入对应 IPC。数据缺少量比、换手率、估值、行业或回撤时继续保持 `partial/unavailable`，不生成代理值。
- `confirmed`：本轮新增本地通达信确定性量化回测、固定交易日历史复盘指标、新闻来源状态 IPC 和可转债独立来源状态 IPC；量化、新闻、历史、可转债页面不再使用定时器伪刷新。
- `confirmed`：新闻输入 6 位股票代码时已通过统一网络层接入东财公开 JSONP 个股新闻；非代码热点输入、网络风控或解析失败时保持 unavailable，不伪造资讯。
- `confirmed`：本轮全量 Rust workspace 离线测试 19 项通过，前端 Vitest 2 项通过，Vite 生产构建通过，14 菜单/来源清单/文件登记门禁通过，UTF-8 乱码扫描和 `git diff --check` 通过。
- `confirmed`：本轮最终 Windows x64 NSIS 安装包 SHA-256 为 `3C6F0A11B26554A7C5CB8925F5B869AB525D7A4DC9F6B7EA605956A68C66F8B2`；便携 EXE SHA-256 为 `CEF7F710F94F0278D63083F23B92A607010B29F4DFCAE0099AEE3F466561102C`；便携 ZIP SHA-256 为 `4F94E50C52AB9B1BA897DC015DC6AFD8085376AE6902AECC6B28E8962DB9956A`；更新成功/健康超时回滚烟测均通过。
- `confirmed`：本轮新增可转债条款字段解析和独立诊断域；发现池在有来源证据时解析转股价、转股价值、溢价率、剩余规模、转股/赎回/回售日期，纯函数诊断计算转股溢价率、剩余期限和风险标记，缺失时保持 `partial/missing/unavailable`。
- `confirmed`：本轮最终重建 Windows x64 交付产物；NSIS 安装包 SHA-256 为 `508D6D9B39B768DCA21A8693F44ECE3EF49C1DD903E8456BF441B69FC5A242A9`，便携 EXE SHA-256 为 `6A503504E2D64854B2D53C81A0F13FB8655A5D31FE235A7165691983241EC3C4`，便携 ZIP SHA-256 为 `549534673F33F282C1A3B377EA275B8BD1DE5C36DAAFE703049D2791B6D4BA76`；更新成功/回滚和 release EXE 启动 smoke 通过。

## 本轮增量

### 2026-08-31 新闻来源状态矩阵阶段

- `confirmed`：`news-source-status-matrix.ts` 以纯函数汇总三源 `NewsSourceStatus[]`，固定状态集合和来源顺序，区分未查询、确认空窗、旧值回退与不可用；覆盖率固定按三源基线计算，计数不生成假成功。
- `confirmed`：`NewsSourceStatusMatrix.svelte` 只渲染 Presenter 结果，并已接入 `NewsPage.svelte`；无 IPC、网络、计时器和额外依赖。
- `confirmed`：Presenter 3 项 Vitest、Node 跨层合同、Vite 3910 模块构建和双注册表登记通过；根级 `pretest` 已纳入该跨层合同，完整前端 172 个文件/675 项、Rust 730 项、架构/编码/格式/差异门禁均通过；产品总体继续保持 `active/partial`。

来源：`docs/superpowers/specs/2026-08-31-news-source-status-matrix-design.md`、`apps/desktop/src/feature/news/news-source-status-matrix.ts`、`apps/desktop/src/feature/news/news-source-status-matrix.test.ts`、`apps/desktop/src/feature/news/NewsSourceStatusMatrix.svelte`、`tests/features/news-source-status-matrix-contract.test.mjs`。

### 2026-08-30 成交明细可见金额阶段

- `confirmed`：`stock-trade-detail-presenter.ts` 新增 `visibleAmountYuan` 与 `visibleAmountLabel`，只累加有效记录的来源成交额；无有效行返回 0 与 `--` 标签。
- `confirmed`：`StockTradeDetailPanel.svelte` 在最新页摘要中展示可见成交额，保持 3 秒聚合、来源方向标记和非逐笔边界文案，不新增请求、缓存或计时器。
- `confirmed`：Presenter 定向测试、成交明细 Node 跨层契约和生产构建通过；双注册表职责已同步。
- `observed`：交易所逐笔、第二成交源、委托/成交编号和原子同刻快照仍缺失，个股观察与产品总体继续保持 `active/partial`。

- 来源：`apps/desktop/src/feature/stock-observation/stock-trade-detail-presenter.ts`、`apps/desktop/src/feature/stock-observation/StockTradeDetailPanel.svelte`、`apps/desktop/src/feature/stock-observation/stock-trade-detail-presenter.test.ts`、`tests/features/stock-trade-detail-contract.test.mjs`。

### 2026-08-30 公告正文直接结构化分段阶段

- `confirmed`：`announcement-detail-semantics.ts` 新增 `sections` 输出，支持常见编号和冒号前缀的独立章节标题，截取标题到下一标题之间最多 240 字符原文摘要，最多 12 段；普通正文中的标题词不会被误识别。
- `confirmed`：`AnnouncementDetailPanel.svelte` 展示结构分段数量和摘要，保持既有正文缓存、受信外链和五态状态边界；不增加网络请求、轮询或 AI 推断。
- `confirmed`：语义 Vitest 4 项与 Node 跨层契约通过，YAML/Markdown 文件注册表已同步更新。
- `observed`：公告完整实体关系、全文撤回/修订差异、逐条行业归因和市场反应归因仍未接入，新闻工作台与产品总体保持 `active/partial`。

- 来源：`apps/desktop/src/feature/news/announcement-detail-semantics.ts`、`apps/desktop/src/feature/news/AnnouncementDetailPanel.svelte`、`apps/desktop/src/feature/news/announcement-detail-semantics.test.ts`、`tests/features/announcement-detail-semantics-contract.test.mjs`。

### 2026-08-30 公告连续快照修订证据阶段

- `confirmed`：新闻工作区现在在巨潮公告稳定 `announcementId` 基础上比较连续两次真实列表快照，输出 `new`、`revised`、`not_observed`；列表未出现不解释为公告撤回。
- `confirmed`：修订基线复用现有 `PersistentCache`，前缀为 `cninfo:announcement-revisions:v1:`，TTL 30 天、每股最多 8 份；首次读取为 `missing` 基线，重复快照为 `ready`，字段变化为 `partial`。
- `confirmed`：stale 公告只比较不写新基线；无缓存、无观测时间、无当前数据和归档失败均保留真实状态，归档问题不清除公告主数据。
- `confirmed`：新增独立 `AnnouncementRevisionPanel.svelte` 和跨端类型，新闻页仅做接线，面板不直接调用 IPC/网络/轮询；双注册表、架构合同和 Rust 定向测试已补齐。
- `observed`：本阶段尚未实现公告正文语义差异、全量历史窗口和撤回事实来源；产品继续保持 `active/partial`。未修改参考项目，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

- 来源：`docs/superpowers/specs/2026-08-30-announcement-revision-design.md`、`apps/desktop/src-tauri/src/application/use_cases/load_news_workbench.rs`、`apps/desktop/src/feature/news/AnnouncementRevisionPanel.svelte`、`tests/features/announcement-revision-contract.test.mjs`。

### 2026-08-30 一级页面按路由懒加载阶段

- `confirmed`：应用入口已移除十四个一级页面的静态导入，新增 `apps/desktop/src/app/page-loaders.ts` 作为唯一路由到页面异步模块的注册表；`App.svelte` 只加载当前路由，使用版本号隔离快速切换的晚到模块，并保留加载中/失败的真实边界。
- `confirmed`：Vite 生产构建输出独立一级页面 chunk；14 路由动态导入合同、TypeScript 构建通过，新生产文件已登记到 `docs/architecture/file-registry.yaml` 与 Markdown 视图。未新增网络请求、轮询、依赖、数据库表或后台任务。
- `observed`：该阶段改善启动解析成本，不关闭交易所临时公告、完整跨年度历史、第三来源核验等数据缺口；产品继续保持 `active/partial`，未生成发布包、未修改参考工程、未执行 Git 写操作。

- 来源：`docs/superpowers/plans/2026-08-30-route-page-lazy-loading.md`、`apps/desktop/src/app/page-loaders.ts`、`apps/desktop/src/app/App.svelte`、`tests/features/route-page-lazy-loading-contract.test.mjs`。

### 2026-08-30 个股资讯自动刷新生命周期阶段

- `confirmed`：新闻页面在默认股票代码加载后启动独立 `news-refresh-lifecycle.ts`；首刷、窗口焦点、网络恢复和重新可见均复用同一个刷新 Promise，手动查询不再建立第二条请求路径。
- `confirmed`：生命周期只在前台可见时通过可取消的单次 60 秒 `setTimeout` 调度；隐藏或卸载清理调度和监听器，不使用 `setInterval`、高频后台常驻任务、新网络来源或新依赖。既有三源 `sync_news` 缓存、请求去重、熔断和真实状态信封保持不变。
- `confirmed`：新增生命周期 Vitest、Node 架构合同、实施计划，并同步登记到 YAML/Markdown 文件注册表；定向测试、TypeScript 检查通过。
- `observed`：普通网页预览无 Tauri IPC，不能证明远程三源返回非空或交易所级实时性；公告撤回/修订追踪、后台离线采集和完整跨来源资讯确认仍保持缺口。项目继续为 `active/partial`，未生成 EXE/安装包/ZIP，未修改参考工程，未执行 Git commit/push。

- 来源：`docs/superpowers/plans/2026-08-30-news-refresh-lifecycle.md`、`apps/desktop/src/feature/news/news-refresh-lifecycle.ts`、`apps/desktop/src/feature/news/NewsPage.svelte`、`tests/features/news-refresh-lifecycle-contract.test.mjs`。

### 2026-08-28 AI+选股工作区

- `confirmed`：信息总览第 31“AI+选股”已接入独立懒加载页面，首次涨停与尾盘选股两个既有菜单迁移到同一共享候选任务仓；相同分支进行中请求去重，刷新失败保留上一次真实结果并降级为 `stale`，页面不直接调用 Tauri、网络或计时器。
- `confirmed`：合法六位代码跨策略合并后保留 `candidate/pending/blocked`、原始规则原因、字段缺口、风险、真实任务 ID 和输入审计，不生成综合预测分。AI 只允许用户在单只候选上显式触发，不能改写禁买、回避、缺字段或陈旧来源。
- `confirmed`：页面包含 AI 选股证据闸门、规则候选池、候选策略匹配、两个来源状态和按需解释。证据规范化与视图聚合已拆为 181 行和 179 行两个单一职责文件，架构合同限制两者不超过 300 行。
- `confirmed`：新鲜验证通过全部根级 Node 契约、60 个 Vitest 文件 226 项、Vite 3700 模块生产构建、Rust 桌面端 336 项且 1 项既有性能测试 ignored、更新核心 11 项、14 个菜单、804 项文件登记、2186 个项目文本文件编码扫描、rustfmt 和项目差异检查。
- `confirmed`：浏览器 1280px 页面/工作区宽度为 `1280/1280`、`1021/1021`，760px 为 `760/760`、`483/483`；窄屏三类分析区和来源状态切单栏，候选表只在自身形成 `1080/446` 局部滚动，三块结构、真实 `unavailable` 空态均渲染，控制台无警告或错误。预览保留在 `http://127.0.0.1:1420/?workspace=ai-selection`。
- `observed`：跨策略服务端冻结 ID、跨日回放、统一解释输入哈希、第二行情来源和长期效果归因仍未接入，因此工作区保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考工程，未执行 Git 写操作。
- 来源：`apps/desktop/src/feature/selection-candidates/selection-candidates-store.ts`、`apps/desktop/src/feature/market-overview/ai-selection-evidence.ts`、`apps/desktop/src/feature/market-overview/AiSelectionPanel.svelte`、`tests/features/ai-selection-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-28 复盘统计大全工作区

- `confirmed`：信息总览第 29“复盘统计大全”已接入独立懒加载页面，只复用共享全市场宽度、永久日线成交、严格涨跌停和板块横截面；不新增 Rust、IPC、网络来源、数据库、缓存、依赖、AI 或刷新计时器。
- `confirmed`：纯 Presenter 负责非负整数与成交合同校验、股票和板块身份去重、六项透视、同源五档互斥分布、四路完整度审计和状态降级。关系矛盾与非法值保持缺失，真实零保留；不同来源不强行解释为同日冻结快照。
- `confirmed`：新鲜验证通过全部根级 Node 契约、58 个 Vitest 文件 215 项、Vite 3694 模块生产构建、Rust 桌面端 336 项且 1 项既有性能测试 ignored、更新核心 11 项、14 个菜单、793 项文件登记、2175 个项目文本文件编码扫描、rustfmt 和项目差异检查。
- `confirmed`：浏览器 1280px 页面/工作区宽度为 `1280/1280`、`1021/1021`，760px 为 `760/760`、`483/483`；窄屏分析区和四来源状态切单栏，摘要与六项透视为两列，审计表只在自身形成 `850/445` 局部滚动。真实 `unavailable` 空态和三块参考结构均渲染，控制台无警告或错误；预览保留在 `http://127.0.0.1:1420/?workspace=review-statistics`。
- `observed`：同日冻结快照、第二来源交叉确认、成员级完整涨跌名单和跨日复盘历史仍未接入，因此工作区保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考工程，未执行 Git 写操作。
- 来源：`apps/desktop/src/feature/market-overview/ReviewStatisticsPanel.svelte`、`apps/desktop/src/feature/market-overview/review-statistics-presenter.ts`、`tests/features/review-statistics-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-28 异动语音播报工作区

- `confirmed`：信息总览第 02“异动语音播报”已接入独立懒加载页面，复用约 5 秒异动事件流和共享用户设置合同；不新增行情请求、Rust IPC、数据库表、云端 TTS、后台轮询、常驻进程或第三方依赖。系统语音只存在于 WebView 跨平台适配器，Windows WebView2 与 macOS WKWebView 共用同一接口。
- `confirmed`：纯 Presenter 负责严格校验、事件 ID 去重、中文播报文本、方向/优先级和最近 12 条视图；控制器首次只播最新事件，后续旧到新排队，覆盖暂停、继续、清空、关闭、失败推进、同步启动异常清理和离页销毁。`stale/missing/unavailable` 只展示不播报，也不补播旧事件。
- `confirmed`：新鲜验证通过全部根级 Node 契约、53 个 Vitest 文件 / 194 项、Vite 3680 模块生产构建、Rust 桌面端 324 项通过且 1 项显式性能测试 ignored、更新核心 11 项、14 个菜单和 756 项文件登记、rustfmt、2138 个项目文本文件 UTF-8/乱码扫描及项目差异检查。
- `confirmed`：浏览器 1280px 页面/工作区宽度为 `1280/1280`、`1023/1023`，760px 为 `760/760`、`485/485` 并切为单栏；无 Tauri 后端时事件行和队列为 0，阶段为“语音已关闭”，控制台无警告或错误。预览保留在 `http://127.0.0.1:1420/?workspace=movement-voice`。
- `observed`：交易所逐笔时间戳、第二来源和应用退出后的后台常驻播报尚未接入，因此工作区保持 `partial`。本阶段未生成发布产物，未修改参考工程，未执行 Git 写操作。
- 来源：`apps/desktop/src/feature/market-overview/MovementVoicePanel.svelte`、`apps/desktop/src/feature/market-overview/movement-voice-presenter.ts`、`apps/desktop/src/feature/market-overview/movement-voice-controller.ts`、`apps/desktop/src/platform/speech/webview-speech-engine.ts`、`tests/features/movement-voice-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-28 游资动向工作区

- `confirmed`：信息总览第 18“游资动向”已接入独立懒加载页面，复用第 17 的 `load_hot_money_tracking` 14 日证据包，不新增 Rust IPC、网络请求、缓存、数据库表、依赖、轮询或首屏预取。
- `confirmed`：纯 Presenter 只聚合快照保留的合法可见操作，按股票和精确席位—股票关系计算买入、卖出与净额；净额正、负、精确零分别归为净买入、净卖出和双向平衡。页面包含席位买卖方向分布、股票榜与席位贡献、龙虎榜资金概览和动向证据边界；题材映射固定缺失，不从文本推断。
- `confirmed`：新鲜验证通过根级 Node 契约、49 个 Vitest 文件 / 177 项、Vite 3672 模块生产构建、Rust 桌面端 324 项通过且 1 项显式性能测试 ignored、更新核心 11 项、14 菜单与 741 项文件登记、rustfmt 和 2123 个项目文本文件 UTF-8/乱码扫描。
- `confirmed`：浏览器 1280px 页面/工作区宽度为 `1280/1280`、`1021/1021`，股票榜与席位详情保持双栏；760px 为 `760/760`、`483/483` 并切为单栏。无 Tauri 后端时四项摘要均显示 `--`、股票按钮为 0，控制台无警告或错误。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考工程，未执行 Git 写操作。
- 来源：`apps/desktop/src/feature/market-overview/hot-money-flow-types.ts`、`apps/desktop/src/feature/market-overview/hot-money-flow-presenter.ts`、`apps/desktop/src/feature/market-overview/HotMoneyFlowsPanel.svelte`、`tests/features/hot-money-flows-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-28 当日分时显示兜底修复

- `confirmed`：修复个股观察当日分时为空的问题。时间线现在优先读取盘中归档快照；当天归档为空时，仅对当前交易日读取一次真实腾讯行情快照作为可见兜底，历史日期不使用实时数据混入历史。
- `confirmed`：新增“当前日真实快照兜底”和读取失败回归测试；Web 39 项聚焦测试、API 55 项聚焦测试和 Ruff 通过，生产构建通过。
- `confirmed`：便携 EXE 已重建并通过真实启动冒烟，窗口 337ms、API 5780ms、14/14 菜单通过、退出后无 `xiaoqibao.exe` 残留；最新 EXE SHA-256 为 `910FF6B57C291DE2CF75A0BF5CD603546AB92B8E9729CA059ABDE66A3D724682`，八个持久目录均保留，未操作通达信。
- 来源：`apps/api/src/qibao_api/a_shares/stock_timeline.py`、`apps/api/src/qibao_api/main.py`、`apps/api/tests/a_shares/test_stock_timeline.py`、`scripts/build-portable.ps1`、`scripts/run-portable-smoke.ps1`。

### 2026-08-28 个股观察双 K 线

- `confirmed`：个股观察的事件 K 线下方新增同一行双图，左侧为所选股票当日真实分时与成交量增量，右侧为最近 30 个真实交易日日 K、MA5/MA10/MA20 和成交量；桌面双列，900px 以下单列，遵循 A 股红涨绿跌。
- `confirmed`：后端复用既有盘中快照库与本地日线，不新增重复日线请求；分时读取失败或缺失时只影响左图，日线和事件仍可展示。当前股票会以 `stock_observation` 来源非阻塞登记到后台采样。
- `confirmed`：新鲜验证通过 Web `137` 个测试文件 / `805 passed`、API `1770 passed，1 skipped`、Ruff、Vite 生产构建、UTF-8/乱码扫描与 `git diff --check`；便携 EXE 冒烟窗口 `364ms`、API `7045ms`、14/14 菜单通过，结束后 `xiaoqibao.exe` 残留为 `0`。
- `confirmed`：最新便携 EXE 位于 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 为 `C57F3A7CA778F99CB9A95D18E2BB084866249083FAF35567664531F17EA3E4F5`；八个持久目录均保留，未操作通达信。
- 来源：`apps/api/src/qibao_api/a_shares/stock_timeline.py`、`apps/web/src/features/stock-timeline/StockTimeframeCharts.tsx`、`apps/web/src/features/stock-timeline/StockEventKline.tsx`、`scripts/build-portable.ps1`、`scripts/run-portable-smoke.ps1`。

- `confirmed`：信息总览剩余 7 个专题菜单（连板梯队、龙虎榜、游资动向、突破前高、低位放量、异动统计大全、板块赛道）完成 1440×900 桌面视觉回归；主体无横向溢出，指标卡宽度稳定，四项仪表保持同排，板块长内容按整行展示。新闻横向条仅在自身滚动容器内裁切，不撑破页面。
- `confirmed`：本轮 fresh 验证通过 Web `135` 个测试文件 / `795 passed`、API `1758 passed，1 skipped`、Ruff、Vite 生产构建、源码/文档 UTF-8 扫描和 `git diff --check`；staged EXE 冒烟窗口 `79ms`、API `4261ms`、14/14 菜单门禁通过，验证结束后 `xiaoqibao.exe` 残留为 `0`。
- `confirmed`：最新 staged EXE 位于 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable-staged-26c84057ceed44d89792fdefebf86f8a/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 为 `EB779168D2F4DF9BD6FC6492E6EEAD2E76C278607432D379D5EECCF81C6BF8A8`；真实发布数据覆盖 `99.94%`，量化策略与公司研究继续按真实证据缺口显示 `partial`。
- `observed`：当前环境没有默认 Rust toolchain，`cargo test --workspace --offline` 无法执行；已使用现有 Windows release/staged EXE 完成实际启动和 14 菜单运行门禁，未启动、关闭、重启或控制通达信。
- 来源：`apps/web/src/features/market-overview/overview.css`、`apps/web/src/features/market-overview/workspaces/MetricDrilldown.tsx`、`apps/web/src/features/market-overview/workspaces/WorkspaceBlocks.tsx`、相关回归测试、`scripts/run-portable-smoke.ps1`、本轮 Web/API/Ruff/构建/EXE 验证。

- `confirmed`：通达信已支持多目录递归发现、覆盖率排序、真实来源健康探针和永久库幂等导入；本地运维页提供导入按钮，重复导入按 `(symbol, trading_date)` 更新，不重复生成历史行。
- `confirmed`：本轮发布产物已重新计算并复制到 Codex outputs：NSIS SHA-256 为 `C9F76A2F34D131069E63EDCD244D7C1E43F74102621CCFB7AACE11673FAD233C`，便携 EXE SHA-256 为 `C35873AFBBE851403F576150A807412D47FBF6DDB6C3E4F1E175A2934DE8A38A`，便携 ZIP SHA-256 为 `C029F5CB88FB52C74FB593E5DA29013C558F5DBA1BA49386193BFA61156039F3`；此前哈希保留为历史记录。
- `confirmed`：TDX 多目录发现按覆盖率和最新交易日排序；来源健康在无目录、无可读文件和有可读日线时分别返回 `unavailable/partial/ready`；导入单个坏文件不阻塞其他文件，永久库按 `(symbol, trading_date)` 幂等 upsert，重复导入不会膨胀历史数据。
- `confirmed`：新增 `docs/verification/` 功能对照、来源矩阵、性能记录和恢复记录，并新增 `scripts/verify-architecture.mjs`、`scripts/run-windows-smoke.ps1` 作为可重复验收入口；前端门禁、架构登记、编码扫描、Vault 校验、更新回滚和 release EXE smoke 已重跑通过。
- `observed`：当前执行环境未提供 `cargo` 或 `rustup` 命令，本轮无法重新执行 Rust 编译/测试；产物来自已构建的 Windows x64 release，下一次工具链恢复后需补跑 Rust 门禁。
- `observed`：已尝试通过官方 Rustup 安装器恢复工具链；安装器长时间停在 stable 组件同步，仅生成部分工具链目录后已停止，当前仍不能据此宣称 Rust 编译通过。
- `confirmed`：新增 `infrastructure/sources/text_codec.rs`，统一识别 UTF-8/UTF-8 BOM，并对 TDX 文本元数据支持 GB18030/GBK 解码和 `had_errors` 质量标记；新增契约测试并纳入 `pnpm test`，不改变 `.day` 二进制解析。
- `confirmed`：新闻工作台已从仅显示条数升级为真实资讯列表，支持全部/已关联代码/未关联代码筛选、来源链接、来源/时间/代码字段和冻结证据事件钻取；未关联代码新闻仍不进入确定性依据，确定性事件影响计算继续保持待接入状态。
- `confirmed`：新增 `NewsEventImpact` DTO、`domain/news/news_event.rs` 领域纯函数和 `analyze_event_impact` IPC；完整标题/来源/时间/代码只返回证据绑定状态，缺少市场反应、行业归因或公告交叉验证时保持 `partial/unavailable`，不推断利好或利空。
- `confirmed`：公司研究 `load_company_research` 已接入统一腾讯行情缓存链路；可返回真实证券名称、实时证据版本和明确的财务/行业/公告/估值覆盖率，网络失败保留缓存状态，不伪造研究字段。
- `confirmed`：2026-08-25 新增独立 `infrastructure/sources/financial.rs` 东方财富财务主表适配器，解析报告期、营业收入、归母净利润、ROE、每股收益；新增 `FinancialSnapshot` 跨层 DTO 和公司研究财务面板，缺失字段保持 `null`，行业/公告/估值仍显示缺口。
- `confirmed`：财务主表已接入内存 + 用户缓存目录双层缓存，默认 6 小时 TTL；网络失败时回退缓存并保留明确告警，缓存仍与永久业务数据物理隔离。
- `confirmed`：公司研究已新增独立东方财富行业/板块分类与巨潮公告来源模块，分别使用 24 小时和 30 分钟用户缓存；页面独立展示行业板块、公告分类和原文链接，代码不一致或来源失败不进入确定性结论。
- `confirmed`：公司研究在行情确认后使用 `tokio::join!` 并发读取财务、行业和公告三条独立链路，减少网络串行等待；缓存和状态仍按来源隔离。
- `confirmed`：东方财富财务请求现返回最多 8 个报告期，`FinancialSnapshot.history` 按报告期降序排序；公司研究独立财务面板新增历史趋势表，不足的报告期保持缺失。
- `confirmed`：公司研究新增东方财富估值原值适配器 `infrastructure/sources/valuation.rs`，解析 PE(TTM)、PB、总市值和流通市值；使用独立 15 分钟内存/用户缓存，和财务、行业、公告通过 `futures_util::future::join4` 并发读取。
- `confirmed`：估值字段只展示来源原值；缺失或请求失败时保留 `null`、`partial/unavailable` 和告警，不计算未经来源支持的历史估值分位；新增独立 `ResearchValuationPanel.svelte` 和契约测试。
- `confirmed`：工作区 `.toolchain` 提供 Rust 1.98.0 stable；显式设置 `RUSTUP_HOME/CARGO_HOME/RUSTUP_TOOLCHAIN` 后，本轮 `cargo fmt --check`、`cargo check --workspace --offline`、39 个桌面单测、10 个 updater-core 单测和全部 doc tests 通过。
- `confirmed`：修复巨潮和东方财富分类测试中非 ASCII `br#` 字节字符串导致的 Rust 编译错误，并从 contracts crate 重新导出 `CompanyValuation`。
- `confirmed`：本轮重建 Windows x64 交付产物；NSIS 安装包 SHA-256 为 `09C07AF9DC81528EDCEF183B8D3E1876FBE2B1D6C0EB2E855043289C5C78E7F6`，便携 EXE 为 `A0DA14546067C375FB367921A00D2124581D03019743B34EF85270C876614B23`，便携 ZIP 为 `5E3C72836DCFB178B2527DB4D57AC22AD8027158A0C507012716072138B57E9C`；release EXE 启动 smoke 和更新成功/回滚 smoke 通过。
- `confirmed`：个股观察新增 `infrastructure/database/stock_queries.rs`，从永久 `business.sqlite3` 按代码读取最多 120 根日线，并通过 `load_stock_cockpit` 与腾讯快照、巨潮公告时间线合并；页面新增日线表格，缺失时保持 `daily_bars/timeline` 缺口。
- `confirmed`：股票目录搜索已补齐：`stock_queries.rs` 提供代码/中文名称模糊匹配、精确代码/名称前缀排序、结果上限、空查询拒绝和最近排序；`stock_search.rs` 提供本地优先搜索、6 位代码无本地命中时的腾讯增量补录、最近标的配置记忆；`StockSelector.svelte` 提供防抖、键盘回车/Esc 和最近标的下拉。配置字段使用 `serde(default)`，旧配置可无损迁移。
- `confirmed`：本轮新增 `tests/features/stock-search-contract.test.mjs`，Rust `stock_queries` 单测扩展至 44 个桌面测试；前端契约、Vitest、Vite 构建和文件登记 130 项门禁通过。未修改只读参考项目，未提交 Git。
- `confirmed`：公司研究新增 `CompanyResearchComparisonSnapshot`、`compare_company_research` IPC 和 `ResearchComparison.svelte`；两个标的通过共享单标的研究用例并发加载，结果保留各自版本、来源和缺口，未复制财务/行业/公告/估值解析逻辑。前端比较契约、Vite 构建和 Rust 桌面 44 项测试通过，文件登记更新为 131 项。
- `confirmed`：量化回测新增 `TaskRegistry`、`TaskSnapshot` 和 `start_backtest_task/get_task/cancel_task` IPC；回测移出 UI 线程，页面显示排队/读取/整理/完成或取消状态，取消后不发布半成品结果。量化任务契约、TaskRegistry 单测和前端生产构建通过，文件登记更新为 135 项。
- `confirmed`：量化回测核心新增循环级取消检查和进度回调；长样本计算期间会更新 `computing` 阶段并响应取消请求，任务不会序列化或发布半成品结果。
- `confirmed`：量化工作台新增独立 Kronos 预测适配器边界、`QuantForecast*` DTO、`run_kronos_forecast` IPC 和 `ForecastPanel.svelte`；默认返回 `unavailable/kronos-disabled`，不下载模型、不占用 CPU/GPU、不生成随机预测曲线。
- `confirmed`：监控中心新增独立规则 DSL、连续确认/恢复状态纯函数、`MonitorRuleEvaluation` DTO、`test_monitor_rule` IPC 和 `RuleEditor.svelte`；支持六类数值指标和比较符，缺少观测值不命中，测试动作不发送通知；文件登记库更新为 140 项。
- `confirmed`：本轮重新构建 Windows x64 release EXE，`target/release/yishu-desktop.exe` SHA-256 为 `19AA33A1BDA565180AC8152854CE6DCE9043B3FD96AEFF95CC538D3A745D58AE`；release 启动 smoke、更新成功/回滚 smoke 通过，参考项目工作树保持干净。
- `confirmed`：接入 Kronos 默认关闭边界后已重建 Windows x64 交付物；NSIS SHA-256 为 `1E81EF1732347C800BFCDF016DBCE3E24F89FBC4ED789F866B8E226E2B4E1FBB`，便携 EXE 为 `0066BFD6EA2FE4DF2CB736D144683E24D0AB93135268CC04304228ED15DAF639`，便携 ZIP 为 `60F6432F50A1DD8F50CF7694AD9DDEA3AB0E3D1A8F779E863F1BB9130AB57B84`；启动与更新回滚 smoke 通过。
- `confirmed`：接入监控规则 DSL 与编辑器后已重建 Windows x64 交付物；NSIS SHA-256 为 `0F54A3382AE4352C4A3F1FFDB1F4ADA4762B336C1C923B09A9BFD8B4D0951313`，便携 EXE 为 `5AFA9F983FE025DE57EB0D748CEDA552D5989F666072E378F3BCE3A521D060E2`，便携 ZIP 为 `D4194D38ED7755314C09E62261F37EBCD0122CC502AAF791E418939638FCFDD2`；启动与更新回滚 smoke 通过。
- `confirmed`：监控运行时已持久化规则状态快照和审计事件：连续命中/恢复次数、最近触发/恢复时间、冷却截止时间写入用户配置目录，触发/恢复审计追加到用户日志目录；新增站内通知、系统语音 pending 队列、飞书 Webhook 三个独立适配器，通道失败隔离且不阻塞规则状态机；监控页面展示通道可用性、运行时状态和最近审计。Rust 桌面单测 55 项、前端契约和生产构建均通过，文件登记库 146 项。
- `confirmed`：监控运行时增量后已重建 Windows x64 交付物：NSIS SHA-256 `86E82471EF3E8B096A9356E2D52FE8204D75612941A95D21BCC67791EBDA4CDE`，便携 EXE SHA-256 `7D0850DE7A0A4D77B56DFA9E0DB3860E034D74B22233433145934A0D6F3135A1`，便携 ZIP SHA-256 `85D7536368172E9E2E92B74D7431350B48E90CB2AE97C60E65B8A02029571837`；release 启动和更新成功/回滚 smoke 通过，参考工作树保持干净。
- `confirmed`：公司研究新增独立 AI 解释边界和面板；请求必须绑定研究证据版本，未配置端点/凭据或供应商适配器未启用时明确返回 `unavailable`，不发送证据、不生成随机文本、不占用 GPU/CPU；文件登记库更新为 149 项。
- `confirmed`：AI 边界增量后已重新构建 Windows x64 交付物：NSIS SHA-256 `E5A1FA687DF85E19D460CD5CBF3B9FC9229895D64045D9B0667CF4A338B4AFA8`，便携 EXE SHA-256 `3A7A27F7A4B57ED2A792F2E2AF3C7100538928504D16ADE6A6182B8254868AA1`，便携 ZIP SHA-256 `A0601E7F219CD9CD2E9862E5568326DE2D1BE0EE05929659AFF6216B0181DEE1`。
- `confirmed`：信息总览新增独立市场宽度来源和空闲加载链路：东方财富指数聚合接口只解析可核验的上涨/下跌/平盘字段，涨停/跌停字段缺失时保持缺口；指数首屏与宽度请求分离并使用 30 秒内存缓存，文件登记库更新为 151 项，Rust 桌面测试 59 项通过。
- `confirmed`：信息总览增量后已重建 Windows x64 交付物：NSIS SHA-256 `C696F4B72D80B21CC44807BBF438E7C584236AE3B387D1B57B686AA9DF6C300D`，便携 EXE SHA-256 `89A4B7084ACF7ED1DE45D01F82B13892CF8B2A32E6971C460D94DC385A5A4835`，便携 ZIP SHA-256 `9242D9E136BB11B4580BFCE36F2B23C037E21FBDAF541D31FFEA268E64094343`。
- `confirmed`：2026-08-26 完成信息总览验收闭环：腾讯指数首屏与东方财富市场宽度独立加载，宽度使用 30 秒内存缓存，指数可携带 `symbol` 钻取个股观察；缺失的涨停/跌停和全市场成交额不以代理值填充。
- `confirmed`：2026-08-26 新鲜验证通过 Windows release 启动与更新成功/健康超时回滚 smoke、`cargo fmt --check`、Rust workspace 59 个桌面测试和 10 个更新核心测试、前端测试/生产构建、14 菜单清单、151 项文件登记及 `git diff --check`；参考工作树保持无改动，未执行 Git 提交。
- `confirmed`：本轮新增后 workspace Rust 单测总数为 41 个桌面测试、10 个 updater-core 测试；文件登记库为 128 项；Windows x64 产物已重新生成，NSIS SHA-256 为 `98D0596CDD8CDCDE127C66FEF93D1FA2D68D59A4B2F1F295C98907DA7A9D1735`，便携 EXE 为 `7A73347AC731714261863E0C5776A595101DA41D946478891B0E1A84F264B07C`，便携 ZIP 为 `D7A4153AE4138BE0B09CB67127B311A906E5F3A24C8C81653F4C0D35DCE3E6E0`。
- `obsolete`：早前 Rustup stable 组件缺失导致 Rust 编译/单元测试无法执行；该限制已由工作区 `.toolchain` 恢复并被 2026-08-26 的完整离线测试结果替代。
- `confirmed`：2026-08-26 完成首次涨停、尾盘选股和候选证据情绪闭环：领域纯规则覆盖首次涨停、20 日排除、涨停日禁买、估值/位置缺失、回撤横盘和尾盘时间/阈值/来源冲突；后台任务支持进度、取消和短时复用，两套页面支持候选钻取。候选证据组件只汇总严格/观察数量、字段缺口和观测时间，不生成方向性分数。
- `confirmed`：视觉验收发现并修复 Svelte 5 仍使用旧 `new App` 构造器导致的空白窗口；入口改用 `mount` 并新增壳契约。真实本地页面已显示 14 个菜单以及首次涨停、尾盘选股两处候选证据摘要。
- `confirmed`：本轮 Rust workspace 69 个桌面测试和 10 个更新核心测试、前端契约/Vitest/生产构建、159 项文件登记、UTF-8 扫描、release EXE 1200ms 存活及更新成功/回滚 smoke 通过；最新 NSIS SHA-256 为 `C1B1A2DB0D6C5E558A25DAE191AF3C6DCA5C48034DB007DD2C31AF44CCF4B353`，便携 EXE 为 `6545FE9841C1AD21256C3756C7A054A6A83E11975C245BF915B1A962ECE8A0C4`，便携 ZIP 为 `C1711AB5902C983DB6FC36769C2DEAC3190874BA9224FBB768BDA96B83C98333`。
- `confirmed`：2026-08-26 完成量化图表、样本外验证和导出闭环：回测逻辑拆为独立领域与应用用例，总收益改为复合权益；按时间顺序 70%/30% 切分且验证区独立预热。前端无大型图表依赖，峰谷降采样最多渲染 240 点；JSON/UTF-8 BOM CSV 原子写入跨平台用户目录。
- `confirmed`：量化增量后 Rust 桌面 76 项、更新核心 10 项、前端 4 项、171 项文件登记、实际量化页面、release EXE 和更新回滚 smoke 通过；最新 NSIS SHA-256 为 `2FA0C7C5EF7DF041D86237308FB495F6E9A710F8C1C0CA375DAC8C2213ED242A`，便携 EXE 为 `B629E933B6C3EDB334BC90F929C46D6C4AC556C099EADB65A9482BA010EF039F`，便携 ZIP 为 `16D5BB58D627B97454C83C818FD58D69CBE57BFCDB978208DBB29B24F225086E`。
- `confirmed`：2026-08-26 完成新闻事件影响钻取：独立事件面板只展示冻结的标题、来源、时间、代码、缺失字段和证据理由；只有真实关联代码时才进入个股观察或公司研究，明确不推断利好或利空。
- `confirmed`：2026-08-26 完成本地运维长任务生命周期：共享任务状态新增暂停与暂缓，全面维护按本机扫描、过期缓存清理、数据库检查和独立备份分阶段执行；页面支持暂停、继续、重试和暂缓，暂停只在安全阶段边界生效。
- `confirmed`：上述增量后 Rust 桌面 77 项、更新核心 10 项、前端 4 项、全部架构与功能契约、生产构建、174 项文件登记、UTF-8 扫描和新闻/运维实际页面通过；参考工作树保持无改动，未执行 Git 提交。
- `confirmed`：2026-08-26 完成本地运维安全恢复闭环与 macOS 更新适配预留；恢复演练只使用用户备份目录内的合法备份并复制到独立临时库，不覆盖当前业务库。Windows/macOS 更新共享协议，macOS 以完整 `.app` 为替换边界；真实 Apple 签名、公证和 DMG 仍需 macOS runner 验证。
- `confirmed`：2026-08-26 最新 Windows release 性能重采记录到 `docs/verification/windows-performance-latest.json`：首个热环境窗口样本约 127ms、热启动 P50 约 102ms、热启动 P95 约 104ms；5 秒闲置 CPU 约 0.031%，工作集峰值约 41.29MiB，按进程 GPU 本地显存采样为 0B。上一轮 2319ms 首个样本保留为历史证据；两轮都不是干净机冷启动结论，真实远程 API P95 仍待固定交易时段复测。
- `confirmed`：2026-08-26 完成 Task 14 Step 1：统一配置存储拒绝路径逃逸，覆盖保存保留旧版本备份，损坏 JSON 返回明确错误；设置命令不再复制原子写逻辑，普通 IPC 序列化只返回密钥配置状态且不回显秘密值。SQLite 写锁占用返回明确 `busy/locked`，事务释放后数据写入和 `quick_check` 正常；现有任务注册表继续覆盖排队、阶段进度、暂停、恢复、取消、暂缓与终态边界。
- `confirmed`：本轮新鲜门禁为 Rust 桌面 91 项、更新核心 11 项、前端 6 项、全部 Node/架构/功能契约、Vite 生产构建、190 项文件登记和 UTF-8/乱码扫描通过；只读参考工作树保持干净，未执行 Git 提交。
- `confirmed`：Task 14 Step 1 增量后已重建 Windows x64 交付物并通过启动与更新回滚 smoke；NSIS、便携 EXE、便携 ZIP 的 SHA-256 分别为 `532A9F328F0E367AD1975E95FD83B01F4281A51F264EF8F2C86406D9E0BAE0E6`、`565D170D767725C37CC182B240807F0117A49AC0E5983ADE1047ECACA719F8FC`、`BC0EECCFCB4038352EC1C3DA38BAA4801643B39BFAD80274E003C0687155CC42`。
- `confirmed`：2026-08-26 完成风险工作台深化：真实持仓和观察篮子使用独立 DTO、原子配置文件、领域纯函数、应用用例、IPC 与 UI 面板；腾讯当前价只做增强，本地永久库日线计算 20 日回撤和年化波动，网络失败仍保留本地指标。观察篮子不展示持仓语义，行业、相关性和事件风险缺证据时保持缺口；监控模块旧持仓实现已删除。
- `confirmed`：风险增量后新鲜验证通过 Rust 桌面 95 项、更新核心 11 项、前端 10 项、全部功能契约、生产构建、204 项文件登记、245 个文本文件 UTF-8/乱码扫描和实际页面验收；参考工作树无跟踪文件改动，未执行 Git 提交。
- `confirmed`：风险增量后已重建 Windows x64 交付物并通过 release 启动、更新成功和健康超时回滚 smoke；NSIS、便携 EXE、便携 ZIP 的 SHA-256 分别为 `0E29619E60181CBB7AB048FF1D97934B6B9A566F64B567A239C1BDFFEF072659`、`8F417142BB924C48276CF72A0CEFBF928535B7092151613F2A1E1A2EE17DB018`、`F82591F5ACEF29054CB947F0FB9F4554E9EF0BDE70A8A3060F18D261C2AD7405`；便携包只含主程序和更新助手。
- `confirmed`：2026-08-26 完成历史价格结果复盘深化：永久业务库严格命中指定交易日；当时证据只使用复盘日及之前日线计算均线、区间收益、回撤、波动、60 日价格位置和 5 日量比，独立事后面板展示后续 1/5/20 个交易日结果与 20 日最大有利/不利波动。未来样本不足保持明确缺口，不使用邻近日期、当前行情或补造的三阶段决策日志。
- `confirmed`：历史增量后新鲜验证通过 Rust 桌面 96 项、更新核心 11 项、前端 10 项、全部 Node/架构契约、生产构建、213 项文件登记、256 个文本文件 UTF-8/乱码扫描和实际页面交互验收；参考项目两个工作树无跟踪文件改动，未执行 Git 提交。
- `confirmed`：历史增量后已重建 Windows x64 交付物并通过 release 启动、更新成功和健康超时回滚 smoke；NSIS、便携 EXE、便携 ZIP 的 SHA-256 分别为 `D15098FE313E55D0A178794B3C43F9918225137E434478290E9B6AE78EC92FA1`、`4D1DA40846988E2FB528C5970E1905C322B16BD32C6BDFC74BB9762CC914D16C`、`69FE12D112F821B5405DE43CE629086977229045533CF71524ED56A43B00F76E`；便携 ZIP 只含主程序和更新助手。
- `confirmed`：2026-08-26 完成真实三阶段决策冻结账本：只从当前真实运行时开始积累盘前、盘中、盘后全局 `TodayDecisionSnapshot`，不导入、不反推、不补造过去记录，不冒充完整个股建议或盘后逐条归因。永久 SQLite 账本按阶段建立追加式 SHA-256 链，相同证据幂等，触发器拒绝更新和删除，并要求冻结日期存在于永久库 `daily_bars`。
- `confirmed`：今日研判提供显式冻结面板，历史复盘提供三阶段账本面板；价格复盘和账本独立失败、分别保留成功快照。新鲜验证通过 Rust 桌面 106 项、更新核心 11 项、前端 Vitest 11 项、全部 Node 契约、Vite 构建、14 菜单、226 项文件登记、270 个文本文件 UTF-8/乱码扫描、实际页面、release EXE 1,200ms 存活和更新成功/健康超时回滚；参考项目两个工作树无跟踪文件改动，未执行 Git 提交。
- `confirmed`：决策账本增量后的 Windows x64 交付物已输出；NSIS、便携 EXE、便携 ZIP 的 SHA-256 分别为 `6EE92DCF464BDDFA8B4B3BC09C7F0CC8AB55E2E507E51AF6166364513E4C7F83`、`A25392A538F1DCCE0F7906BEECCC39034D080A8BFE0E538857078251E8772BE6`、`941A8A835B1D477D8E4D985F6B0501905A0AA4560DA86307032EE897C75B6763`；ZIP 只包含主程序与更新助手，不包含用户数据或凭据。
- `confirmed`：2026-08-26 完成信息总览本地永久日线市场区间复盘：自然日严格校验并对齐首尾真实交易日，单次 SQLite 聚合全市场收益、振幅和成交额，后台线程执行；前端显式触发、搜索、稳定排序、每页 50 行、错误保留和股票钻取，不新增网络源、轮询或物化区间表。信息总览仍因异动/快讯、热点和资金分层缺口保持 `partial`。
- `confirmed`：5,000 股票、110,000 根合成日线的显式聚合性能测试在当前 Debug 环境返回 5,000 行耗时 318 ms；窄窗口验收发现并修复全局 1080px 最小宽度，760px 视口已无页面级水平溢出。新鲜验证通过 Rust 桌面 116 项、显式性能测试 1 项、更新核心 11 项、前端 Vitest 14 项、全部 Node 契约、Vite 构建、239 项文件登记和 283 个文本文件编码扫描；参考项目两个工作树未改动，未执行 Git 提交。
- `confirmed`：市场区间复盘增量后的 Windows x64 交付物已输出；NSIS、便携 EXE、便携 ZIP 的 SHA-256 分别为 `9B03437C2CAB2A40E8224693331CA880E8B8DDC6AF696261D1665A2E8620B43C`、`19B8894E2A99E863F52E29FFFA702B70AB137F952CE2DA4102E85FD9E33F3EEA`、`D4592CB035778E2474793DCD166DE67FE664E14CF3825FF5369DCE182E6E2C57`；ZIP 只包含主程序与更新助手，release 启动和更新成功/回滚 smoke 通过。
- `confirmed`：2026-08-26 完成信息总览市场异动与 7×24 快讯：东方财富公开快讯由统一 HTTP 客户端串行节流，单次按需读取；60 秒内存/用户缓存、同请求去重、三次失败熔断和 stale-if-error 已接入。条目只接受标题与来源时间，稳定去重，只提取原文明示六位代码和异动词；无利好/利空方向字段，无真实 URL 时不伪造链接。
- `confirmed`：快讯面板支持页面空闲单次加载、显式刷新、失败保留旧列表、标题/摘要/代码搜索、市场异动/明示代码筛选、来源打开和个股钻取；本地实际页面与 760px 无水平溢出通过。Chrome 远程调试未授权，按联网安全规范未绕过执行真实端点采样，该外部环境边界保留在验证记录中。
- `confirmed`：快讯增量后新鲜验证通过 Rust 桌面 125 项、更新核心 11 项、前端 Vitest 18 项、全部 Node 契约、Vite 构建、248 项文件登记和 306 个项目文本文件 UTF-8/乱码扫描；参考项目两个工作树无跟踪文件改动，未执行 Git 提交。
- `confirmed`：快讯增量后的 Windows x64 交付物已输出；NSIS、便携 EXE、便携 ZIP 的 SHA-256 分别为 `643BBA5F1A54EC79251B43AD82C4E5FE6C68A4D932B0673B0185C2D72F60211F`、`1F13068E89BD96241454D1597DF22B96A5012D74D39D6013D9523E61A56179EE`、`CBA8CE110CEB3DC12A15BF31E20F3CFFE842CCE8C6BA5F79535FC72C4846387B`；ZIP 只含主程序和更新助手，release 启动及更新成功/回滚 smoke 通过。
- `confirmed`：2026-08-26 完成信息总览市场热点题材聚类：同花顺公开端点按交易日单次读取，复用 UTF-8 BOM/GB18030/GBK 解码；错日、坏代码、空名称/题材、重复 ID/股票被严格丢弃。人工 `reason` 只按 `+` 确定性拆分，股票数量仅表示来源样本数，不生成方向、热度、持续性或交易评分。
- `confirmed`：热点链路使用通用 JSON 两级缓存、5 分钟 TTL、同日期请求去重、独立三次失败熔断和同日 stale-if-error；不使用问财签名接口，不保存永久热点表，不轮询，不携带凭据或用户数据。前端支持北京时间默认日期、显式历史日期、题材/名称/代码搜索、至少 2/3 只筛选和股票钻取。
- `confirmed`：热点增量后新鲜验证通过 Rust 桌面 133 项、1 项既有显式性能测试忽略、更新核心 11 项、前端 Vitest 21 项、全部 Node/架构/功能契约、Vite 构建、14 菜单、260 项 YAML/Markdown 文件登记和 318 个项目文本文件 UTF-8/乱码扫描。1280px 与 760px 页面均无水平溢出，控制台无警告或错误；普通浏览器无 Tauri IPC，真实端点可用性未冒充验证。参考项目两个工作树已跟踪与暂存差异为 0，未执行 Git 提交或推送。
- `confirmed`：热点增量后的 Windows x64 交付物已输出；NSIS、便携 EXE、便携 ZIP 的 SHA-256 分别为 `4D12954C71DD30E01A577E64859C684555B8D0D9D6869C16E993099AE9A9292F`、`21BA5336D8D0D0353E4BD1754CC32CDE58F372877C3AC91250ED7ADC59BC0C7D`、`9258060981AEA592B54C0524D4C92F51F6421B0C41B430134C64407BC521C492`。ZIP 只含主程序和更新助手；release 主程序 1,200ms 存活，更新成功激活及健康超时回滚均保留用户配置。
- `confirmed`：2026-08-26 完成信息总览行业资金分层：东方财富行业板块公开端点单次返回 `f62/f66/f72` 主力、超大单和大单原始净额，最多处理 200 行；坏代码、空名称、非有限主力净额和重复代码严格丢弃，可选金额缺失时保持空值，不推算中单、散户、北向历史、热度、方向或交易建议。
- `confirmed`：资金链路复用统一 HTTP 客户端、东方财富一秒串行门和通用 JSON 两级缓存；60 秒 TTL、同请求去重、独立三次失败熔断与 stale-if-error 已接入，不写永久业务库、不建立资金历史表、不轮询。前端支持名称/代码搜索、全部/净流入/净流出筛选和最多 16 行统一零轴展示。
- `confirmed`：资金增量后新鲜验证通过 Rust 桌面 138 项、1 项既有显式性能测试忽略、更新核心 11 项、前端 Vitest 24 项、全部 Node/架构/功能契约、Vite 构建、14 菜单、271 项 YAML/Markdown 文件登记和 325 个项目文本文件 UTF-8/乱码扫描。1280px 与 760px 页面无水平溢出，搜索和方向筛选可切换，控制台无警告或错误；普通浏览器无 Tauri IPC，未冒充实时东方财富端点证据。参考项目两个工作树跟踪与暂存差异为 0，未执行 Git 提交或推送。
- `confirmed`：资金增量后的 Windows x64 交付物已输出；NSIS、便携 EXE、便携 ZIP 的 SHA-256 分别为 `7E833546C1BA431B9EFCB3961887A357056A124023B404F878001322986BE56A`、`4B784F468AECD7445D3A5FF678BA572BBE9BF0172B99530F01AE82227BD75665`、`74651F4E256FA606BF858D82F2EEBE0AC090357E44634FA87B305C88196D653C`。ZIP 只含主程序和更新助手；release 主程序 1,200ms 存活，更新成功激活及健康超时回滚均保留用户配置。

## 已确认需求

- 程序安装目录和用户配置、永久数据、缓存、日志、备份、临时目录物理隔离。
- 更新必须签名校验、原子激活、健康确认和失败回滚，不能触碰用户目录。
- 永久业务数据与可重建缓存分库；长期数据需要 TTL、归档、VACUUM、备份校验和恢复到新目录。
- 每个菜单/业务模块单一职责，生产源文件必须登记到 `docs/architecture/file-registry.yaml` 和可读视图。

## 技术与结构

- Rust stable + Tokio + reqwest/rustls + rusqlite/WAL 负责业务、网络、数据库和后台任务。
- Tauri 2 负责桌面窗口和 IPC；Svelte 5 + TypeScript + Vite 负责独立页面和组件。
- `crates/platform-abstraction` 收拢 Windows/macOS 路径、凭据和文件系统差异；`crates/contracts` 定义跨层 DTO。
- `docs/architecture/feature-map.yaml` 是功能覆盖清单；`docs/architecture/file-registry.yaml` 是文件职责唯一登记源。

## 已确认决策

- `confirmed`：品牌名称固定为“一树-A股观测台”。
- `confirmed`：参考目录 `D:/Users/90090/Documents/金融财经` 及其工作树只读，当前新项目不依赖其运行时文件。
- `confirmed`：真实数据不足时保留状态和缺口，禁止零值、随机值或旧日期冒充实时数据。

## 风险与阻塞

- `confirmed`：更新核心已完成独立助手、暂存激活、用户目录重叠保护、健康超时回滚和事务日志烟测；生产服务端签名密钥与真实下载源仍需发布环境配置。
- `observed`：新闻工作台存在错码被重标、整体状态被错误压成 `missing`、默认标的自动请求和编排行为测试不足；完成度文档需服从修复后的新鲜证据。
- `observed`：个股事件影响未选择状态与注册表依赖登记需修复；交易所逐笔、原子同刻多源快照、独立临时公告和完整因果归因仍是产品级缺口。

## 下一步

1. 先修复新闻严格同股、状态矩阵、显式提交/晚到隔离和 `execute` 行为测试，并回撤或更新超前完成口径。
2. 将个股事件未选择状态改为 `missing`，修正两处注册表依赖并重跑对应门禁。
3. 继续补齐交易所逐笔、临时公告、跨重启日历同步和原子同刻多源证据；缺口保持真实降级。
4. 发布阶段再在 macOS runner 和干净 Windows x64 环境完成签名、公证、安装升级、回滚及用户数据保留验收。

## 来源

- 当前新项目：`D:/Users/90090/Documents/ChatGPT/A股平台`
- 只读参考项目：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research`
- 用户任务目标：`01a03785-a8a0-7a42-88d4-836458a08fb1`

## 2026-08-26 两市成交额增量

- `confirmed`：信息总览顶部“两市成交”已改为从用户永久库 `business.sqlite3.daily_bars.amount` 汇总，不再保留空字段，也不使用上证指数与深证成指成交额做代理。聚合只包含沪深 A 股前缀，并以最近 30 个有数据日期中的最大有效股票数为基准，选择覆盖率至少 80% 的最新交易日；金额原始单位为元，前端换算亿元。
- `confirmed`：成交额查询在后台线程执行，不联网、不轮询、不建立物化成交表；页面同时展示交易日、有效样本数、基准样本数和覆盖率，因此该值明确是本地最新高覆盖交易日证据，不冒充盘中实时成交额。
- `confirmed`：本阶段新鲜门禁通过 Rust 桌面 142 项、更新核心 11 项、前端 Vitest 26 项、全部 Node 契约、Vite 生产构建、14 菜单、282 项 YAML/Markdown 文件登记及 UTF-8/乱码扫描；既有 5,000 股票显式性能测试保持忽略。参考项目两个工作树已跟踪与暂存差异为 0，未执行 Git 提交或推送。
- `confirmed`：Windows x64 安装包、便携 EXE、便携 ZIP 已重建；SHA-256 分别为 `ED558EA254FF84A01ABB8E6645F69344C6F323E0C1E908519D03988BE2F46D5C`、`B73A1B852A0123A91ACDA5BCF6DCFAE3DB41E95462F4161893C8BC8F0EE69A45`、`943DCB6E0ABD9330F90E16FEFF05A6A918D9FC73C21289105F3BFCF1CA3B68E3`。release 主程序 1,200 ms 存活，更新成功激活和健康超时回滚均保留用户配置；ZIP 只含主程序和更新助手。
- `confirmed`：下一阶段按完成度审计推进“今日研判九因子”，继续坚持真实证据不足时显示 `partial/stale/missing/unavailable`，不补造历史或方向性结论。

## 2026-08-26 九因子市场温度增量

- `confirmed`：今日研判新增独立九因子市场温度链路。波动率情绪、成交活跃度、价格强度、市场广度、涨跌停情绪和赚钱效应由永久日线库最新高覆盖交易日计算；每股最多流式读取 252 根日线，后台执行，不轮询、不新增物化表。
- `confirmed`：风险偏好、板块扩散情绪和风格风险偏好因缺少可靠债券基准、时点行业映射和无歧义大小盘序列而保持空值。有效权重覆盖不足 70% 时不生成总分；有分数时也只对已覆盖因子归一化，不作为个股买卖建议。
- `confirmed`：涨跌停统计只纳入名称不含 ST 且至少有 6 根历史的样本，主板按 10%、创业板/科创板按 20%；IPO 等特殊无涨跌幅阶段仍列为限制，不伪装成全市场精确涨跌停口径。
- `confirmed`：新鲜验证通过 Rust 桌面 145 项、更新核心 11 项、前端 Vitest 28 项、全部 Node/架构契约、Vite 构建、14 菜单和 294 项文件登记；Windows x64 安装包、便携 EXE、便携 ZIP 哈希分别为 `3C68AA8D730F84587B199538BA2141161B7B05CA23B85858ECF5CF358DD4A89E`、`EEEE62EF1CA21D6929514375F6E688DE85FD8BFE96C2B5F22870814B5BA8529A`、`BF5017537EA04A86F07DA20F3CDEAC49CD8D37CAD022673AC3DEA3CC125E473C`；启动、更新成功和回滚 smoke 通过，用户配置保持不变。

## 2026-08-26 单只候选情绪观察增量

- `confirmed`：首次涨停与尾盘选股新增任务绑定的单只“情绪观察”入口，请求必须同时携带 `task_id + symbol`；后端在联网前验证任务已完成、类型受支持、结果可反序列化且股票确实属于该任务候选列表。情绪结果不修改候选排序、筛选状态或原行动字段。
- `confirmed`：新闻、热点、资金固定权重为 40/30/30，可用权重低于 60% 不评分，缺失分项不按零分参与。热点使用候选交易日的同花顺人工题材证据；资金使用东方财富单股最多 120 日主力净额和本地永久库候选日前 20 日成交额，坏值和不足样本保持不可用。
- `confirmed`：个股资金流复用统一网络客户端、东方财富域名级一秒串行门、5 分钟内存/用户缓存、同请求去重、独立熔断和 stale-if-error；不写永久业务库，不建立资金历史表，不轮询。
- `confirmed`：新闻倾向因尚无冻结引用、非降级解释和至少 0.65 置信度，继续明确为 `unavailable`；热点与资金同时可用时覆盖率为 60%，只形成 `partial` 观察分，不冒充完整情绪结论。
- `confirmed`：本阶段新鲜验证通过 Rust 桌面 159 项、更新核心 11 项、前端 Vitest 11 个文件 31 项、全部 Node/架构/功能契约、Vite 生产构建、14 菜单、308 项 YAML/Markdown 文件登记、362 个项目文本文件 UTF-8/乱码扫描和 `git diff --check`；1 项既有 5,000 股票显式性能测试保持忽略。
- `confirmed`：真实 Tauri 窗口在 1456px 与 760px 验收首次涨停和尾盘选股页面；当前隔离用户目录没有 TDX 配置和永久日线，页面如实显示来源不可用且没有生成假候选，因此单只详情的真实数据点击仍需在产生真实候选任务后补验。
- `confirmed`：Windows x64 NSIS、便携 EXE、便携 ZIP 已重建，SHA-256 分别为 `3D9F5D09BF9F11B7DE0A252790CCAE815B266B66D434162378FC6F0E231F071A`、`A21F83985BF0C1163DCE0EE5EC0549D1006DA5FDC6E7DFD6BAE3269875345191`、`E41A0986E3D370B93BEB2C190BE5F536F216E9710045CDCDB7544B69AF90D1AC`。ZIP 只含主程序和更新助手；release 主程序 1,200ms 存活，更新成功激活与健康超时回滚均保持隔离用户配置。
- `confirmed`：两个参考工作树跟踪与暂存差异均为 0，本项目未执行 Git commit、push、merge 或 PR。
- `confirmed`：下一项优先缺口为候选新闻冻结证据层；先复用既有个股新闻来源建立交易日边界、原文引用和可追溯列表，在可靠解释与置信度门槛满足前继续不计算新闻倾向分。

## 2026-08-26 候选新闻合格解释增量

- `confirmed`：候选新闻解释改为默认关闭、用户显式触发。首次打开候选详情只读取已有七天合格缓存，不自动调用模型；IPC 会重新验证已完成任务中的 `task_id + symbol` 并重建当前交易日边界内的冻结新闻，请求证据 ID 必须与冻结集合完全一致。
- `confirmed`：OpenAI-compatible 适配器只发送证据 ID、标题、来源和发布时间；严格拒绝未知字段、越界引用、无引用事实、无反方证据、交易指令、降级、方向不确定和置信度低于 0.65 的输出。只有合格解释才由后端按正面 75、中性 50、负面 25 纳入 40% 新闻分项，前端不计算分数。
- `confirmed`：AI 使用独立单并发网络客户端，连接超时 3 秒、总超时 12 秒、零重试和独立三次失败熔断；模型失败不清空热点、资金、候选排序、筛选状态或原行动字段。缓存键绑定任务、股票、截止日、模型、提示词版本和证据集合。
- `confirmed`：AI 密钥只存 Windows Credential Manager 或 macOS Keychain，普通设置、响应、日志和缓存不含秘密值；设置页支持启用、替换和明确清除且不回显密钥。macOS Keychain FFI 仍需 macOS runner 实机编译和读写验证。
- `confirmed`：本阶段新鲜验证通过 Rust workspace 桌面 181 项、更新核心 11 项、前端 Vitest 34 项、全部 Node 功能与架构契约、Vite 生产构建、329 项文件登记、383 个文本文件 UTF-8/乱码扫描和 rustfmt。真实 Svelte 组件在 1456px/760px 无页面级横向溢出，临时视觉夹具已删除；两个参考工作树跟踪与暂存差异均为 0。
- `confirmed`：遵照用户最新要求，本阶段没有生成或重建安装包、便携 EXE、ZIP，也没有执行 Git commit、push、merge 或 PR。项目总体仍未完成，下一步继续按完成度审计关闭其余 `partial` 功能。

## 2026-08-26 量化回测交易成本增量

- `confirmed`：量化回测新增 10 万元默认研究本金、100 股整手现金账本、信号后次日开盘买入、固定持有期后开盘卖出、买入上浮/卖出下调滑点、买卖双边佣金和卖出单边印花税。所有公式集中在独立跨平台领域模块，前端和导出不重复计算。
- `confirmed`：回测快照新增信号日、原始开盘、实际成交价、股数、毛/净收益、佣金、印花税、滑点和总成本；汇总新增初始/结束权益与三项成本。时间顺序 70/30 训练区和验证区复用同一成本策略，JSON 与 UTF-8 BOM CSV 导出包含同一后端结果。
- `confirmed`：量化页新增独立交易成本面板，支持本金及三项费率输入、后端成本摘要和最近 50 笔闭合交易明细。1456px 与 760px 均无页面级横向溢出，760px 参数两列展示完整，浏览器控制台无警告或错误。
- `confirmed`：新鲜门禁通过 Rust workspace：契约 1 项、桌面 186 项通过且 1 项显式 5,000 股票性能测试保持 ignored、更新核心 11 项；前端 Vitest 34 项、全部 Node 契约、Vite 生产构建、334 项文件登记、388 个文本文件 UTF-8/乱码扫描、rustfmt 和项目 `git diff --check` 均通过。
- `confirmed`：交易成本完成后量化模块仍保持 `partial`；停牌顺延、涨跌停不可成交、复权/公司行动、完整交易日历、策略研究和决策日志继续作为真实缺口，不冒充完整交易所撮合。
- `observed`：本轮只读验收时，参考主目录 tracked/staged 仍为零；参考工作树 staged 为零，但出现 15 个市场总览/资金流/决策相关 tracked 修改和 1 个未跟踪路由文件，与本轮量化文件无交集。当前任务未写入、未清理这些外部状态，后续只读参考必须继续避开任何修改。
- `confirmed`：本阶段没有生成或重建安装包、便携 EXE、ZIP，也没有执行 Git commit、push、merge 或 PR。项目总体仍未完成。

## 2026-08-26 个股观察独立诊断增量

- `confirmed`：个股观察新增固定九分区诊断：行情、量价、趋势、估值、基本面、资金、事件、行业和风险。诊断复用 `load_stock_cockpit` 同一次腾讯快照与最多 120 根永久库日线，不重复联网、不轮询、不写诊断快照或物化指标表。
- `confirmed`：后端集中计算 MA5/MA20、5/20 日收益、20 日平均成交额、量比、距 MA20、20 日最大回撤和年化波动率；前端只展示 DTO。恰好 20 根日线时需要 21 个收盘价的 20 日收益保持空值；日线少于 20 根、重复日期、坏价格或来源不一致时量价与趋势整体不可用。
- `confirmed`：估值、财务、资金、行业和完整事件证据没有绑定当前请求时明确为 `unavailable`，并指向已有按需模块；公告时间线不冒充已核验事件诊断。风险分区只输出缺失数量、回撤、波动与 `observe/blocked` 边界，不生成买卖、仓位或方向性评分。
- `confirmed`：新增公共 `daily_metrics.rs`，风险提醒、历史复盘和个股诊断共用均值、收益、回撤与波动公式，删除重复实现。新增独立契约、领域、应用用例、前端专属类型和 `StockDiagnosisPanel.svelte`，文件登记库更新为 343 项。
- `confirmed`：新鲜门禁通过 Rust workspace：contracts 1 项、桌面 192 项通过且 1 项显式 5,000 股票性能测试保持 ignored、更新核心 11 项；全部 Node 契约、前端 Vitest 34 项、Vite 生产构建、rustfmt、架构登记、397 个文本文件 UTF-8/乱码扫描和项目 `git diff --check` 均通过。
- `confirmed`：1456px 与 760px 独立响应式视觉夹具均渲染九个分区且页面级 `scrollWidth` 不超过视口，临时夹具已删除。真实桌面开发程序已成功编译并启动；本次未把视觉夹具冒充真实行情端点证据。
- `observed`：只读核对时参考主目录仍有既有未跟踪文件；参考工作树仍有 15 个市场总览、资金和决策相关 tracked 修改。本阶段没有写入、清理或还原参考目录。
- `confirmed`：本阶段没有生成或重建安装包、便携 EXE、ZIP，也没有执行 Git commit、push、merge 或 PR。个股观察仍因分时与五个研究分区的同请求证据绑定缺口保持 `partial`，项目总体仍未完成。

## 2026-08-26 个股当日分时增量

- `confirmed`：个股观察新增腾讯公开当日分钟链路，严格校验股票节点、交易日期、交易时段、分钟顺序、累计成交量额单调性和 242 点上限；后端唯一计算分时均价与分钟成交量，前端不重复公式。2026-08-26 对 `600519` 的公开端点只读采样返回截至 11:30 的 121 个真实分钟点。
- `confirmed`：链路使用 10 秒内存/用户缓存两级短缓存、同请求去重、独立三次失败/60 秒冷却熔断和同股票 stale-if-error；个股快照与分时并行读取，请求序号阻止切换股票后旧响应覆盖，手动刷新失败只保留同股票旧图。
- `confirmed`：独立 `StockIntradayPanel.svelte` 使用原生 SVG 展示现价、后端均价和分钟量柱，不引入 ECharts、Python/mootdx 边车、轮询、SSE 或 WebSocket。真实组件以腾讯午间快照采样在 1456px/760px 验收，两个视口均无页面级横向溢出；来源、日期、刷新、午间空档、旧快照和无数据状态清楚，直达页签没有控制台错误，临时夹具已删除。
- `confirmed`：新鲜门禁通过 Rust contracts 3 项、桌面 200 项、更新核心 11 项；1 项既有 5,000 股票显式性能测试保持 ignored。全部 Node 契约、前端 13 个文件 38 项、Vite 生产构建、14 菜单、354 项文件登记、408 个项目文本文件 UTF-8/乱码扫描、rustfmt 和项目 `git diff --check` 均通过。
- `observed`：只读核对时参考主目录仍有既有未跟踪文件，参考工作树存在外部已有 tracked/untracked 差异；本阶段没有写入、清理或还原参考目录。
- `confirmed`：用户明确要求项目最终完成并再次提出生成指令前，不生成或重建安装包、便携 EXE、ZIP。本阶段也没有执行 Git commit、push、merge 或 PR。个股观察下一核心缺口为把估值、财务、资金、行业和事件五个分区绑定到同一次请求的冻结证据；项目总体继续保持未完成。

## 2026-08-26 个股五类研究证据同请求绑定增量

- `confirmed`：新增独立 `load_stock_research_cockpit` 增强 IPC；基础驾驶舱与当日分时先并行显示，随后单次读取估值、财务、资金、行业和公告事件，并生成同一 `freeze_id/frozen_at`。增强失败保留基础结果，观察、分时和研究使用独立请求序号，切换股票后旧响应不能串标。
- `confirmed`：公司四证据已拆为公共缓存/去重/熔断加载器、四个来源策略文件和一个薄并行编排文件；公司研究与个股观察复用同一套来源用例。个股资金继续复用候选情绪的唯一共享用例，保留 5 分钟缓存、5/20 日门槛、同股旧值回退和独立熔断，没有新建数据库表或复制计算逻辑。
- `confirmed`：腾讯快照改为 30 秒两级缓存优先和同请求去重，基础请求完成后的增强装配不重复联网。九分区只消费拥有型冻结证据；缺失、字段不全或旧缓存保持 `partial/stale/unavailable`，公告事件最高 `partial`，不推断利好、利空、买卖或仓位。
- `confirmed`：本阶段新鲜验证通过 Rust contracts 4 项、桌面 204 项且 1 项显式 5,000 股票性能测试保持 ignored、更新核心 11 项和全部 doc tests；前端 13 个 Vitest 文件 38 项、全部 Node 契约、Vite 生产构建、14 菜单、368 项文件登记、422 个文本文件 UTF-8/乱码扫描、rustfmt 与项目 `git diff --check` 通过。
- `confirmed`：真实 `StockDiagnosisPanel.svelte` 临时夹具在 1456px/760px 验收基础、加载、完整冻结、`partial`、`stale`、`unavailable` 共 12 个组合，非空状态均为九分区，完整状态展示 18 个可换行证据 ID；两种视口无水平溢出，控制台无警告或错误，临时夹具随后删除。
- `observed`：只读核对时参考主目录 tracked/staged 为零并保留既有未跟踪文件；参考工作树 staged 为零，存在外部已有 36 个 tracked 修改和 5 个未跟踪文件。本阶段没有写入、清理或还原参考目录。
- `confirmed`：遵照用户最新要求，本阶段没有生成或重建安装包、便携 EXE、ZIP，也没有执行 Git commit、push、merge 或 PR。个股五类证据绑定子能力完成，但研究多源交叉确认、逐笔盘口、历史分钟线及其余菜单真实缺口仍存在，项目总体保持未完成。

## 2026-08-26 公司研究真实财务与现金流增量

- `confirmed`：只读核验发现东方财富 `RPT_F10_FINANCE_MAINFINADATA` 旧请求字段 `TOTAL_OPERATE_INCOME` 已失效，上游返回 `success=false/code=9501`。财务适配器改为有界请求 `REPORT_DATE,TOTALOPERATEREVE,PARENTNETPROFIT,ROEJQ,EPSJB,NETCASH_OPERATE_PK,NETCASH_INVEST_PK,NETCASH_FINANCE_PK` 八个有效字段，并显式传播上游业务错误；空值、破折号和非有限数值继续保持缺失。
- `confirmed`：经营、投资和筹资现金净额复用同一次东方财富财务主表请求、同一拥有型快照和同一冻结证据，没有新增新浪请求、数据库表、轮询或前端计算公式。财务缓存键升级为 `eastmoney:financial:v2:{symbol}`，旧缓存可兼容读取但不会覆盖新字段；八项完整为 `ready`，缺项为 `partial`，旧缓存回退优先保持 `stale`。公司研究版本升级为 `research-v3`，摘要使用 `财务 x/8`。
- `confirmed`：公司研究新增独立 `ResearchCashFlowPanel.svelte`，展示最新与历史经营/投资/筹资现金净额原值；负数保留符号，缺失显示 `--`，不可用状态明确不补零、不推断方向。公司页只组合同一 `financial` 快照，个股基本面只复用经营现金流原值。
- `confirmed`：新鲜门禁通过 Rust contracts 4 项、桌面 204 项且 1 项显式 5,000 股票性能测试保持 ignored、更新核心 11 项及全部 doc tests；全部 Node 契约、13 个 Vitest 文件 38 项、Vite 生产构建、14 菜单、373 项文件登记、427 个项目文本文件 UTF-8/乱码扫描、rustfmt 和项目 `git diff --check` 均通过。
- `confirmed`：真实现金流组件在 1456px 与 760px 验收八项完整、部分缺失、负数、全不可用和长报告期共 10 个组合；页面无水平溢出，760px 表格只在自身容器横向滚动，控制台无警告或错误，临时视觉夹具随后删除。
- `observed`：只读复核时参考主目录 tracked/staged 为零并保留 278 个既有未跟踪文件；参考工作树 staged 为零，存在外部已有 38 个 tracked 修改和 5 个未跟踪文件。本阶段没有写入、清理或还原参考目录。
- `confirmed`：本阶段没有生成或重建安装包、便携 EXE、ZIP；既有交付物最新修改时间仍为 2026-08-26 08:41。当前项目仍无 Git HEAD，没有执行 Git commit、push、merge 或 PR。公司研究仍因完整三表、商业模式、壁垒、催化与真实 AI 供应商等缺口保持 `partial`，项目总体继续保持未完成。

## 2026-08-26 新闻页真实热点复用增量

- `confirmed`：新闻页直接组合既有 `MarketHotspotPanel.svelte`，继续由该组件独占 `load_market_hotspots` IPC、同花顺公开来源、5 分钟两级缓存、同请求去重、熔断和同交易日旧值回退；新闻页只转发股票钻取事件，没有新增来源、请求、缓存、轮询、数据库表或依赖。
- `confirmed`：新闻热点与信息总览消费同一热点快照，继续保留单一来源的 `partial/stale/missing/unavailable` 边界，不计算热度分、方向、持续性或交易建议。新闻菜单仍因新闻与题材逐条行业归因、公告交叉验证和纠错记录缺口保持 `partial`。
- `confirmed`：真实共享组件临时夹具在 1456px 与 760px 验收 `partial`、`stale`、`unavailable` 共六个视口/状态组合，以及长题材、长股票名称、日期、搜索、最少股票数筛选和股票钻取；桌面为双列、窄屏为单列，所有组合页面级 `scrollWidth` 不超过 `clientWidth`，控制台无警告或错误。夹具、空目录和验收页签随后删除。
- `confirmed`：清理夹具后的新鲜门禁通过 Rust contracts 4 项、桌面 204 项且 1 项既有 5,000 股票性能测试保持 ignored、更新核心 11 项和全部 doc tests；全部 Node 契约、13 个 Vitest 文件 38 项、正式 Vite 构建、14 菜单、375 项文件登记、429 个项目文本文件 UTF-8/乱码扫描、rustfmt 和项目 `git diff --check` 均通过。
- `observed`：只读复核时参考主目录 tracked/staged 为零并保留 278 个既有未跟踪文件；参考工作树 staged 为零，存在外部已有 40 个 tracked 修改和 5 个未跟踪文件。本阶段没有写入、清理或还原参考目录。
- `confirmed`：本阶段没有生成或重建安装包、便携 EXE、ZIP；既有交付物最新修改时间仍为 2026-08-26 08:41。当前项目仍无 Git HEAD，没有执行 Git commit、push、merge 或 PR；项目总体继续保持未完成，下一步按完成度审计推进 P1 真实缺口。

## 2026-08-26 新闻公告交叉验证、纠错与阶段 EXE

- `confirmed`：新闻事件按需复用公司研究唯一巨潮公告链路、30 分钟两级缓存、请求去重、独立熔断和同股票旧值回退；无合法 6 位代码时不访问公告来源。自动关系只允许标题完全匹配、新闻包含完整公告标题和北京时间同日候选，最多 5 条，继续保持无方向结论。
- `confirmed`：新增永久 `news_corrections` 表和独立 repository；人工结论以稳定事件 ID 唯一 upsert，只保存状态、500 字以内说明和当前候选 HTTP(S) 公告链接，不保存新闻或公告全文。数据库锁定测试确认写入失败不会损坏旧记录。
- `confirmed`：前端新增独立公告验证与人工纠错面板；新闻事件请求使用请求序号和当前事件门禁，纠错响应使用事件 ID 门禁。1456px/760px 验收完全匹配、同日候选、无匹配、旧缓存、不可用、已有纠错、保存错误和长标题，无页面级横向溢出或控制台错误。
- `confirmed`：新鲜门禁通过 Rust contracts 4 项、桌面 215 项且 1 项显式性能测试 ignored、更新核心 11 项、全部 Node 契约、13 个 Vitest 文件 38 项、Vite 正式构建、384 项文件登记、437 个文本文件编码扫描、rustfmt、架构和 diff 检查。
- `confirmed`：用户明确要求本阶段例外生成 Windows x64 EXE 用于先行验收；只生成主程序和更新助手，没有安装包或 ZIP。主程序 SHA-256 为 `6004706F463B2DFCDAD6749BBC3498C2EFF8FCAAC1FF0C70454D64FCEC5CD57A`，更新助手 SHA-256 为 `6AE7DC93FAA270E2421029D9DADC77A824D3A9D56592F431EB7940DDCA79C2B5`；主程序 1.8 秒存活启动烟测通过。没有执行 Git 提交。
- `confirmed`：用户纠正最终产品基准：必须以来源任务 `019f59b1-db6e-78f2-9b0f-9c46e36657f1` 的完整功能、信息展示和整体风格为验收目标，用全新代码独立实现；重点包括信息总览首屏、顶部情绪/大盘/统计实时带和约 50 个内容不重复的独立菜单页，并加入自动刷新、用户自定义和 AI 分析。当前 14 菜单版本只是阶段基线，项目总体继续保持未完成。

## 2026-08-26 全局实时行情带与最大化应用壳阶段

- `confirmed`：Tauri 桌面壳默认最大化并保持可还原、可缩放；业务代码没有直接调用 Windows 专属 API。顶部新增全局共享市场脉冲，统一展示三大核心指数、九因子情绪、上涨/下跌、涨停/跌停、两市成交、数据状态和更新时间。
- `confirmed`：前端进程内单例 store 并发读取四条既有 IPC，同一时刻只有一个刷新 Promise；交易时段 5 秒、休市 30 秒、窗口隐藏时暂停，失败保留 last-good 并标记旧值。信息总览只订阅共享 store，不再重复请求指数、宽度与成交。
- `confirmed`：参考功能总账已登记 14 个一级菜单和信息总览恰好 50 个独立工作区；每个工作区记录独立内容契约、来源、刷新策略、当前映射、缺口和优先级。完整首屏、50 工作区运行时、用户布局偏好和服务端事件/SSE 总线仍是后续缺口，项目总体保持 `active`。
- `confirmed`：新鲜门禁通过全部 Node 架构/功能契约、14 个 Vitest 文件 41 项、Vite 正式构建、391 项文件登记、444 个项目文本文件编码扫描、Rust 格式、Rust desktop 215 项通过且 1 项显式性能测试 ignored、更新核心 11 项和 doc tests；`git diff --check` 通过。
- `confirmed`：按用户本轮验收要求仅生成 Windows x64 主程序与更新助手 EXE，不生成安装包或 ZIP。主程序 SHA-256 为 `72BABBBC2AF644CB870F9402BAAD94EDD85F870B67700348D101C43AB51D421C`，更新助手 SHA-256 为 `4389CACFB6B0673088A4039E89B7912A1B7170DF92638363CD7D9B11C6C3B083`；交付主程序 1,800 ms 存活启动烟测和更新成功/回滚烟测通过，历史交付物未覆盖。
- `observed`：当前终端 `PATH` 未注册 Cargo，但工具链实际存在于用户 `.cargo/bin`；本阶段使用 Cargo 绝对路径完成格式、测试和 release 构建，没有修改系统环境。
- `confirmed`：本阶段没有修改、清理或还原两个参考目录，也没有执行 Git commit、push、merge 或 PR。

## 2026-08-26 信息总览 50 工作区运行骨架阶段

- `confirmed`：信息总览已建立恰好 50 个独立 TypeScript 定义文件，对应参考总账 01–50；每项拥有唯一 ID、名称、业务问题、摘要、来源、刷新策略、布局、当前工程映射和证据缺口。50 项分为竞价与盘中、板块与题材、涨跌停生态、资金与席位、排名与统计、资讯与研究、盘后复盘和量价筛选八个业务家族。
- `confirmed`：新增 50 席证据矩阵、全文搜索、家族筛选、成熟度图例和 `workspace` URL 查询状态；无效查询回退盘中异动，只渲染当前工作区摘要。Hub 不调用 IPC、不创建计时器、不增加数据库表或缓存，不以静态入口冒充真实数据完成。
- `confirmed`：1456×900 与 760×900 本地页面验收均无页面级横向溢出；首项盘中异动、第 50 项龙虎榜、龙虎榜全文搜索的 3 个关联结果、量价筛选的 5 项结果和无匹配状态均通过，控制台无 warning/error。
- `confirmed`：新鲜门禁通过全部 Node 架构/功能契约、15 个 Vitest 文件 45 项、Vite 正式构建、451 项文件登记、504 个文本文件 UTF-8/乱码扫描、Rust 格式、Rust desktop 215 项通过且 1 项显式性能测试 ignored、更新核心 11 项及 doc tests；`git diff --check` 通过。
- `confirmed`：50 项运行入口已经可见，但其 `implemented / partial / missing` 仍以真实业务能力为准；下一阶段按 P0 优先级把摘要逐个替换为独立数据组件，项目总体继续保持 `active`。
- `confirmed`：本阶段没有生成安装包、ZIP 或 EXE，没有修改、清理或还原参考目录，也没有执行 Git commit、push、merge 或 PR。

## 2026-08-26 涨停、炸板、跌停共享事实生态阶段

- `confirmed`：信息总览的涨停板、炸板、跌停板已分别接入独立懒加载页面；三页共享唯一 `load_market_limit_ecology` IPC 和同一事实快照，支持代码/名称/行业搜索、个股钻取、交易时段 5 秒与休市 30 秒自动刷新、页面隐藏暂停和同刻请求复用，未复制三套请求或表格逻辑。
- `confirmed`：后端只读取东方财富公开涨停池、炸板池、跌停池直接字段；三类请求走统一网络客户端串行限流，东财主机请求间隔至少 1 秒，并使用 5 秒两级缓存、请求去重、独立熔断和 `stale-if-error`。炸板只接受炸板池事实，不以最高价推断；空值保持缺失，不写永久业务库，不生成交易建议。
- `confirmed`：三页在真实本地页面均具备独立 URL、标题、搜索框、刷新入口和证据状态；760×900 同源响应式夹具中三页的 `clientWidth/scrollWidth` 均为 `760/760`，没有页面级横向溢出。真实当前页控制台无 warning/error，临时夹具随后删除。
- `confirmed`：全量门禁通过根级 Node 契约链和前端 18 个 Vitest 文件 53 项、Vite 生产构建、14 菜单与 481 项文件登记、575 个文本文件 UTF-8/乱码扫描、rustfmt、Rust 跨层契约 6 项、桌面 220 项且 1 项显式性能测试 ignored、更新核心 11 项及全部 doc tests；项目 `git diff --check` 通过。根测试脚本已纳入涨跌停结构契约，后续不会只靠手动测试。
- `observed`：本执行环境未对三个东方财富公网端点进行真实响应抽样；当前解析和状态逻辑只通过合成夹具及跨层测试验证。三个工作区继续保持 `partial`，不可称为多源确认或完整板块集中/扩散分析，后续需在允许联网的环境低频抽样校准字段。
- `confirmed`：本阶段没有生成或重建 EXE、安装包、便携包或 ZIP，没有修改、清理或还原参考目录，也没有执行 Git commit、push、merge 或 PR。项目总体继续保持 `active`；后续 P0 顺序为板块精选、板块涨停、强度风口、人气榜、个股异动、异动提醒、热点解读和真实分钟异动事件流。

## 2026-08-26 板块精选四轨阶段

- `confirmed`：信息总览第 06“板块精选”已接入独立懒加载工作区，并发复用既有 `load_market_fund_flow` 与共享 `load_market_limit_ecology`；没有新增后端命令、重复板块请求、数据库表或常驻任务。两份证据分别保留 last-good，同刻只允许一个刷新 Promise，交易时段 5 秒、休市 30 秒，页面隐藏暂停。
- `confirmed`：东方财富板块事实契约在原三层资金字段上增加可选涨跌幅、成交额、上涨家数、下跌家数和领涨股，旧缓存继续可读。前端只在上涨/下跌家数有效且合计大于零时计算广度；涨停成员只按来源行业名称与板块名称完全匹配，成交额和主力净额并列展示且不互相替代，缺失值保持 `null/--`。
- `confirmed`：四轨页面支持板块代码/名称搜索、覆盖数审计、稳定排序和涨停成员个股钻取。1456px 页面级 `clientWidth/scrollWidth` 为 `1456/1456`；760px 为 `760/760`，明细表只在自身容器内由 446px 滚动到 980px，控制台无 warning/error，临时合成视觉夹具随后删除。
- `confirmed`：清理夹具后的全量门禁通过 19 个 Vitest 文件 59 项、全部根级 Node 契约、Vite 生产构建、14 菜单、487 项文件登记、583 个项目文本文件 UTF-8/乱码扫描、rustfmt、Rust 跨层契约 7 项、桌面 220 项且 1 项显式性能测试 ignored、更新核心 11 项和全部 doc tests；项目 `git diff --check` 通过。
- `observed`：本执行环境尚未对东方财富板块新增字段与涨跌停公网端点进行低频真实响应抽样，当前解析由合成夹具和跨层测试验证；板块与涨停仍各为单一公开来源，行业完全匹配不等于完整板块扩散率，因此工作区继续保持 `partial`。
- `confirmed`：本阶段没有生成或重建 EXE、安装包、便携包或 ZIP，没有修改参考项目，也没有执行 Git commit、push、merge 或 PR。项目总体继续保持 `active`；下一项按 P0 完成度审计推进板块涨停。

## 2026-08-26 板块涨停梯队阶段

- `confirmed`：信息总览第 13“板块涨停”已接入独立懒加载工作区，与板块精选共用中性 `marketSectorEcology` 单例运行时，并发复用既有 `load_market_fund_flow` 与 `load_market_limit_ecology`；没有新增网络源、Rust command、数据库表、依赖或常驻任务。
- `confirmed`：纯 presenter 只聚合严格涨停池成员；板块来源可用时行业名称必须完全匹配，行业缺失或未匹配成员进入独立未归类审计区。板块来源缺失时可按非空行业原值降级分组，但明确标记板块证据不可用；不做模糊归因或伪扩散率。
- `confirmed`：页面展示板块梯队、严格涨停数、最高连板、最早封板、封单合计与覆盖数、方向性样本及成员价格/涨跌/成交/换手/封板时间；`上涨家数 + 下跌家数` 只称方向性样本，不称完整板块成员总数。成员支持个股观察钻取，A 股红涨绿跌。
- `confirmed`：1456px 页面级 `clientWidth/scrollWidth` 为 `1456/1456`；760px 为 `760/760`，成员表只在自身容器内由 445px 滚动到 900px。点击“智云科技”进入 `/a-shares?symbol=300185` 的“个股观察”，浏览器 warning/error 为 0；临时同源视觉夹具随后删除。
- `confirmed`：清理夹具后的新鲜门禁通过全部根级 Node 契约、20 个 Vitest 文件 65 项、Vite 生产构建、14 菜单、492 项文件登记、590 个文本文件编码扫描、rustfmt、Rust 跨层契约与桌面 220 项（1 项显式性能测试 ignored）、更新核心 11 项及 doc tests；`git diff --check` 通过。
- `observed`：本执行环境仍未对东方财富板块新增字段和严格涨停公网端点做低频真实响应抽样；当前板块与涨停各为单一公开来源，也不具备概念板块多重归属和跨时段分钟轨迹，因此工作区保持 `partial`。
- `confirmed`：本阶段没有生成 EXE、安装包、便携包或 ZIP，没有修改参考项目，也没有执行 Git commit、push、merge 或 PR。项目总体继续保持 `active`；下一项按 P0 顺序推进“强度风口”。

## 2026-08-26 强度风口透明三轨阶段

- `confirmed`：信息总览第 33“强度风口”已接入独立懒加载工作区，继续复用中性 `marketSectorEcology`、`presentSectorSelection(...)` 和既有板块行情/严格涨停快照；没有新增网络源、Rust command、数据库表、依赖或计时器。东方财富请求仍由既有限流链独占，页面不直接调用 IPC。
- `confirmed`：纯 presenter 先在完整板块横截面计算涨幅、有效上涨广度和严格涨停成员绝对数量三条竞赛序位，再执行搜索；排序依次使用三轨完整性、最差序位、序位合计、涨幅和板块代码，不生成不透明综合分。缺失字段保持空值，搜索不会改变全市场名次。
- `confirmed`：四象限使用有效上涨广度中位数和正严格涨停成员数中位数；零涨停进入低扩散侧，来源缺失或无正样本时不生成象限。页面明确禁止把方向性样本当成完整成员总数，不展示虚假扩散率；来源领涨股只显示名称，行业完全匹配的严格涨停成员才允许进入个股观察。
- `confirmed`：1456px 验收页面 `clientWidth/scrollWidth` 为 `1441/1441`，760px 为 `745/745`；窄屏领涨成员表只在自身容器由 673px 滚动到 820px，严格成员带由 339px 滚动到 466px。搜索“人形机器人”仍保留全市场 `#2/#4/#2` 序位，点击“算力先锋”输出代码 `300001`，浏览器 warning/error 为 0；临时视觉夹具和页签随后删除。
- `confirmed`：新鲜全量门禁通过全部根级 Node 契约、21 个 Vitest 文件 71 项、Vite 生产构建、14 菜单、497 项文件登记、597 个项目文本文件编码扫描、rustfmt、Rust contracts 7 项、桌面 220 项且 1 项显式性能测试 ignored、更新核心 11 项和全部 doc tests；项目构建仍会报告既有 `MarketHotspotPanel.svelte` 静态/动态导入提示和 Rust 未使用代码警告，本阶段没有新增对应警告。
- `confirmed`：本阶段没有生成或重建 EXE、安装包、便携包或 ZIP，没有修改、清理或还原参考目录，也没有执行 Git commit、push、merge 或 PR。项目总体保持 `active`；下一项按 P0 顺序推进人气榜、个股异动、异动提醒、热点解读和真实分钟异动事件流。

## 2026-08-26 人气榜透明三轨阶段

- `confirmed`：信息总览第 19“人气榜”已接入独立懒加载工作区，复刻参考页的综合人气榜、人气构成分布、上榜资讯依据三块信息结构；使用全新 TypeScript/Svelte 实现，没有复制参考源码。“七大人气榜”继续保持独立未实现状态，没有与本页混合。
- `confirmed`：榜单样本严格限定为同花顺热点快照中的合法六位代码股票；三轨分别是涨跌幅绝对值、成交额、东方财富 7×24 快讯原文明示代码的去重事件数。使用标准竞赛序位，并按轨道完整度、最差序位、序位合计、涨跌幅绝对值和股票代码稳定排序；不生成 0–100 黑箱人气分，不宣称官方或全市场完整人气。
- `confirmed`：五等分构成按综合顺序映射为前 20%、20–40%、40–60%、60–80%、后 20%，每只股票只进入一个区间并支持真实成员下钻。资讯依据只展示综合榜前十股票关联的真实快讯，同一事件去重，多股票关联并列；题材标签不会冒充新闻。
- `confirmed`：新增 `marketAttention` 单例运行时，并发复用既有 `load_market_hotspots` 和 `load_breaking_news_alerts`；两个证据信封分别保留 last-good，同刻只允许一个刷新 Promise，交易时段 5 秒、休市 30 秒、窗口隐藏暂停、无订阅者停止。没有新增网络源、Rust command、数据库表、依赖或常驻后台任务。
- `confirmed`：1456px 浏览器验收页面 `clientWidth/scrollWidth` 为 `1441/1441`，760px 为 `745/745`；窄屏榜单局部容器为 `689/780`，实际横向滚动 `0→91`。五区间下钻、搜索“数据中心”保留原综合名次、股票钻取、长标题、部分缺失、缓存数据和全不可用状态通过，浏览器 warning/error 为 0；临时视觉夹具和页签随后删除。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、22 个 Vitest 文件 77 项、Vite 生产构建、14 菜单、505 项文件登记、605 个项目文本文件 UTF-8/乱码扫描、rustfmt、Rust contracts 7 项、桌面 220 项且 1 项显式性能测试 ignored、更新核心 11 项及全部 doc tests；项目 `git diff --check` 通过。
- `observed`：首次把 Vitest 与 Rust 冷编译、Vite 构建并行执行时，动态懒加载测试因 20 秒环境超时失败；无并行争用时相同测试稳定约 11.5–11.8 秒并连续通过，完整根测试链随后通过，因此未放宽测试门槛或修改产品代码。构建仍保留既有 `MarketHotspotPanel.svelte` 静态/动态导入提示和 Rust 未使用代码警告，本阶段没有新增对应警告。
- `confirmed`：本阶段没有生成或重建 EXE、安装包、便携包或 ZIP，没有修改、清理或还原参考目录，也没有执行 Git commit、push、merge 或 PR。项目总体保持 `active`；下一项按 P0 顺序推进个股异动、异动提醒、热点解读和真实分钟异动事件流。

## 2026-08-26 个股异动全市场横截面阶段

- `confirmed`：信息总览第 41“个股异动”已接入独立懒加载工作区，复刻参考页的“振幅-涨幅异动矩阵”“个股异动榜”“个股异动解释线索”三块结构；页面同时提供六项覆盖摘要、代码/名称/触发标签搜索、手动刷新、A 股红涨绿跌、股票钻取、快讯原始来源和双证据状态。全部 TypeScript/Svelte/Rust 代码为当前工程新实现，没有复制参考源码。
- `confirmed`：后端单次请求东方财富沪深京 A 股横截面，只读取价格、涨跌幅、成交额、振幅、换手、代码、名称、高低开收等直接字段；保留空值、数组/对象 `diff` 兼容和去重。矩阵阈值为振幅不低于 4%；异动榜按振幅不低于 5%、开盘缺口绝对值不低于 2%、涨跌幅绝对值不低于 3% 三项触发，按触发项数、最大标准化强度、成交额和代码透明排序，先统计完整命中数再限制矩阵 60 条、榜单 200 条。
- `confirmed`：横截面使用 4 秒进程内缓存、统一东财一秒串行闸门、全局并发限制、请求去重、独立熔断和 `stale-if-error`，不写数据库或永久网络缓存，也不把约五千条完整横截面传给 UI。前端 `marketMovements` 单例按行情 5 秒、快讯最多 30 秒双频刷新，同刻复用一个 Promise，两个来源分别保留 last-good，窗口隐藏或无订阅者时停止计时器，未使用 `setInterval`。
- `confirmed`：资讯解释只接受“异动、涨停、跌停、放量、停牌、复牌”认可信号，并且必须通过快讯 `explicitSymbols` 明示代码命中异动榜股票；重复多股票事件合并，题材词、标题猜测和新闻窗口不可用不会伪造关联。快讯仅称同刻解释线索，不宣称与行情存在已确认因果关系。
- `confirmed`：1456×900 验收页面级 `clientWidth/scrollWidth` 为 `1441/1441`，760×900 为 `745/745`；窄屏矩阵局部纵向容器为 `1350/520`，榜单横向容器为 `900/681`，线索纵向容器为 `1090/480`。搜索“高振幅”后保留 `#1/#2/#4...` 原始序位，股票钻取输出 `300100`；ready、partial、stale、unavailable、真实零线索、80 字长标题和来源入口均通过，浏览器 warning/error 为 0，临时视觉夹具和页签随后删除。
- `confirmed`：清理夹具并格式化后的新鲜门禁通过根级 Node 架构/功能链、23 个 Vitest 文件 83 项、Vite 生产构建、14 菜单、519 项文件登记、619 个项目文本文件 UTF-8/乱码扫描和 rustfmt；完整 Rust 工作区中桌面 229 项通过且 1 项显式性能测试 ignored，更新核心 11 项、跨层契约和 doc tests 通过。构建仍保留既有热点组件静态/动态导入提示，Rust 仍保留既有未使用代码警告，本阶段没有新增对应失败。
- `observed`：本执行环境没有对东方财富全市场横截面做低频真实公网响应抽样；当前来源解析、阈值、状态和缓存逻辑由合成夹具及跨层测试验证。单一公开行情来源、缺少交易所时间戳、缺少真实分钟增量事件流和多源交叉确认，因此工作区保持 `partial`，不能宣称完整实时事件因果链。
- `confirmed`：本阶段没有生成或重建 EXE、安装包、便携包或 ZIP，没有修改、清理或还原参考目录，也没有执行 Git commit、push、merge 或 PR。项目总体继续保持 `active`；下一项按 P0 顺序推进第 39“异动提醒”，并继续为热点解读和真实分钟异动事件流铺设共享事件边界。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-26-stock-movements-design.md`、`docs/superpowers/plans/2026-08-26-stock-movements.md`、`tests/features/market-movements-contract.test.mjs`。

## 2026-08-26 异动提醒分层事件收件箱阶段

- `confirmed`：信息总览第 39“异动提醒”已接入独立懒加载工作区，复刻参考页的“高优先级提醒”“异动提醒收件箱”“提醒关联股票”三块信息结构；支持六项摘要、全部/未读/高优先级/已处理/已忽略筛选、全文搜索、刷新、已读/确认/忽略动作和个股观察钻取。全部 Rust、TypeScript 与 Svelte 代码为当前工程新实现，没有复制参考源码。
- `confirmed`：页面复用第 41“个股异动”的唯一 `marketMovements` 单例，不新增行情或快讯请求、刷新循环、数据库行情快照或常驻任务。行情提醒以北京时间交易日和股票代码形成稳定 ID，快讯提醒以来源事件 ID 形成稳定 ID；快讯仅消费已校验的明示代码和认可异动信号，不推断利好、利空或已确认因果。
- `confirmed`：新增永久用户动作表只保存 `event_id`、`action`、`updated_at`，动作固定为 `read`、`acknowledged`、`ignored`；重复动作按主键 upsert，不保存标题、行情、价格或快讯正文。IPC 最多读取 300 个合法事件 ID，SQLite 操作使用阻塞线程隔离；锁定写入测试确认失败时不会损坏已有状态。
- `confirmed`：用户动作 store 支持 ID 去重、同一集合请求复用、过期响应隔离、乐观更新和保存失败回滚；搜索与筛选发生在完整排序之后，保留原始优先序号。高频实时事件只驻内存，自动更新与缓存清理不会覆盖永久用户动作。
- `confirmed`：1456×900 完整夹具页面级宽度为 `1456/1456`，760×900 为 `760/760`；窄屏收件箱和关联股票仅在自身容器滚动。正式入口清理夹具后再次验证 URL、三块结构和 `760/760` 页面宽度，临时夹具文件及引用均已删除。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、25 个 Vitest 文件 90 项、Vite 生产构建、14 菜单、533 项文件登记、632 个项目文本文件 UTF-8/乱码扫描和 rustfmt；完整 Rust workspace 中桌面 235 项通过且 1 项显式性能测试 ignored，更新核心 11 项、跨层契约和 doc tests 通过。构建仍保留既有热点组件静态/动态导入提示和 Rust 未使用代码警告，本阶段没有新增对应失败。
- `observed`：当前收件箱仍基于五秒全市场横截面和最多三十秒快讯窗口，不具备交易所分钟增量事件流、多源交叉确认或 AI 因果判断，因此工作区保持 `partial`，不能宣称交易级毫秒推送或完整事件历史。
- `confirmed`：本阶段没有生成或重建 EXE、安装包、便携包或 ZIP，没有修改、清理或还原参考目录，也没有执行 Git commit、push、merge或 PR。参考主目录当前 clean；参考工作树保留原有未提交改动并保持只读。项目总体继续保持 `active`；下一项按 P0 顺序推进第 43“热点解读”，随后建设真实分钟增量异动事件流。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-26-movement-alerts-design.md`、`docs/superpowers/plans/2026-08-26-movement-alerts.md`、`tests/features/movement-alerts-contract.test.mjs`。

## 2026-08-26 热点解读四段证据链阶段

- `confirmed`：信息总览第 43“热点解读”已接入独立懒加载工作区，复刻参考页的“热点原始资讯”“热点题材归因”“行情一致性验证”“热点证据链”四块结构；页面提供六项覆盖摘要、全文搜索、共享刷新、原始来源、股票钻取、局部滚动和双来源状态。全部 TypeScript 与 Svelte 代码为当前工程新实现，没有复制参考源码。
- `confirmed`：页面复用既有 `marketAttention` 单例，同时取得真实快讯和热点股票快照；没有新增网络来源、Rust command、数据库表、依赖、缓存或刷新计时器。连接只允许“快讯明示六位代码 → 同代码热点股票 → 来源非空题材 → 直接行情字段”，不从标题、摘要、股票名称或原因文本推断题材。
- `confirmed`：纯 presenter 按事件 ID 去重，完整链优先、时间倒序、事件 ID 稳定收口；搜索发生在完整排序后并保留原始序号。完整链最多 30 条、题材最多 24 个、行情股票最多 60 只；涨跌幅、换手率和成交额缺失时保持空值，不以零填充，不推断利好、利空或已确认因果。
- `confirmed`：1456×900 完整夹具页面级宽度为 `1456/1456`，展示 3 条有效链、4 个来源题材和 3 只股票，未关联传闻被排除；760×900 页面级宽度为 `760/760`，行情表与四段证据轨仅在自身容器滚动。搜索“机器人”保留原始 `#3`，部分链显示“待补行情”，股票钻取返回 `300001`。临时夹具随后删除，正式入口为空态和双状态面板再次通过。
- `confirmed`：修复根路由结构契约中写死的旧懒加载页清单后，新鲜门禁通过全部根级 Node 契约、26 个 Vitest 文件 95 项、Vite 生产构建、14 菜单、540 项文件登记、639 个项目文本文件 UTF-8/乱码扫描和 rustfmt；完整 Rust workspace 中桌面 235 项通过且 1 项显式性能测试 ignored，更新核心 11 项、跨层契约和 doc tests 通过。构建只保留既有热点组件静态/动态导入提示和 Rust 未使用代码警告。
- `observed`：当前行情字段来自热点股票同刻快照，不是事件前后分钟收益窗口；快讯与热点题材仍各为单一公开来源，没有公告交叉验证、多源语义核验或 AI 因果判断，因此工作区保持 `partial`。
- `confirmed`：本阶段没有生成或重建 EXE、安装包、便携包或 ZIP，没有修改、清理或还原参考目录，也没有执行 Git commit、push、merge 或 PR。参考主目录当前 clean；参考工作树保留 82 条原有已跟踪改动并保持只读。项目总体继续保持 `active`；下一阶段建设真实分钟增量异动事件流，并继续按完成度审计推进其余独立工作区。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-26-hotspot-interpretation-design.md`、`docs/superpowers/plans/2026-08-26-hotspot-interpretation.md`、`tests/features/hotspot-interpretation-contract.test.mjs`。

## 2026-08-27 异动统计大全阶段

- `confirmed`：信息总览第 30“异动统计大全”已接入独立懒加载工作区，复用唯一 `marketMovements` 事件流，不新增行情请求、网络源、数据库表或计时器。
- `confirmed`：新增独立类型、纯 presenter、Vitest 和 Svelte 页面，展示方向分布、事件类型、北京时间分钟桶、事件明细审计、搜索、刷新和行情证据状态；搜索发生在完整事件排序后，保留原始排名，最多展示 100 条明细。
- `confirmed`：工作区定义状态从 `missing` 更新为 `partial`，明确跨重启历史、交易所时间戳和多源确认缺口；参考对照账本已同步，双文件登记库新增 5 个文件。
- `confirmed`：本阶段根级 Node 契约、前端 28 个 Vitest 文件 99 项、Vite 构建、架构/文件登记、Rust 格式与事件流定向测试、UTF-8/乱码扫描和 `git diff --check` 均通过；Rust 保留既有弃用/未使用代码警告。
- `confirmed`：本地预览继续运行于 `http://127.0.0.1:1420/`；参考项目未执行写操作，未生成安装包、EXE 或 ZIP，未执行 Git commit/push/merge/PR；项目总体保持 `active`。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`tests/features/movement-statistics-contract.test.mjs`、`apps/desktop/src/feature/market-overview/movement-statistics-presenter.ts`。

## 2026-08-27 真实事件流阶段验证

- `confirmed`：盘中异动事件流已完成跨层接线。Rust 进程级累加器只比较相邻成功横截面，首帧建立基线；快速涨跌、涨跌幅阈值穿越和振幅阈值穿越按分钟去重，单帧最多 100 条、内存最多保留 300 条，日期变化清空窗口；缓存命中和失败回退不生成事件。
- `confirmed`：第 01“盘中异动”已拆为独立懒加载工作区，包含时间线、关联资讯、板块扩散三块区域；前端复用唯一 `marketMovements` 运行时，行情约 5 秒、快讯/热点最多 30 秒，保持 last-good、隐藏暂停和无高频数据库写入。
- `confirmed`：修复首帧 `baselineReady` 对外语义、Svelte 组件 class 指令兼容和过期视觉契约；补齐双文件登记库。根级 Node 契约、前端 27 个 Vitest 文件 97 项、Vite 生产构建、Rust workspace 238 项通过，1 项显式性能测试 ignored；Rust 保留既有未使用代码/弃用 API 警告。
- `confirmed`：本地开发预览已在 `http://127.0.0.1:1420/` 启动，页面标题为“信息总览 - 一树-A股观测台”；当前工作区和参考项目边界保持不变，未生成 EXE/安装包/ZIP，未执行 Git commit/push/merge/PR。
- `observed`：事件时间仍是本机检测时间，单一公开来源且约 5 秒观测粒度；没有交易所逐笔时间戳、多源因果确认或跨重启事件历史，因此功能状态继续保持 `partial`，项目总体保持 `active`。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-26-market-movement-event-stream-design.md`、`docs/superpowers/plans/2026-08-26-market-movement-event-stream.md`、`tests/features/market-movement-event-stream-contract.test.mjs`。

## 2026-08-27 开盘啦阶段

- `confirmed`：第 42“开盘啦”已新增独立 `market-open-types.ts`、`market-open-presenter.ts`、`MarketOpenPanel.svelte`、Vitest 和 Node 契约；页面以七项检查单复用全局 `marketPulse` 与 `marketAttention` 共享快照，未新增网络请求、数据库表或计时器。
- `confirmed`：指数、市场宽度、成交、情绪和热点保留各自 `ready/partial/stale/missing/unavailable` 状态；竞价缺口与开盘冻结记录明确显示 `missing`，竞价缺口作为阻断项，不从盘中快照倒推，不补零或生成交易方向。
- `confirmed`：loader 与前端清单测试已同步 17 个独立懒加载面板；根级 Node 契约、Vitest 29 个文件 101 项、Vite 生产构建、架构/文件登记、Rust 格式检查和 `git diff --check` 通过。
- `observed`：竞价全市场字段、开盘检查冻结持久化、交易所时间戳和多源确认仍未接入，因此工作区保持 `partial`；本阶段没有生成安装包、EXE 或 ZIP，没有修改参考项目，也没有执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`tests/features/market-open-contract.test.mjs`、`apps/desktop/src/feature/market-overview/market-open-presenter.ts`。

## 2026-08-27 连板表现阶段

- `confirmed`：第 08“连板表现”已新增独立 `consecutive-limit-performance-types.ts`、`consecutive-limit-performance-presenter.ts`、`ConsecutiveLimitPerformancePanel.svelte`、Vitest 和 Node 契约；页面以高度金字塔、梯队明细、摘要和个股钻取复刻参考信息结构，代码为当前工程新实现。
- `confirmed`：页面复用唯一 `limitEcology` 涨停事实池，不新增网络源、IPC、数据库表、依赖或计时器；高度只读取来源 `consecutiveLimitCount` 原值，完整排序后搜索并保留原始排名，缺失字段保留在审计中且不补成层级。
- `confirmed`：工作区定义状态由 `missing` 更新为 `partial`，明确跨日连续涨停算法、复权、交易日历覆盖和多源确认缺口；双文件登记库与参考对照账本已同步。
- `confirmed`：新鲜验收通过全部根级 Node 契约、30 个 Vitest 文件 103 项、Vite 生产构建、14 菜单、561 项文件登记、1935 个项目文本文件 UTF-8/乱码扫描、Rust 格式检查、Vault 校验和 `git diff --check`；本地预览已打开连板表现页面，1280px 视口无页面级横向溢出且控制台无警告或错误。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- `observed`：当前仍只有单一公开涨停事实池，跨日历史与多源确认未接入，不能宣称完整连板历史覆盖或交易方向建议。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`tests/features/consecutive-limit-performance-contract.test.mjs`、`apps/desktop/src/feature/market-overview/consecutive-limit-performance-presenter.ts`。

## 2026-08-27 龙头晋级阶段

- `confirmed`：第 09“龙头晋级”已接入独立懒加载工作区，以全新 TypeScript/Svelte 代码复刻“龙头晋级漏斗”“晋级条件与阻断”“晋级失败信号”三段结构；新增独立类型、纯 presenter、Vitest、页面和 Node 架构契约。
- `confirmed`：页面只订阅唯一 `limitEcology` 事实池，不新增网络源、IPC、数据库表、依赖或刷新计时器。候选取合法严格涨停，确认要求来源至少 2 板且当前未开板，当前前排要求确认池内最高合法高度，失败只统计真实炸板；开板风险单列，不冒充失败。
- `confirmed`：七项闸门逐项保留通过、阻断或缺失；板块强度、新闻确认和跨日状态链固定缺失，不参与排序。完整排序后再搜索并保留原始排名，不生成黑箱龙头分、收益预测或交易指令。
- `confirmed`：新鲜验收通过全部根级 Node 契约、31 个 Vitest 文件 105 项、Vite 生产构建、14 菜单、568 项文件登记、1942 个项目文本文件编码扫描、Rust 格式检查、Vault 校验和 `git diff --check`。1456px 与 760px 页面级宽度分别为 `1456/1456`、`760/760`，窄屏闸门表只在自身容器滚动，控制台无警告或错误。
- `observed`：浏览器开发预览没有 Tauri 后端，事实池正确显示来源不可用且未填假数据；跨日状态链、板块强度与新闻同刻确认尚未接入，因此工作区保持 `partial`。
- `confirmed`：本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR；项目总体继续保持 `active`。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-leader-advancement-design.md`、`tests/features/leader-advancement-contract.test.mjs`、`apps/desktop/src/feature/market-overview/leader-advancement-presenter.ts`。

## 2026-08-27 竞价异动阶段

- `confirmed`：第 10“竞价异动”已接入独立懒加载工作区，新增 `auction-movements-types.ts`、`auction-movements-presenter.ts`、`AuctionMovementsPanel.svelte`、Presenter 测试和 Node 契约；页面复刻缺口分布、竞价异动矩阵、高开回落与低开修复三段信息结构，代码为全新实现。
- `confirmed`：Presenter 复用唯一 `marketMovements` 横截面事实池，使用来源昨收、开盘、当前价、开盘缺口和涨跌幅字段；绝对缺口阈值为 2%，按缺口绝对值、成交额和代码稳定排序，再执行搜索并保留原始排名。矩阵最多渲染 80 个有当前涨跌的点，摘要不截断，缺失当前涨跌的样本保留在审计中。
- `confirmed`：六类结果标签由纯函数确定性计算，来源 `ready` 时由于单一来源、窗口有界、缺少交易所竞价时间戳和委托队列降为 `partial`；不生成竞价方向、综合分或代理数据。页面继续沿用共享刷新、状态面板和个股钻取，不新增网络源、IPC、数据库表、依赖或定时器。
- `confirmed`：竞价异动 Node 契约、Presenter/loader 定向测试和 Vite 生产构建通过；本地预览已打开 `http://127.0.0.1:1420/?workspace=auction-movements`，开发预览无 Tauri 后端时显示来源不可用，控制台无警告或错误。双文件登记库与参考对照账本已同步，项目总体保持 `active`。
- `observed`：交易所竞价时间戳、委托队列、多源确认和竞价全量历史覆盖仍未接入，不能宣称完整竞价证据或交易方向建议。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-auction-movements-design.md`、`tests/features/auction-movements-contract.test.mjs`、`apps/desktop/src/feature/market-overview/auction-movements-presenter.ts`。

## 2026-08-27 竞价选股阶段

- `confirmed`：第 11“竞价选股”已接入独立懒加载工作区，新增 `auction-selection-types.ts`、`auction-selection-presenter.ts`、`AuctionSelectionPanel.svelte`、Presenter 测试和 Node 契约；页面复刻规则候选、待补证据、风险阻断和闸门审计结构，代码为全新实现。
- `confirmed`：Presenter 复用唯一 `marketMovements` 横截面，使用开盘缺口、当前涨跌、成交额、振幅和换手率五个直接字段。五项闸门阈值固定且公开，缺失字段保持 `missing`；完整排序后再搜索，候选最多 100 行、审计最多 200 行，原始排名保持不变。
- `confirmed`：页面继续沿用共享刷新、状态面板和个股钻取，不新增网络源、IPC、数据库表、依赖或定时器；来源 `ready` 由于单一有界横截面、缺少竞价时间戳、委托队列、量比和多源确认降为 `partial`，不生成综合分或交易建议。
- `confirmed`：竞价选股 Node 契约、Presenter/loader 定向测试和 Vite 生产构建通过；架构登记、参考对照矩阵和完成审计已同步，项目总体保持 `active`。预览目标为 `http://127.0.0.1:1420/?workspace=auction-selection`。
- `observed`：开发预览没有 Tauri 后端时事实池显示来源不可用，无法据此观察真实候选数量；交易所竞价全量证据和多源确认仍未接入。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-auction-selection-design.md`、`tests/features/auction-selection-contract.test.mjs`、`apps/desktop/src/feature/market-overview/auction-selection-presenter.ts`。

## 2026-08-27 板块赛道阶段

- `confirmed`：第 12“板块赛道”已接入独立懒加载工作区，新增类型、纯 Presenter、Vitest、运行内历史 store、Svelte 页面和 Node 契约；页面复刻赛道轮动带、涨幅与广度矩阵、赛道迁移明细三块结构，代码为全新实现。
- `confirmed`：页面复用唯一 `marketSectorEcology` 板块资金与涨停生态事实池。板块资金 `observedAt` 变化时保存一个真实运行内时点，重复时间去重，最多 12 个；最后订阅关闭后释放历史，不新增网络、IPC、数据库表、依赖、轮询或永久数据。
- `confirmed`：基准为最早运行内时点，当前为最新时点。新晋前排使用涨幅排名前十迁移；增强、稳定和走弱只使用涨幅、广度、主力净额、严格涨停数四条直接差值的多数规则；不足两个时点或两条可比较轨道时保持 `missing`，不生成综合分。
- `confirmed`：板块赛道 Node 契约、Presenter/loader 定向测试和 Vite 生产构建通过；双文件登记库、参考对照和完成审计已同步，项目总体保持 `active`。
- `observed`：运行内历史不能替代跨重启历史；板块与涨停仍为单一公开来源，严格涨停只按行业名称完全匹配，缺少交易所统一时间戳、多源确认和概念多重归属。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-sector-tracks-design.md`、`tests/features/sector-tracks-contract.test.mjs`、`apps/desktop/src/feature/market-overview/sector-tracks-presenter.ts`。

## 2026-08-27 竞价封单阶段

- `confirmed`：第 05“竞价封单”已接入独立懒加载工作区，新增类型、纯 Presenter、Vitest、Svelte 页面和 Node 契约；页面复刻竞价封板状态、封单金额证据和竞价字段审计三块结构，代码为全新实现。
- `confirmed`：页面只订阅唯一 `limitEcology`。严格涨停且开板次数为 0 为当前封板，开板次数大于 0 或缺失归入开板风险，真实炸板只使用来源 `brokenLimitUp`；封单金额直接读取 `sealAmount`，封单/成交额比只在两个来源值均为正数时计算。
- `confirmed`：六项字段审计把当前状态、开板次数和封单金额按来源标记可用或缺失；竞价/涨停价格、委托队列和撤单轨迹固定缺失，不通过最高价、涨跌幅或成交额推测，不生成综合分或交易建议。
- `confirmed`：竞价封单 Node 契约、Presenter/loader 定向测试和 Vite 生产构建通过；双文件登记库、参考对照与完成审计已同步，项目总体保持 `active`。
- `observed`：共享涨停生态只证明当前盘中状态，不能替代交易所 9:15–9:25 竞价委托证据；竞价价、涨停价、逐笔队列和撤单轨迹仍未接入。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-auction-seal-orders-design.md`、`tests/features/auction-seal-orders-contract.test.mjs`、`apps/desktop/src/feature/market-overview/auction-seal-orders-presenter.ts`。

## 2026-08-27 隔夜单/抢筹阶段

- `confirmed`：第 04“隔夜单/抢筹”已接入独立懒加载工作区，新增类型、纯 Presenter、Vitest、Svelte 页面和 Node 契约；页面以全新代码复刻高开缺口分布、抢筹观察榜和隔夜委托证据三块结构。
- `confirmed`：页面只订阅唯一 `marketMovements` 横截面，不新增网络、IPC、数据库、依赖或计时器。高开样本只读取来源 `openGapPct >= 1`，按当前涨跌与缺口偏差透明区分延续、承接、回落和缺失；完整排序后搜索并保留原始排名。
- `confirmed`：昨收、开盘和当前涨跌按来源审计；隔夜委托量、竞价撤单轨迹和竞价成交明细固定缺失，不以成交额、高开或现价代理，不生成抢筹强度分或交易建议。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、36 个 Vitest 文件 120 项、Vite 构建、14 菜单、604 项文件登记、1978 个文本文件编码扫描、Rust 格式、Vault 和差异检查。1456px/760px 页面级宽度分别为 `1456/1456`、`760/760`，两个大表只在自身容器滚动，控制台无警告或错误。
- `observed`：浏览器开发预览没有 Tauri 后端，横截面显示来源不可用且没有假数据；真实隔夜委托队列、竞价撤单与成交、交易所时间戳和多源确认仍是缺口，工作区保持 `partial`。
- `confirmed`：本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR；项目总体继续保持 `active`。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-overnight-orders-design.md`、`tests/features/overnight-orders-contract.test.mjs`、`apps/desktop/src/feature/market-overview/overnight-orders-presenter.ts`。

## 2026-08-27 七大人气榜阶段

- `confirmed`：第 20“七大人气榜”已接入独立懒加载工作区，新增类型、纯 Presenter、Vitest、Svelte 页面和 Node 契约；页面以全新代码复刻七大人气榜单、重复上榜矩阵和榜单口径说明三块结构。
- `confirmed`：页面只复用唯一 `marketMovements` 行情/热点/真实事件流与 `limitEcology` 涨停事实池，不新增网络、IPC、数据库、依赖或计时器。涨幅、成交、振幅、高开、封板、题材和异动分别使用直接字段排序、按代码去重并限制前 10 名；异动榜不使用振幅或资讯代理。
- `confirmed`：重复矩阵按上榜数、名次和、代码稳定排序，最多 60 行；搜索在完整排序后执行并保留原始行序。七项口径审计保持来源状态和覆盖限制，不生成跨榜综合指标、预测或交易建议。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、37 个 Vitest 文件 123 项、Vite 构建、14 菜单、611 项文件登记、1985 个文本文件编码扫描、Rust 格式、Vault 和差异检查。1456px/760px 页面级宽度分别为 `1456/1456`、`760/760`，七榜墙、矩阵和审计只在自身容器滚动，控制台无警告或错误。
- `observed`：浏览器开发预览没有 Tauri 后端，三份事实池显示来源不可用且没有假数据；官方全市场人气排名、热点/异动全覆盖、跨重启异动历史和多源确认仍是缺口，工作区保持 `partial`。
- `confirmed`：本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR；项目总体继续保持 `active`。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-seven-popularity-rankings-design.md`、`tests/features/seven-popularity-rankings-contract.test.mjs`、`apps/desktop/src/feature/market-overview/seven-popularity-rankings-presenter.ts`。

## 2026-08-27 百日新高阶段

- `confirmed`：第 21“百日新高”已接入独立懒加载工作区。Rust 新增合同、领域、SQLite 只读聚合、用例和 Tauri 命令；目标日按最近 30 日期的 80% 高覆盖规则选择，查询窗口固定为目标日加前 100 个统一日期。
- `confirmed`：只有 101 个统一日期均有合法正收盘的股票参与判定；参考高点只取目标日前 100 日最高收盘，当前收盘等于前高也计入，成交额缺失保持空值，完整历史中的零新高仍返回真实快照。
- `confirmed`：页面展示“100 日历史覆盖审计”“已验证新高清单”“未验证原因”，四类缺口互斥；支持稳定排序、搜索后原始排名、50 行分页、按需核验和个股钻取。无网络、无定时器、无数据库写入、无新依赖。
- `confirmed`：Rust 7 项定向测试、Presenter 3 项、懒加载器 2 项、Node 跨层与路由契约、Vite 生产构建及 623 项文件登记检查已通过。
- `observed`：外部交易日历交叉核验、复权口径和多源确认仍未接入，因此工作区保持 `partial`；本阶段未生成 EXE、安装包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-hundred-day-highs-design.md`、`tests/features/hundred-day-high-contract.test.mjs`、`apps/desktop/src-tauri/src/infrastructure/database/hundred_day_high.rs`。

## 2026-08-27 百日新高趋势阶段

- `confirmed`：第 22“百日新高趋势”已接入独立懒加载工作区。Rust 只读永久日线，将 100 日参考基线与其后 20 个统一交易日观察窗口分开统计，并通过 Tauri 阻塞线程加载。
- `confirmed`：趋势按真实收盘路径透明分类为突破延续、突破回踩、突破失效和未形成突破；回踩容差固定 3%，展示距离峰值和峰值相对基线溢价，不使用今日涨幅代理，不输出交易建议。
- `confirmed`：页面包含阶段分布、路径清单和证据边界，支持排序、搜索后原始排名、50 行分页、有效零突破快照和个股钻取；无网络、无定时器、无写库、无新依赖。
- `confirmed`：Rust 6 项定向测试、Presenter 3 项、Node 跨层与路由契约和 Vite 生产构建已通过。
- `observed`：外部交易日历、复权和多来源确认仍未接入，工作区保持 `partial`；本阶段未生成 EXE、安装包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-hundred-day-high-trends-design.md`、`tests/features/hundred-day-high-trends-contract.test.mjs`、`apps/desktop/src-tauri/src/infrastructure/database/hundred_day_high_trends.rs`。

## 2026-08-27 龙头梯队阶段

- `confirmed`：`leader-tiers` 已接入独立懒加载工作区。`limitEcology` 是唯一输入；前排、中军、跟随、风险四条泳道由严格涨停、炸板、连板高度和开板次数直接字段确定，角色仅代表同刻横截面，不代表跨日龙头结论。
- `confirmed`：缺失高度或开板次数的样本进入待补证据列表；完整排序后再搜索并保留原始排名。页面不新增 IPC、网络源、数据库表、依赖或计时器，来源 `ready` 仍因板块和跨日边界降为 `partial`。
- `confirmed`：已新增设计/计划、前端类型、纯 presenter、Presenter 测试、Svelte 页面和 Node 契约，并接入工作区懒加载与路由契约；本轮全部根级 Node 契约、40 个 Vitest 文件 133 项、Vite 生产构建、14 菜单、642 项文件登记、2016 个项目文本文件 UTF-8/乱码扫描、Rust workspace 251 项通过且 1 项既有性能测试按设计保持 ignored、rustfmt、Vault 校验和 `git diff --check` 均通过。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-leader-tiers-design.md`、`tests/features/leader-tiers-contract.test.mjs`、`apps/desktop/src/feature/market-overview/leader-tiers-presenter.ts`。

## 2026-08-27 涨停复盘啦阶段

- `confirmed`：第 28“涨停复盘啦”已接入独立懒加载工作区。页面只订阅共享 `limitEcology`，涨停、炸板、跌停分别消费对应来源池；每栏池内去重、稳定排序后再搜索并保留原始排名，缺失价格、成交、事件时间、连板高度、开板次数和行业字段保留在字段审计中。
- `confirmed`：次日开盘价、封板/开板延续、次日成交确认、板块扩散与交叉确认四项纪律固定为 `missing`，不从当日快照推断方向，不生成交易建议；来源 `ready` 因次日证据、盘后长期冻结、板块完整成员和多源确认缺口降为 `partial`，其他状态原样保留。
- `confirmed`：已新增设计/计划、前端类型、纯 presenter、Presenter 测试、Svelte 页面和 Node 契约，并接入工作区懒加载、路由契约、双文件登记、参考对照和完成审计；定向 Node 契约、Presenter/loader 测试和 Vite 生产构建通过。开发预览已打开 `http://127.0.0.1:1420/?workspace=limit-up-review`，无 Tauri 后端时显示真实来源不可用，不填充假行情。
- `confirmed`：本阶段全量门禁通过：全部根级 Node 契约、41 个 Vitest 文件 137 项、Vite 生产构建、14 菜单、649 项文件登记、2023 个项目文本文件 UTF-8/乱码扫描、Rust workspace 251 项通过且 1 项既有性能测试按设计保持 ignored、rustfmt、Vault 校验和 `git diff --check` 均通过。浏览器预览 `http://127.0.0.1:1420/?workspace=limit-up-review` 桌面宽度为 `1280/1280`，760px 窄屏为 `760/760`，三栏与次日纪律均渲染，控制台无警告或错误；预览标签已保留。来源缺失时显示真实 `unavailable`，不填充假行情。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-limit-up-review-design.md`、`tests/features/limit-up-review-contract.test.mjs`、`apps/desktop/src/feature/market-overview/limit-up-review-presenter.ts`。

## 2026-08-27 概念叠加阶段

- `confirmed`：第 26“概念叠加”已接入独立懒加载工作区。页面只订阅共享 `marketAttention.hotspots`，使用同花顺人工题材原值构建股票—题材矩阵、概念叠加榜和题材拥挤提示；不新增网络源、IPC、数据库表、依赖或刷新计时器，不从新闻文本推断标签。
- `confirmed`：每只股票题材去空白、去重，至少两个有效题材才进入叠加样本；矩阵最多 80 股 × 12 个高覆盖题材，榜单最多 100 行，组合最多 40 行。单股至少 4 个题材、同一完整组合至少 3 股、至少 4 只叠加样本且题材覆盖率不低于 50% 分别形成三类透明集中标签；标签不参与排序，不生成综合分或交易建议。
- `confirmed`：Presenter 使用与操作系统区域无关的稳定文本顺序，搜索在完整排序后执行并保留原始排名，摘要始终基于完整合法样本；来源 `ready` 因全市场概念归属、跨日版本、行业地域分类和多源确认缺口降为 `partial`，其他状态原样保留。
- `confirmed`：已新增设计/计划、类型、纯 Presenter、5 项 Presenter 测试、Svelte 页面和 Node 契约，并接入懒加载、路由、双文件登记、参考对照和完成审计；本阶段新鲜验收通过全部根级 Node 契约、42 个 Vitest 文件 142 项、Vite 生产构建、14 菜单、656 项文件登记、2030 个项目文本文件 UTF-8/乱码扫描、Rust workspace 251 项通过且 1 项既有性能测试按设计保持 ignored、rustfmt、Vault 校验和 `git diff --check`。浏览器预览在 1280px 与 760px 下页面级宽度分别为 `1280/1280`、`760/760`，三个页面区块均实际渲染，窄屏榜单只在自身容器滚动，控制台无警告或错误；无 Tauri 后端时显示真实 `unavailable` 空态。
- `confirmed`：本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-concept-overlap-design.md`、`tests/features/concept-overlap-contract.test.mjs`、`apps/desktop/src/feature/market-overview/concept-overlap-presenter.ts`。

## 2026-08-27 放量突破阶段

- `confirmed`：第 47“放量突破”已接入独立懒加载工作区。Rust 新增跨层合同、证据状态纯规则、SQLite 只读聚合、用例和 Tauri 命令；目标日从最近 30 日期中选择达到近期最大样本 80% 覆盖的最新日期，统一窗口固定为目标日加此前 60 个交易日期。
- `confirmed`：只有 61 日正收盘完整且目标日与前 5 日正成交量完整的股票参与判定；目标日收盘必须不低于前 60 日最高收盘，成交量必须不低于前 5 日均量的 1.80 倍。结果按量能倍数、突破幅度、成交额和代码稳定排序，最多 5000 行；有效零命中保留真实快照。
- `confirmed`：页面展示六类互斥覆盖审计和命中清单，支持搜索后原始排名、50 行分页、按需核验和个股钻取；不新增网络源、数据库表、写入、依赖或定时器。开发预览为 `http://127.0.0.1:1420/?workspace=volume-breakout`，无 Tauri 后端时显示真实 `unavailable` 空态。
- `confirmed`：新鲜验收通过全部根级 Node 契约、43 个 Vitest 文件 144 项、Vite 生产构建、Rust workspace 桌面 260 项通过且 1 项既有性能测试 ignored、更新核心 11 项、14 菜单、666 项文件登记、2045 个文本文件编码扫描、rustfmt、Vault 校验和 `git diff --check`。1280px 与 760px 页面根宽度无横向溢出，控制台无警告或错误。
- `observed`：外部交易日历、复权口径和多源确认仍未接入，因此工作区保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-volume-breakout-design.md`、`tests/features/volume-breakout-contract.test.mjs`、`apps/desktop/src-tauri/src/infrastructure/database/volume_breakout.rs`。

## 2026-08-27 突破前高阶段

- `confirmed`：第 48“突破前高”已接入独立懒加载工作区。Rust 新增跨层合同、证据状态纯规则、SQLite 只读扫描、用例和 Tauri 命令；共享 `market_review_window.rs` 只负责最近 30 日 80% 高覆盖目标日、统一日期和原始 OHLCV 装载，第 47“放量突破”已迁移复用且规则不变。
- `confirmed`：突破前高规则独立要求目标日收盘严格高于此前 20 个统一交易日最高价，目标日成交量不低于前 5 日均量的 1.20 倍；相等不命中。六类审计互斥，价格、历史或量能缺失不使用代理值，有效零命中保留真实快照。
- `confirmed`：页面展示四项突破强度、六类覆盖审计、命中清单、搜索、成交额缺失值始终置后的双向排序、原始排名、50 行分页、按需核验和个股钻取；不新增网络、数据库表、写入、依赖或定时器。
- `confirmed`：新鲜验收通过全部根级 Node 契约、45 个 Vitest 文件 152 项、Vite 生产构建、Rust workspace 306 项且 1 项显式性能测试按设计保持 ignored、14 个菜单、692 项文件登记、2074 个文本文件编码扫描、rustfmt 和 `git diff --check`。1280px/760px 页面宽度均无横向溢出，真实 `unavailable` 空态、四项摘要、四项强度、六类审计和控制台已实测；窄屏核验按钮换行已通过红绿契约修复。
- `observed`：外部交易日历、复权口径和多源确认仍未接入，因此工作区保持 `partial`；开发预览没有 Tauri 后端时显示来源不可用，不填充假股票。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-prior-high-breakout-design.md`、`tests/features/prior-high-breakout-contract.test.mjs`、`apps/desktop/src-tauri/src/infrastructure/database/prior_high_breakout.rs`、`apps/desktop/src/feature/market-overview/PriorHighBreakoutPanel.svelte`。

## 2026-08-28 低位放量阶段

- `confirmed`：第 49“低位放量”已接入独立懒加载工作区。Rust 复用只负责高覆盖目标日、统一日期和原始 OHLCV 的共享读取器，并新增独立合同、领域状态、SQLite 只读规则、用例和 Tauri 命令；统一窗口含目标日共 120 个日期。
- `confirmed`：区间低点取 120 日最低 `low`，区间高点取最高 `high`；平坦区间固定 50.00%。普通区间位置与当前量/前 5 日均量通过有界十进制定点有理数执行两位 `ROUND_HALF_UP`，只有位置不高于 30.00% 且量能不低于 1.50 倍才命中；半点上下相邻值、非有限值和溢出均有测试，不使用 ULP 容差近似。六类审计互斥，价格、区间或量能缺失不使用代理值，有效零命中保留真实快照。
- `confirmed`：页面展示四项位置与量能仪表、六类覆盖审计、观察清单、搜索后原始排名、双向成交额缺失置后、50 行分页、按需核验和个股钻取；搜索无结果、完整证据下的真实零命中和证据缺失分别呈现。四项聚合在稳定排序后、5000 行截断前使用两位定点整数求和，结果与输入顺序无关；IPC 读取既有永久库时不创建目录。明确“低位”仅表示历史价格位置，不等于低估、见底或买入建议。不新增网络、数据库表、写入、依赖或计时器。
- `confirmed`：新鲜验收通过低位放量定向 Rust 测试连续 5 轮、每轮 12 项，全部根级 Node 契约、46 个 Vitest 文件 159 项、Vite 3663 模块生产构建、Rust workspace 318 项且 1 项显式性能测试按设计保持 ignored、14 个菜单、704 项文件登记、2086 个项目文本文件编码扫描、Vault Markdown 严格 UTF-8 解码、Vault 官方验证器和 rustfmt。浏览器 1280px/760px 页面无横向溢出，工作区宽度分别为 1021px/483px；真实 `unavailable` 空态、四项摘要、四项仪表、六类审计、局部表格滚动规则和控制台均已实测。
- `observed`：外部交易日历、复权口径、多源确认和跨日位置轨迹仍未接入，因此工作区保持 `partial`；开发预览没有 Tauri 后端时不填充假股票。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-27-low-position-volume-design.md`、`tests/features/low-position-volume-contract.test.mjs`、`apps/desktop/src-tauri/src/infrastructure/database/low_position_volume.rs`、`apps/desktop/src/feature/market-overview/LowPositionVolumePanel.svelte`。

## 2026-08-28 龙虎榜阶段

- `confirmed`：第 50“龙虎榜”已接入东方财富日级详情、同交易日买卖席位、15 分钟两级缓存、完整事务并发去重和独立熔断。空详情或来源失败只有在同键 last-good 存在时返回 `stale`，否则保持 `unavailable`；持久缓存提升到内存时继承原始剩余 TTL，不因重启延长有效期。
- `confirmed`：来源层已按请求、解析、网络装配和测试拆分；用例层增加可注入来源边界，并将 440 行混合文件拆为 189 行生产编排与 253 行独立行为测试。职责库同步为 719 项，未新增依赖、数据库表、后台轮询或首屏预取。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、47 个 Vitest 文件 165 项、Vite 3666 模块生产构建、Rust workspace 桌面端 313 项通过且 1 项显式性能测试按设计保持 ignored、更新核心 11 项、14 个菜单、719 项文件登记、2101 个项目文本文件 UTF-8/乱码扫描和 rustfmt。定向验证包含来源 9 项、用例 7 项和缓存 3 项。
- `confirmed`：浏览器预览 `http://127.0.0.1:1420/?workspace=dragon-tiger-list` 在 1280px 与 760px 下页面级宽度分别为 `1280/1280`、`760/760`，龙虎榜工作区宽度分别为 `1021/1021`、`483/483`；桌面双栏在窄屏切为单栏，控制台无警告或错误。无 Tauri 后端时显示真实 `unavailable`、0 个股票按钮，不填充假股票；席位表局部横向滚动由页面 CSS 与跨层契约覆盖，网页空态下没有真实席位行可供滚动实测。
- `obsolete`：龙虎榜阶段时第 17“游资追踪”和第 18“游资动向”都只有可复用席位合同；第 17 已在后续游资追踪阶段完成独立跨日聚合与页面，第 18 仍为最高优先级缺口。
- `confirmed`：本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/plans/2026-08-28-dragon-tiger-list.md`、`tests/features/dragon-tiger-list-contract.test.mjs`、`apps/desktop/src-tauri/src/application/use_cases/load_dragon_tiger.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_dragon_tiger_tests.rs`、`apps/desktop/src/feature/market-overview/DragonTigerPanel.svelte`。

## 2026-08-28 游资追踪阶段

- `confirmed`：第 17“游资追踪”已接入独立懒加载跨层工作区。来源按中国日期读取 14 个自然日的东方财富历史详情、买入席位和卖出席位，三请求串行经过统一网络层；详情上限 2000 行、两侧席位各 5000 行，不新增依赖、永久业务表、后台轮询或首屏预取。
- `confirmed`：席位记录必须匹配同日同股合法详情；名称只去首尾空白，相似名称不合并，完全相同跨报表记录合并为 `mixed`。聚合最多展示 300 席、每席 60 条最近操作，完整摘要在截断前计算，丢弃、未匹配和截断均可审计。
- `confirmed`：用例使用 15 分钟两级缓存、完整三请求事务去重和独立 `eastmoney_hot_money_breaker`。新鲜结果始终为 `partial`；来源失败只有同窗口 last-good 存在时返回 `stale`，否则为 `unavailable`，熔断打开时不执行来源事务。
- `confirmed`：页面包含席位净额追踪榜、七字段双向排序、席位/股票/代码/原因搜索、完整集合摘要、选择回退、跨日股票轨迹、覆盖仪表、字段审计、手动核验和个股钻取。无 Tauri 后端时摘要、仪表与审计显示 `--`，没有假席位或假股票。
- `confirmed`：全量门禁通过 48 个 Vitest 文件 171 项、Vite 3669 模块生产构建、Rust 桌面端 324 项且 1 项显式性能测试按设计 ignored、更新核心 11 项、14 菜单、734 项文件登记和 rustfmt。浏览器 1280px/760px 页面级宽度分别为 `1280/1280`、`760/760`，工作区宽度分别为 `1021/1021`、`483/483`，窄屏切单栏且控制台无警告错误。
- `observed`：当前仍只有东方财富单一公开来源，窗口只有 14 个自然日，没有交易所或第二来源确认、权威席位身份映射和长期归档，因此工作区保持 `partial`。第 18“游资动向”可复用当前快照，但独立股票方向聚合和页面仍未完成。
- `confirmed`：本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git commit/push/merge/PR；预览保留在 `http://127.0.0.1:1420/?workspace=hot-money-tracking`。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-28-hot-money-tracking-design.md`、`tests/features/hot-money-tracking-contract.test.mjs`、`apps/desktop/src-tauri/src/application/use_cases/load_hot_money_tracking.rs`、`apps/desktop/src/feature/market-overview/HotMoneyTrackingPanel.svelte`。

## 2026-08-28 个股分时完整曲线修复

- `confirmed`：个股观察时间线此前只显示一个点，根因是本地盘中归档按轮询快照保存，而当天常只有一条收盘快照；前端没有缺失曲线，后端确实没有分钟序列。
- `confirmed`：新增腾讯个股分钟真实来源，读取当日 09:30–11:30、13:00–15:00 分钟行，使用腾讯报价的昨收计算真实涨跌字段；过滤接口附带的 15:06–15:30 非交易参考行，不插入模拟点。
- `confirmed`：时间线服务在当前交易日归档不足 5 点时读取分钟来源，并按观测时间与本地快照合并；本地较新的采样优先保留。历史日期仍不调用实时接口，来源失败继续明确保持单点/不可用状态。
- `confirmed`：后端全量 `1773 passed, 1 skipped`，前端 `807 passed`，Ruff、Vite 构建、乱码扫描和差异检查通过；便携 EXE 烟测第二次通过，14/14 菜单门禁、窗口 44ms、API 2212ms，退出后无观测台残留。
- `confirmed`：最新 EXE `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `1A7A37E393F4AFC45C36B1ED07FAF0BE379D39C7C2F4E788FD69E269D93BD967`；烟测首次公司研究超时为外部接口波动，第二次重试通过。未关闭或控制通达信。
- 来源：`apps/api/src/qibao_api/a_shares/stock_timeline.py`、`apps/api/src/qibao_api/gongbu/tencent_overview.py`、`apps/api/src/qibao_api/main.py`、`apps/api/tests/a_shares/test_stock_timeline.py`、`apps/api/tests/gongbu/test_tencent_overview.py`、`scripts/build-portable.ps1`、`scripts/run-portable-smoke.ps1`。

## 2026-08-28 AI+题材阶段

- `confirmed`：信息总览第 03“AI+题材”已接入独立 Rust/Tauri/Svelte 冻结证据工作区。题材只使用同花顺热点人工原值，快讯只按东方财富原文明示六位代码连接，不从文本、股票名称或市场信号推断题材；稳定排序后使用 SHA-256 冻结身份。
- `confirmed`：冻结证据缓存 30 分钟；AI 只由用户显式触发，要求题材完整证据 ID 集精确匹配，使用严格 JSON、引用白名单、反方证据和交易指令拦截，并复用单并发、零重试、12 秒超时、独立熔断与 7 天合格结果缓存。密钥不进入正文、缓存身份或前端。
- `confirmed`：页面包含 AI 题材证据卡、新闻到股票证据链和题材行情验证；离页、换题材和旧快照的迟到结果不会覆盖当前状态。无桌面后端时显示真实 `unavailable`、零题材和零股票，不生成示例数据，也不自动调用 AI。
- `confirmed`：新鲜验收通过 55 个 Vitest 文件 200 项、Vite 3684 模块构建、AI 主题合同 2 项、桌面定向 11 项、Rust workspace 桌面 336 项且 1 项既有性能测试 ignored、更新核心 11 项、14 菜单、771 项文件登记、2153 个项目文本文件编码扫描、rustfmt、架构检查和项目差异检查。
- `confirmed`：浏览器 1280px 页面/工作区宽度为 `1280/1280`、`1023/1023`，760px 为 `760/760`、`485/485`；证据卡和状态区在窄屏切为单列，三块结构与真实空态均渲染，控制台无警告或错误。预览保留在 `http://127.0.0.1:1420/?workspace=ai-themes`。
- `observed`：多来源题材确认、事件前后分钟行情窗口和跨日冻结版本仍是明确缺口，因此工作区保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/plans/2026-08-28-ai-themes.md`、`tests/features/ai-themes-contract.test.mjs`、`apps/desktop/src-tauri/src/domain/market/ai_themes.rs`、`apps/desktop/src/feature/market-overview/AiThemesPanel.svelte`、`docs/verification/feature-completion-audit.md`。

## 2026-08-28 情绪周期阶段

- `confirmed`：信息总览第 16“情绪周期”已接入独立懒加载工作区。页面只订阅共享 `marketPulse` 与 `limitEcology`，总阶段直接读取后端九因子 `band`；分项按透明 70/30 阈值归入支持、压力、中性和缺口，上涨占比与严格封板率仅做同刻核验，不写回九因子总分。
- `confirmed`：页面包含五阶段市场风格仪表、支持与压力证据、研究模式路由、九因子原始覆盖和三来源状态；总分缺失显示“证据不足”，陈旧来源不升级。无 Tauri 后端时实际渲染 9 个缺口因子与 3 个真实 `unavailable` 状态，不填充示例阶段、分数或行情。
- `confirmed`：本阶段不新增 Rust、IPC、网络来源、数据库、缓存、依赖或计时器，自动刷新与 last-good 完全复用两个共享 store。职责库为 778 项，`SentimentCyclePanel` 为独立生产分包。
- `confirmed`：新鲜门禁通过 56 个 Vitest 文件 207 项、Vite 3687 模块生产构建、Rust workspace 桌面端 336 项且 1 项既有性能测试 ignored、更新核心 11 项、14 个菜单、778 项文件登记、2160 个项目文本文件编码扫描、rustfmt、项目差异检查、Vault 官方验证器和 66 份长期记忆 Markdown 严格 UTF-8/乱码扫描。
- `confirmed`：浏览器 1280px 页面/工作区宽度为 `1280/1280`、`1023/1023`，760px 为 `760/760`、`485/485`；窄屏双栏切单栏，因子表只在自身容器形成 `860/446` 局部滚动，页面根节点无横向溢出，控制台无 warning/error。预览保留在 `http://127.0.0.1:1420/?workspace=sentiment-cycle`。
- `observed`：风险偏好、板块扩散、风格偏好和跨交易日周期轨迹仍未接入，因此工作区保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-28-sentiment-cycle-design.md`、`docs/superpowers/plans/2026-08-28-sentiment-cycle.md`、`tests/features/sentiment-cycle-contract.test.mjs`、`apps/desktop/src/feature/market-overview/sentiment-cycle-presenter.ts`、`apps/desktop/src/feature/market-overview/SentimentCyclePanel.svelte`。

## 2026-08-28 题材挖掘阶段

- `confirmed`：信息总览第 25“题材挖掘”已接入独立懒加载工作区。页面只订阅共享 `marketMovements` 的热点、快讯和异动三份证据；题材只取同花顺人工标签原值，东方财富快讯与运行内异动只按六位股票代码完全匹配，不从新闻文本、股票名称或异动方向生成题材。
- `confirmed`：页面包含题材共现网络、扩散题材排行、题材股票共振、七项去重/坏行/未连接审计和三来源状态。阶段固定为标签样本、资讯连接、异动连接和多链共现；搜索保留原始名次，非有限行情保持缺失。并列文本顺序已通过先失败后通过的回归测试改为跨运行时稳定比较；证据规范化与连接文件 168 行，视图 Presenter 243 行，符合约 300 行职责拆分阈值。
- `confirmed`：本阶段不新增 Rust、IPC、网络来源、数据库、缓存、依赖、AI 或刷新计时器。新鲜门禁通过全部根级 Node 契约、57 个 Vitest 文件 212 项、Vite 3691 模块构建、Rust 桌面端 336 项且 1 项既有性能测试 ignored、更新核心 11 项、14 菜单、786 项文件登记、2168 个项目文本文件编码扫描、rustfmt 和项目差异检查。
- `confirmed`：浏览器 1280px 页面/工作区宽度为 `1280/1280`、`1021/1021`，760px 为 `760/760`、`483/483`；窄屏分析区和状态区切为单栏，两个宽表只在自身容器形成 `760/446` 局部滚动。三块参考结构、七项审计和三个真实 `unavailable` 来源状态实际渲染，全新页面控制台无警告或错误。预览保留在 `http://127.0.0.1:1420/?workspace=theme-mining`。
- `observed`：全市场概念归属、跨日扩散历史、第二新闻来源、事件前后行情窗口和因果判断证据仍未接入，因此工作区保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-28-theme-mining-design.md`、`docs/superpowers/plans/2026-08-28-theme-mining.md`、`tests/features/theme-mining-contract.test.mjs`、`apps/desktop/src/feature/market-overview/theme-mining-evidence.ts`、`apps/desktop/src/feature/market-overview/theme-mining-presenter.ts`、`apps/desktop/src/feature/market-overview/ThemeMiningPanel.svelte`。

### 2026-08-28 低位放量与龙虎榜只读审计

- `observed`：任务 `01a04683-fa33-7ae1-bcae-91b78a5f5cf7` 的低位放量复核确认十进制定点半入、溢出拒绝、无副作用路径、搜索空态和截断前聚合的前序问题已有实质修复；但当前 `finalize_rows` 在稳定排序前按 `HashMap` 派生顺序做浮点在线均值，导致 `average_volume_multiple` 最低位可能跨运行变化，定向集合出现 `11/12` 通过。该项在重新取得稳定定点聚合的完整证据前保持未闭环。
- `observed`：任务 `01a046c9-8106-7df0-b678-9968a34c2792` 的龙虎榜复核确认持久缓存剩余 TTL、非有限金额拒绝和 `500/100/20` 资源边界已通过；仍有两个 P2：重复金额元组提前 `continue` 可能漏掉后续合法行的涨跌幅/换手率补充，且 `load_dragon_tiger.execute` 尚未覆盖并发去重、空详情/HTTP/解析失败和熔断短路行为。
- `observed`：上述审计线程均为只读复核，没有修改源码、生成 EXE/安装包/ZIP 或执行项目 Git 写操作；相关计划中的旧“全量通过”数字不替代本日审计结果。
- 来源：`task:01a04683-fa33-7ae1-bcae-91b78a5f5cf7`、`task:01a046c9-8106-7df0-b678-9968a34c2792`、`docs/superpowers/plans/2026-08-27-low-position-volume.md`、`docs/superpowers/plans/2026-08-28-dragon-tiger-list.md`、对应设计文档与定向测试输出。

### 2026-08-28 昨涨停阶段

- `confirmed`：第 34“昨涨停”已接入独立跨层工作区。Rust 从永久日线选择最近三个统一高覆盖日期，按板块与明确 ST 口径冻结严格涨停基线；五类审计互斥，有效零严格涨停保留为真实快照。
- `confirmed`：前端复用唯一 `marketMovements` 共享横截面，只有反馈交易日和来源昨收同时匹配才连接今日开盘、现价、涨跌和成交额；日期错位、昨收不一致、缺失字段与待形成反馈分别保留。页面提供四档反馈、搜索、稳定原始排名、双向排序、50 行分页、双来源状态和个股钻取。
- `observed`：外部交易日历、复权、交易所逐笔时间戳和第二行情来源仍未接入，因此保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-28-previous-limit-ups.md`、`tests/features/previous-limit-ups-contract.test.mjs`、`apps/desktop/src-tauri/src/infrastructure/database/previous_limit_up.rs`、`apps/desktop/src/feature/market-overview/PreviousLimitUpsPanel.svelte`。

### 2026-08-28 首板梯队阶段

- `confirmed`：第 46“首板梯队”已接入独立懒加载工作区，并与第 45“连板梯队”共享一次永久日线扫描和一个按需 Store。首板严格要求目标日收盘涨停且上一交易日明确未涨停；首板与连板分别稳定排序、独立截断，真实零结果保持有效。
- `confirmed`：页面提供完整首板清单、四档成交分布、六类互斥判定审计、搜索、双向缺失置后排序、50 行分页、来源状态和个股钻取；不新增查询、网络、数据库表、依赖或计时器。
- `observed`：外部交易日历、复权、制度变更和封板时间证据仍未接入，因此保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-28-first-limit-tiers.md`、`tests/features/first-limit-tiers-contract.test.mjs`、`apps/desktop/src/feature/market-overview/limit-tier-store.ts`、`apps/desktop/src/feature/market-overview/FirstLimitTiersPanel.svelte`。

### 2026-08-28 问财选股阶段

- `confirmed`：第 38“问财选股”已接入独立懒加载本地规则组合器，只复用唯一 `marketMovements` 共享横截面，不新增网络源、Rust、IPC、数据库、缓存、依赖或刷新计时器。
- `confirmed`：涨跌幅、当前价、成交额、振幅、开盘缺口和换手率六类区间规则全部使用 AND 关系；通过、缺失和明确不满足分别进入 `candidate/pending/blocked`。页面提供规则校验与应用、可追溯结果、搜索后原始排名、双向缺失置后排序、50 行分页、六项字段审计、真实来源状态和个股钻取。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、65 个 Vitest 文件 245 项、Vite 3711 模块生产构建、Rust workspace 桌面端 346 项且 1 项既有性能测试 ignored、更新核心 11 项、14 个菜单、838 项文件登记、2220 个项目文本文件编码扫描、rustfmt 和项目差异检查。1280px 页面/工作区宽度为 `1280/1280`、`1023/1023`；760px 截图中工作区保持在主内容列，控制台无 warning/error。
- `observed`：当前只覆盖共享横截面最多 200 条有界异动样本，不冒充全市场；全市场服务端筛选、规则持久化、自然语言解释和第二行情来源仍是缺口，因此保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-28-query-selection-design.md`、`docs/superpowers/plans/2026-08-28-query-selection.md`、`tests/features/query-selection-contract.test.mjs`、`apps/desktop/src/feature/market-overview/query-selection-presenter.ts`、`apps/desktop/src/feature/market-overview/QuerySelectionPanel.svelte`、`docs/verification/feature-completion-audit.md`。

### 2026-08-28 投资日历阶段

- `confirmed`：第 32“投资日历”已接入独立懒加载事件账本，只复用 `marketMovements` 的共享快讯和热点证据，不新增网络源、Rust、IPC、数据库、缓存、依赖、首屏预取或计时器。信息总览现有 47 个独立页面，剩余个股详情、主力大单监控和非研产业库三个工作区。
- `confirmed`：事件必须具备完整身份、带明确时区的有效 ISO 时间和原文明示六位 A 股代码；统一换算上海日期，名称与人工题材只按精确代码连接。资讯时间固定为 `news_published_at`，官方事项日期保持缺失，不从文本推断或生成事件。
- `confirmed`：页面包含 A 股事件日历、当前事件详情和日期口径与来源，支持按日索引、搜索后原始排名、选择回退、原始来源、个股钻取、十项坏行/连接/截断审计和双来源状态；最多保留 200 条事件、每个日期组展示 50 条。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、66 个 Vitest 文件 250 项、Vite 3714 模块构建、Rust 桌面端 346 项且 1 项既有性能测试 ignored、更新核心 11 项、14 菜单、845 项文件登记、2227 个项目文本文件编码扫描、rustfmt 和项目差异检查。
- `confirmed`：浏览器 1280px 页面/工作区宽度为 `1280/1280`、`1023/1023`，760px 为 `760/760`、`485/485`；摘要分别为六列和三列，窄屏双状态区切单列，页面无横向溢出，控制台无警告或错误。普通网页预览没有 Tauri 后端，真实空态未填充假事件；预览保留在 `http://127.0.0.1:1420/?workspace=investment-calendar`。
- `obsolete`：当时尚无官方事项日期源；2026-08-29 已由限售解禁官方事项切片部分替代。第二资讯来源、其他官方事项和跨日事件归档仍是明确缺口，因此工作区保持 `partial`。
- 来源：`docs/superpowers/specs/2026-08-28-investment-calendar-design.md`、`docs/superpowers/plans/2026-08-28-investment-calendar.md`、`tests/features/investment-calendar-contract.test.mjs`、`apps/desktop/src/feature/market-overview/investment-calendar-presenter.ts`、`apps/desktop/src/feature/market-overview/InvestmentCalendarPanel.svelte`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 投资日历限售解禁官方事项阶段

- `confirmed`：第 32“投资日历”在既有资讯发布时间账本旁新增独立东方财富 `RPT_LIFT_STAGE` 限售解禁切片；窗口固定为中国当天至未来第 90 个自然日，单次最多 200 条，使用独立请求去重、熔断器、6 小时两级缓存和同前缀 8 个窗口容量，不新增轮询、首屏预取、数据库表或平台专属业务调用。
- `confirmed`：合法事项为 `partial`，来源确认空窗口为 `missing`，同窗口旧缓存回退为 `stale`，首次来源失败为 `unavailable`。`FREE_SHARES_NUM` 缺失时只回退同源 `FREE_SHARES`；资讯发布时间与官方事项日期不互相推断，缺失事项类型和数值保持为空，不生成演示事项或替代值。
- `confirmed`：真实来源烟测在 `2026-08-29` 至 `2026-11-27` 窗口返回 448 条，按上限取回 200 条；当前来源未返回 `LIMITED_STOCK_TYPE`，解析器按可选缺失处理，其余 248 条进入截断审计。新鲜门禁通过 99 个 Vitest 文件 404 项、Vite 3778 模块、Rust 桌面端 469 项且 1 项既有性能测试 ignored、updater-core 11 项、14 个菜单、1072 项登记、2458 个项目文本编码扫描、rustfmt、架构和项目差异检查。
- `confirmed`：1280px 与 526px 页面/面板宽度分别为 `1280/1280`、`1021/1021` 和 `526/526`、`250/250`；官方事项三块标题实际渲染，无面板溢出后代，控制台 warning/error 为 0。普通网页环境保持真实不可用，不展示伪造事项。
- `observed`：财报、分红、股东大会、第二官方事项来源和跨日资讯归档仍未接入，因此投资日历和产品总体保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-investment-calendar-official-events-design.md`、`docs/superpowers/plans/2026-08-29-investment-calendar-official-events.md`、`apps/desktop/src-tauri/src/application/use_cases/load_investment_calendar_official.rs`、`apps/desktop/src/feature/market-overview/InvestmentOfficialEvents.svelte`、`tests/features/investment-calendar-official-events-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-28 个股详情阶段

- `confirmed`：第 36“个股详情”已接入独立懒加载单股速览，只复用 `marketMovements` 的共享异动排行、热点和快讯，不新增网络源、Rust、IPC、数据库、缓存、依赖、首屏预取或计时器。信息总览现有 48 个独立页面，剩余主力大单监控和非研产业库两个工作区。
- `confirmed`：合法六位代码按共享排行原序去重；行情名称为空时才按同代码回退热点名称，非有限量价保持缺失。人工题材和新闻只按精确代码连接，新闻还要求完整身份与带时区有效时间；不从文本推断。收盘位置、涨跌方向和相对开盘只做透明事实派生。
- `confirmed`：页面包含个股实时档案、个股证据链和个股状态提醒，提供可搜索样本索引、八项档案、原始新闻来源、四类事实提醒、十二项审计、三来源状态和个股钻取；最多保留 200 个候选、单股展示 20 条新闻。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、67 个 Vitest 文件 256 项、Vite 3717 模块构建、Rust 桌面端 346 项且 1 项既有性能测试 ignored、更新核心 11 项、14 菜单、852 项文件登记、2234 个项目文本文件编码扫描、rustfmt 和项目差异检查。
- `confirmed`：浏览器 1280px 页面/工作区为 `1280/1280`、`1023/1023`，档案与证据/提醒均为双栏；760px 为 `760/760`、`485/485`，档案、证据/提醒和三状态区均为单栏。页面无横向溢出，三块标题、三个真实 `unavailable` 状态和严格空态实际渲染，控制台无 warning/error；预览保留在 `http://127.0.0.1:1420/?workspace=stock-details`。
- `observed`：当前样本不是完整股票目录，第二行情/资讯来源和深度历史仍是缺口，因此保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-28-stock-details-design.md`、`docs/superpowers/plans/2026-08-28-stock-details.md`、`tests/features/stock-details-contract.test.mjs`、`apps/desktop/src/feature/market-overview/stock-details-presenter.ts`、`apps/desktop/src/feature/market-overview/StockDetailsPanel.svelte`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 主力大单监控与非研产业库阶段

- `confirmed`：第 37“主力大单监控”已接入独立跨层工作区。全市场双向榜只使用东方财富 `f62/f66/f72` 主力、超大单和大单净额，具备 5 秒缓存、请求去重、独立熔断、last-good 和可见性刷新边界；单股钻取使用真实 120 日资金分层，缺失值不补零、不使用成交额或涨跌幅代理。
- `confirmed`：第 44“非研产业库”已接入独立懒加载工作区，只复用共享热点与快讯 Store。关系严格限定为快讯明示代码连接同代码热点股票及人工题材，不从文本猜题材，不推断产业上下游、受益程度、评级或未来走势。
- `observed`：主力大单仍缺逐笔成交、大单阈值、主动买卖方向和第二来源；产业库仍缺权威产业分类、关系版本、第二来源和长期归档，因此两页继续保持 `partial`。
- 来源：`apps/desktop/src/feature/market-overview/LargeOrderMonitorPanel.svelte`、`apps/desktop/src/feature/market-overview/IndustryLibraryPanel.svelte`、`tests/features/large-order-monitor-contract.test.mjs`、`tests/features/industry-library-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 信息总览 50/50 阶段完成

- `confirmed`：信息总览当前有 50 个定义、50 个唯一入口和 50 个独立懒加载页面；较早“47/48 个页面、剩余三个/两个”的记录已被当前 50/50 状态取代，但保留为历史阶段证据。
- `confirmed`：新鲜全量验证通过全部根级 Node 契约、70 个 Vitest 文件 269 项、Vite 3724 模块生产构建、Rust 桌面端 351 项且 1 项既有性能测试 ignored、更新核心 11 项、14 个菜单、872 项文件登记、2254 个项目文本文件编码扫描、rustfmt 和差异检查。
- `confirmed`：浏览器 DOM 为 50 个入口和 50 个唯一名称；第 37 与第 44 在 1280px/760px 下无页面级横向溢出，宽表仅局部滚动，控制台无错误。开发预览为 `http://127.0.0.1:1420/?workspace=industry-library`。
- `observed`：50/50 证明页面和路由覆盖完成，不证明所有来源、多源交叉确认、跨日归档和交易所级证据已完成；整个产品继续按功能矩阵中的真实 `partial` 缺口推进。本阶段未生成发布包、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/architecture/reference-parity-ledger.md`、`docs/verification/feature-completion-audit.md`、`apps/desktop/src/feature/market-overview/overview-workspace-panel-loaders.ts`。

### 2026-08-29 市场异动事件桥阶段

- `confirmed`：市场异动新增 `yishu://market-movements` Tauri 事件桥。Rust 成功形成真实快照后广播完整证据信封，前端单例 Store 按订阅生命周期监听；事件传输失败不会影响权威 HTTP 命令。
- `confirmed`：事件与 HTTP 回包共用 `sessionDate + latestCursor + observedAt` 单调版本门禁，拒绝迟到、相同版本、空载荷和非法游标覆盖 last-good；无 Tauri 事件运行时继续使用既有 5 秒/30 秒 HTTP 回退，隐藏页面暂停。
- `confirmed`：本阶段无新增网络源、数据库表、依赖或常驻任务；聚焦事件门禁 3 项、事件桥合同、Rust workspace 351 通过/1 个既有性能测试 ignored、Vite 3729 模块构建和格式检查均通过。
- `observed`：当前事件由按需 HTTP 快照触发，尚未接入交易所级 SSE/逐笔行情，因此实时刷新仍为 `partial`。本阶段未生成发布包、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-29-market-movement-event-bridge-design.md`、`docs/superpowers/plans/2026-08-29-market-movement-event-bridge.md`、`apps/desktop/src/feature/market-overview/market-movements-events.ts`、`apps/desktop/src/feature/market-overview/market-movements-store.ts`、`apps/desktop/src-tauri/src/commands/market_movements.rs`、`tests/features/market-movement-event-bridge-contract.test.mjs`。

### 2026-08-29 直接 URL 预览路由修复

- `confirmed`：修复 SPA 直接访问路径默认显示信息总览的问题。`resolveRoutePath` 负责 pathname 尾斜杠归一化和未知路径回退，App 初始加载及浏览器前进/后退同步 URL；`/today-decision` 直接访问已显示今日研判。
- `confirmed`：新增 `routes.test.ts`，路由测试与 3729 模块生产构建通过；直接 URL 在 1280px/760px 均无页面横向溢出，控制台无 warning/error。
- 来源：`apps/desktop/src/app/routes.ts`、`apps/desktop/src/app/App.svelte`、`apps/desktop/src/app/routes.test.ts`。

### 2026-08-29 今日研判三阶段工作台阶段

- `confirmed`：今日研判页面已改为共享 `marketPulse` 与 `marketAttention` 驱动，两个 Store 并行刷新；页面移除独立 `load_today_decision`、重复 `load_market_sentiment` 与 `setTimeout` 串接，仅保留 `freeze_current_decision` 永久账本写入。
- `confirmed`：新增纯 TypeScript Presenter 与独立工作台组件，按上海时间输出盘前、盘中、盘后三阶段职责，最多三条支持证据、六条风险/反方证据、六路来源状态和可冻结快照；非有限数值保持缺失，陈旧来源不升级，不生成买卖建议或 AI 结论。
- `confirmed`：本轮门禁通过 71 个 Vitest 文件 274 项、Rust workspace 351 通过/1 个既有性能测试 ignored、Vite 3727 模块构建、879 项文件登记、2261 个项目文本编码扫描、架构检查、rustfmt 与差异检查；市场情绪合同已同步共享 Store 边界。
- `observed`：统一服务端阶段快照、交易日历与跨日回放、候选建议链、盘后归因和 AI 解释仍未接入，工作台保持 `partial`。本阶段未生成发布包、未修改参考项目、未执行 Git 写操作。预览保留在 `http://127.0.0.1:1420/today-decision`。
- 来源：`docs/superpowers/specs/2026-08-29-today-decision-workbench-design.md`、`docs/superpowers/plans/2026-08-29-today-decision-workbench.md`、`tests/features/today-decision-workbench-contract.test.mjs`、`tests/features/market-sentiment-contract.test.mjs`、`apps/desktop/src/feature/today-decision/today-decision-workbench-presenter.ts`、`apps/desktop/src/feature/today-decision/TodayDecisionWorkbench.svelte`、`apps/desktop/src/feature/today-decision/TodayDecisionPage.svelte`。

### 2026-08-29 统一市场脉冲总线阶段

- `confirmed`：新增 `MarketPulseSnapshot` 跨层合同和 `load_market_pulse` 聚合命令，并行读取指数、市场宽度、两市成交和九因子四路既有证据；子信封来源、缺失字段、缓存和状态保持独立，聚合层只输出透明状态、覆盖和警告。
- `confirmed`：新增 `yishu://market-pulse` 事件桥；前端 `marketPulse` 首个订阅者建立一次监听、最后一个释放，刷新只调用一次聚合 IPC；事件与回包共用外层 `observedAt` 单调门禁，聚合失败时各子证据保留 last-good 并降为 `stale`。
- `confirmed`：定向门禁通过：事件 2 项、Store 6 项、Rust 聚合状态 2 项、Node 合同和 TypeScript 类型检查；本阶段未新增依赖、网络源、数据库表或常驻任务，未生成 EXE/安装包/ZIP，未修改参考工程，未执行 Git 写操作。
- `observed`：统一聚合已减少顶部实时带的 IPC/观测时刻分裂，但交易所级 SSE、逐笔行情、后台统一实时总线和其余专题 Store 的缓存帧收敛仍未完成，实时刷新与全产品继续保持 `partial`。
- 来源：`docs/superpowers/plans/2026-08-29-market-pulse-bus.md`、`crates/contracts/src/market_pulse.rs`、`apps/desktop/src-tauri/src/commands/market_pulse.rs`、`apps/desktop/src/app/market-pulse-events.ts`、`apps/desktop/src/app/market-pulse-store.ts`、`tests/features/market-pulse-bus-contract.test.mjs`。

### 2026-08-29 核心指数双来源交叉确认阶段

- `confirmed`：新增东方财富核心指数适配器和腾讯主源—东方财富副源纯对齐函数；五个固定指数按六位代码合并，原始值、涨跌幅、差异和缺失字段均独立保留。
- `confirmed`：新增 `MarketIndexConfirmation` 跨层合同和顶部核验条带；状态区分 `confirmed/divergent/primary_only/secondary_only/unavailable`，冲突不平均、不覆盖，缺失不补零。
- `confirmed`：核心指数两源请求并行执行，各自使用 30 秒两级缓存、请求去重和独立熔断；主行情卡继续展示腾讯主值，副源只作为可追溯核验。
- `observed`：当前副源仍是单一东方财富公开端点，缺来源原生交易所时间戳、同刻冻结和交易所级 SSE/逐笔行情，因此顶部与整个产品仍按 `partial` 口径推进。本阶段未生成发布产物，未修改参考工程，未执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-29-index-cross-confirmation.md`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_index.rs`、`apps/desktop/src-tauri/src/domain/market/index_cross_confirmation.rs`、`apps/desktop/src-tauri/src/commands/core_menu.rs`、`apps/desktop/src/app/GlobalMarketPulse.svelte`、`tests/features/index-cross-confirmation-contract.test.mjs`。

### 2026-08-29 共享关注度快照投影阶段

- `confirmed`：`marketMovements` 现在是异动、热点和快讯的唯一刷新与事件来源；`marketAttention` 只投影热点/快讯/加载状态，避免今日研判、开盘检查、人气榜等页面重复发起同一组 IPC/网络请求。
- `confirmed`：关注度 Store 支持注入源 Store 的单元测试；首个订阅者建立一次源订阅，最后一个释放，刷新直接委托源 Store；不新增数据源、数据库、依赖或计时器，真实 `stale/unavailable` 状态保持不变。
- `observed`：交易所级逐笔时间戳、第二资讯来源和跨重启历史仍未接入，实时能力与相关页面继续保持 `partial`。本阶段不生成发布产物、不修改参考工程、不执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-29-shared-attention-snapshot.md`、`apps/desktop/src/feature/market-overview/market-attention-store.ts`、`apps/desktop/src/feature/market-overview/market-attention-store.test.ts`、`tests/features/market-attention-store-contract.test.mjs`。

### 2026-08-29 用户偏好持久化阶段

- `confirmed`：`UserSettings` 现在统一保存刷新间隔、总览工作区顺序和折叠映射；TypeScript 设置网关与 Rust 配置命令都兼容旧配置缺字段，刷新秒数规范化为 5–300 秒，AI 密钥继续只保留系统凭据状态。
- `confirmed`：`marketPulse.setRefreshInterval` 已接入设置页和总览首屏，交易时段按用户秒数调度、休市至少 30 秒；共享 Store 仍按订阅生命周期运行，页面隐藏时停刷，不为 50 个工作区重复创建计时器。
- `confirmed`：信息总览新增当前工作区上移、下移和折叠/展开控制。顺序去重、未知 ID 丢弃并自动追加新工作区；桌面端原子写入统一用户配置，普通浏览器预览仅在 Tauri 不可用时使用 localStorage 回退。
- `observed`：默认标的统一接线、更多页面级布局偏好和交易所级实时源仍未闭环，整体继续保持 `partial`。本阶段未生成 EXE/安装包/ZIP，未修改参考工程，未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-29-user-preferences-design.md`、`docs/superpowers/plans/2026-08-29-user-preferences.md`、`apps/desktop/src/shared/settings/user-settings-types.ts`、`apps/desktop/src/feature/market-overview/OverviewWorkspaceHub.svelte`、`apps/desktop/src/app/market-pulse-store.ts`、`apps/desktop/src-tauri/src/commands/settings.rs`。

### 2026-08-29 共享刷新偏好总线阶段

- `confirmed`：新增 `apps/desktop/src/app/refresh-preferences.ts` 作为前端进程内刷新间隔唯一发布源，所有输入统一规范为 5–300 秒；设置页现有 `marketPulse.setRefreshInterval` 入口继续有效并写入该源。
- `confirmed`：顶部 `marketPulse`、全市场异动、板块生态、涨跌停生态和主力大单监控 Store 均订阅同一偏好源，交易时段使用用户秒数，休市至少 30 秒；异动的新闻/热点次级证据最短 30 秒。
- `confirmed`：偏好订阅只存在于 Store 有订阅者期间，停止时和定时器、可见性监听一起释放；未增加网络源、IPC、数据库表、第三方依赖或常驻任务。
- `confirmed`：新增共享偏好与调度 Vitest；全量根级 Node 合同、78 个 Vitest 文件 295 项、Vite 3733 模块构建、Rust workspace 360 项通过/1 项既有性能测试 ignored、910 项文件登记、2292 个文本编码扫描、rustfmt、差异检查和 Vault 校验均通过。干净浏览器标签页 `http://127.0.0.1:1420/market-overview?preview=latest` 实际渲染信息总览且控制台 error/warn 为 0。
- `observed`：交易所级 SSE、逐笔行情和多源同刻冻结仍未接入，整体实时能力继续保持 `partial`；本阶段未生成发布包、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-29-shared-refresh-preference-design.md`、`docs/superpowers/plans/2026-08-29-shared-refresh-preference.md`、`apps/desktop/src/app/refresh-preferences.ts`、`apps/desktop/src/app/refresh-preferences.test.ts`、`apps/desktop/src/app/refresh-preference-scheduling.test.ts`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 刷新生命周期与证据回退加固

- `confirmed`：`limitEcology` 失败刷新改用 `keepLastGood`，只降级状态和警告，保留旧数据、来源、观测时间、交易日、快照/血缘 ID 与缺失字段；新增独立 `limit-ecology-store.test.ts` 覆盖该合同。
- `confirmed`：顶部市场脉冲、全市场异动、板块生态、涨跌停生态和主力大单监控在隐藏文档首个订阅时不自动请求；隐藏期间偏好变化只更新内存间隔，恢复可见才触发自动刷新。顶部脉冲与主力大单真实生命周期测试已覆盖首刷抑制、恢复刷新、间隔变更和定时器清理。
- `confirmed`：主力大单页面及工作区定义显示“按用户设置”刷新口径，不再固定宣称盘中 5 秒。
- `confirmed`：定向 4 个 Vitest 文件 18 项与主力大单 Node 合同通过；未生成发布包，未修改只读参考工程，未执行 Git 写操作。
- 来源：`apps/desktop/src/feature/market-overview/limit-ecology-store.ts`、`apps/desktop/src/feature/market-overview/limit-ecology-store.test.ts`、`apps/desktop/src/app/market-pulse-store.ts`、`apps/desktop/src/app/market-pulse.test.ts`、`apps/desktop/src/feature/market-overview/large-order-monitor-store.ts`、`apps/desktop/src/feature/market-overview/large-order-monitor-store.test.ts`、`apps/desktop/src/feature/market-overview/LargeOrderMonitorPanel.svelte`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 异动事件跨重启缓存阶段

- `confirmed`：龙虎榜解析 9 项、用例 7 项、前端 79 文件 299 项和 Node 跨层合同均通过，未发现可复现的重复金额或缓存/熔断回归，因此没有重复修改龙虎榜生产逻辑。
- `confirmed`：异动事件累加器现在按上海交易日恢复归档窗口，最多 300 条；恢复后重新建立实时基线，错日事件、重复 ID 和超出容量的旧事件均被丢弃。
- `confirmed`：新增 `market_movement_event_archive`，复用用户缓存目录的 `network-cache.sqlite3`，每个交易日单键、7 天 TTL，只在游标前进时异步写入，不写永久业务库，也不增加网络请求或常驻轮询。
- `confirmed`：本阶段最终门禁通过根级 Node 合同、前端 79 个 Vitest 文件 299 项、Vite 3733 个模块生产构建、Rust workspace 367 项通过且 1 项既有性能测试 ignored、14 个菜单/912 项文件登记、2295 个文本文件编码扫描、rustfmt、`git diff --check` 和 Vault 校验（退出码 0）。
- `observed`：异动仍是约 5 秒客户端观测，不含交易所逐笔时间戳、第二来源或真实分钟级事件流；工作区和产品总体继续保持 `partial`。本阶段未生成发布产物，未修改参考项目，未执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-29-market-movement-history.md`、`apps/desktop/src-tauri/src/domain/market/market_movement_events.rs`、`apps/desktop/src-tauri/src/infrastructure/cache/market_movement_event_archive.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_market_movements.rs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 量化任务事件进度阶段

- `confirmed`：量化回测任务复用已有 `TaskSnapshot`，后端在任务状态变化后广播 `yishu://task-progress`；前端独立 `task-events.ts` 只转发当前任务，终态和离页会清理监听与计时器。
- `confirmed`：固定 250ms 轮询已移除，事件不可用时仅保留 2 秒低频 `get_task` 兜底；不新增依赖、网络源、数据库表或常驻任务，不改变回测结果和真实证据边界。
- `confirmed`：量化任务合同、TypeScript 类型检查、Rust 定向测试和 rustfmt 通过；新增共享文件已登记到文件注册表。
- `observed`：事件通道只改善任务进度传输，不等同于交易所级行情实时流；量化数据源与预测模型缺口仍保持 `partial`。本阶段未生成发布产物，未修改参考工程，未执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-29-quant-task-events.md`、`apps/desktop/src-tauri/src/commands/quant_tasks.rs`、`apps/desktop/src/feature/shared/task-events.ts`、`apps/desktop/src/feature/quant-analysis/QuantAnalysisPage.svelte`、`tests/features/quant-task-contract.test.mjs`。

### 2026-08-29 重要事件雷达共享生命周期阶段

- `confirmed`：`ImportantEventRadar.svelte` 只投影 `marketAttention.breakingNews`，保留三条重要事件、显式股票代码钻取、原始来源入口和真实来源状态；移除直接 `load_breaking_news_alerts` IPC。
- `confirmed`：组件不再维护 15 秒计时器或 `visibilitychange` 监听，快讯刷新、请求去重、用户刷新偏好、隐藏暂停和 last-good 回退统一由 `marketMovements` Store 负责，避免总览同时打开多个专题时重复请求。
- `confirmed`：新增 `market-attention-store-contract.test.mjs` 约束事件雷达必须复用共享 Store、禁止页面级 IPC/独立计时器；同步更新 YAML/Markdown 文件登记、参考复刻总账和功能完成审计。全量验证通过：根级合同、前端 79 文件 299 项、Rust workspace 367 通过/1 个既有性能测试 ignored、Vite 3734 模块、913 项登记、2297 个文本编码扫描、rustfmt 和 `git diff --check`。
- `observed`：事件仍来自客户端观测快照，交易所逐笔时间戳、第二资讯来源和真实分钟事件流未接入，实时能力及产品总体继续保持 `partial`；本阶段未生成发布包、未修改参考工程、未执行 Git 写操作。
- 来源：`apps/desktop/src/feature/market-overview/ImportantEventRadar.svelte`、`apps/desktop/src/feature/market-overview/market-attention-store.ts`、`tests/features/market-attention-store-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 板块资金动图共享时序阶段

- `confirmed`：第 40 个“板块资金动图”已从页面级 `load_market_fund_flow` 改为只订阅 `sectorTrackHistory`，刷新委托 `marketSectorEcology`；不再创建独立 IPC、计时器或可见性监听。
- `confirmed`：新增纯 Presenter 与类型文件，最多保留当前页面生命周期内 12 个真实观测点，按主力净额显示净流入/净流出/零轴/缺失、最近两点变化、金额排名和每板块轨迹；搜索与方向筛选在完整排序后执行。
- `confirmed`：Presenter 2 项单测、共享 Store 架构合同、旧资金合同和 Vite 生产构建通过；新增文件已登记到 YAML/Markdown 文件注册表和实施计划。
- `observed`：跨重启板块历史、交易所统一时间戳、多源确认和来源质量轨迹仍未接入，工作区及产品总体继续保持 `partial`。本阶段未生成发布产物，未修改参考工程，未执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-29-sector-fund-animation.md`、`apps/desktop/src/feature/market-overview/sector-fund-animation-types.ts`、`apps/desktop/src/feature/market-overview/sector-fund-animation-presenter.ts`、`apps/desktop/src/feature/market-overview/MarketFundFlowPanel.svelte`、`tests/features/sector-fund-animation-contract.test.mjs`。

### 2026-08-29 默认标的统一接线阶段

- `confirmed`：统一用户设置新增 `defaultSymbol`，Rust 与 TypeScript 兼容旧配置缺字段并规范为六位 A 股代码；无效值回退 `600519`，用户配置仍只写平台用户数据目录。
- `confirmed`：个股观察、公司研究和量化分析共用“合法 URL 参数 > 用户默认标的 > 兼容默认值”的初始化规则；显式 URL 不等待设置 IPC，不新增网络源、数据库表、计时器、依赖或平台专属调用。
- `confirmed`：股票代码前后缀规范化已下沉为共享纯函数；设置页新增默认代码输入，普通浏览器预览的 Tauri 缺失异常已归一化为中文状态，不再暴露英文内部错误。
- `confirmed`：新鲜门禁通过根级合同、82 个 Vitest 文件 306 项、Vite 3737 模块构建、Rust workspace 367 项通过/1 项既有性能测试 ignored、923 项文件登记、2309 个文本编码扫描、rustfmt 和项目差异检查。浏览器实测三个页面均接受 URL `000858`，控制台无 warning/error。
- `observed`：更多页面级布局偏好和交易所级实时源仍未闭环，产品总体继续保持 `partial`。本阶段未生成发布产物，未修改参考工程，未执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-29-default-symbol.md`、`apps/desktop/src/shared/settings/default-symbol.ts`、`apps/desktop/src/shared/settings/default-symbol-client.ts`、`apps/desktop/src-tauri/src/commands/settings.rs`、`tests/features/default-symbol-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 板块时序跨重启历史阶段

- `confirmed`：第 12“板块赛道”和第 40“板块资金动图”现在共享 `load_market_sector_ecology` 后端聚合；资金与涨停证据并行读取且保持独立状态，前端每次刷新只有一次聚合 IPC。
- `confirmed`：原始板块观测复用用户缓存目录的 `network-cache.sqlite3`，按上海日期分键、`observedAt` 去重、最多 12 条、TTL 7 天；周末、错日、非法时间、空资金和缺失/空涨跌停证据会被过滤，重复陈旧快照不新增或覆盖，模拟应用重启往返测试通过。
- `confirmed`：前端历史 Store 只投影后端恢复数组，已删除运行内第二套容量/去重逻辑；最后订阅者离开不会删除权威历史，聚合 IPC 失败时双子证据和历史保留 last-good 并降为 `stale`。
- `confirmed`：涨跌停来源响应必须携带合法 `data.qdate` 且与请求日期一致；没有经验证历史时 `sessionDate` 返回空，归档前缀过期逻辑行会被定向回收，不影响其他来源的陈旧回退快照。公网低频抽样仅得到 `rc=102/data=null`，所以真实公网 `qdate` 字段仍未宣称校准成功。
- `confirmed`：浏览器发现并通过失败合同修复两个页面残留的旧生命周期说明；现在明确展示当前上海交易日最多 12 个时点、用户缓存跨重启恢复和 7 天过期。新鲜门禁通过根级 Node 合同、84 个 Vitest 文件 308 项、Vite 3737 模块构建、Rust desktop 385 项通过/1 项既有性能测试 ignored、更新核心 11 项、933 项登记、2319 个文本编码扫描、rustfmt 和差异检查。两个工作区在 1280px/526px 无页面横向溢出，控制台 warning/error 为 0。
- `observed`：交易所统一时间戳、多源确认、概念多重归属与来源质量轨迹仍未接入，两个工作区和产品总体保持 `partial`。本阶段未生成发布产物、未修改参考工程、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-sector-track-history-design.md`、`docs/superpowers/plans/2026-08-29-sector-track-history.md`、`apps/desktop/src-tauri/src/application/use_cases/load_market_sector_ecology.rs`、`tests/features/sector-track-history-contract.test.mjs`。

### 2026-08-29 题材库共享刷新生命周期阶段

- `confirmed`：第 15“题材库”当前上海日期只投影 `marketAttention.hotspots` 并委托共享刷新；页面移除直接 Tauri IPC、`invokeEvidence`、挂载首刷和独立计时器，避免与 `marketMovements` 重复读取同一热点来源。
- `confirmed`：历史日期仅由用户点击触发既有 `load_market_hotspots`；同日并发读取合并，失败保留同日 last-good 并降为 `stale`，非法、未来和错日回包不会覆盖，进程内默认最多保留 8 个显式查询日期。
- `confirmed`：新鲜门禁通过根级 Node 合同、85 个 Vitest 文件 312 项、Vite 3738 个模块生产构建、14 个菜单与 937 项文件登记、2323 个文本编码扫描、rustfmt 和差异检查。浏览器 1280px/526px 均无页面横向溢出，当前/历史按钮切换正确，网页环境无假股票行且控制台 warning/error 为 0。
- `observed`：第二题材来源、逐条新闻关系、跨日自动归档和交易所日历仍未接入，题材库和产品总体继续保持 `partial`。本阶段未修改 Rust 生产文件，未重复运行 Rust workspace 全量测试；未生成发布产物、未修改参考工程、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-29-theme-library-shared-lifecycle-design.md`、`docs/superpowers/plans/2026-08-29-theme-library-shared-lifecycle.md`、`apps/desktop/src/feature/market-overview/theme-library-store.ts`、`apps/desktop/src/feature/market-overview/MarketHotspotPanel.svelte`、`tests/features/market-hotspots-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 热点播报共享刷新生命周期阶段

- `confirmed`：第 24“热点播报”只投影可注入的 `MarketAttentionStore`，刷新委托共享 `marketMovements`；页面移除直接快讯 IPC、本地证据信封、挂载首刷和计时器，搜索、筛选、原始来源和股票钻取保持不变。
- `confirmed`：失败合同先命中旧页面缺少共享 Store，迁移后全量门禁通过 85 个 Vitest 文件 312 项、Vite 3738 个模块、939 项登记、2325 个文本编码扫描、rustfmt 和差异检查；热点播报懒加载 JS 由约 5.64 kB 降到约 5.42 kB。
- `confirmed`：浏览器 1280px/526px 均无页面横向溢出；共享刷新后网页环境保持真实不可用且无假快讯或六位假代码，控制台 warning/error 为 0。
- `observed`：第二资讯来源、跨日归档和交易所级发布时间核验仍缺失，热点播报和产品总体继续保持 `partial`。本阶段未修改 Rust 生产文件，未重复运行 Rust workspace 全量测试；未生成发布产物、未修改参考工程、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-29-hotspot-broadcast-shared-lifecycle-design.md`、`docs/superpowers/plans/2026-08-29-hotspot-broadcast-shared-lifecycle.md`、`apps/desktop/src/feature/market-overview/BreakingNewsPanel.svelte`、`tests/features/market-breaking-news-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 信息总览板块热力共享刷新与真实挂载阶段

- `confirmed`：`OverviewSectorBoard.svelte` 只投影 `marketAttention.hotspots` 并委托共享刷新；页面移除直接热点 IPC、本地证据信封、上海日期计算、挂载首刷和计时器，题材样本热力、板块选择、双表与股票钻取保持不变。
- `confirmed`：浏览器验收发现该组件此前是未挂载死代码；50 工作区真实入口 `OverviewIntradayWorkspace.svelte` 现已导入并渲染板块组件。合同同时约束共享生命周期与真实挂载，防止“文件存在但用户不可见”再次被登记为完成。
- `confirmed`：新鲜门禁通过根级 Node 合同、85 个 Vitest 文件 312 项、Vite 3741 个模块生产构建、14 个菜单与 941 项文件登记、2327 个文本编码扫描、rustfmt 和差异检查。浏览器 1280px/526px 无页面横向溢出，热力和双表均可见，网页环境无假股票行且控制台 warning/error 为 0。
- `observed`：当前仍只是同花顺热点题材成员样本，完整行业成员、涨停数、市值、首次涨停、第二题材来源和交易所级时间戳未接入，因此信息总览及产品总体继续保持 `partial`。本阶段未修改 Rust 生产文件、未生成发布产物、未修改参考工程、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-29-overview-sector-board-shared-lifecycle-design.md`、`docs/superpowers/plans/2026-08-29-overview-sector-board-shared-lifecycle.md`、`apps/desktop/src/feature/market-overview/OverviewSectorBoard.svelte`、`apps/desktop/src/feature/market-overview/OverviewIntradayWorkspace.svelte`、`tests/features/reference-overview-visual-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 游资双工作区共享快照阶段

- `confirmed`：第 17“游资追踪”和第 18“游资动向”现在订阅同一领域 `HotMoneyStore`；首个订阅者只读取一次既有 `load_hot_money_tracking`，页面切换直接复用进程内证据信封，并发自动/显式刷新合并，后续显式核验仍可重新读取。
- `confirmed`：正常来源结果使用统一 last-good；传输异常有旧证据时完整保留数据、来源、观测时间、交易日、快照/血缘 ID 和缺失字段并降为 `stale`，首次失败保持真实 `unavailable`。两个页面已移除直接 Tauri IPC、本地证据信封、挂载首刷和页面级错误回退，独立 Presenter 与信息结构保持不变。
- `confirmed`：新鲜门禁通过根级 Node 合同、86 个 Vitest 文件 317 项、Vite 3742 个模块生产构建、945 项文件登记、2331 个文本编码扫描、rustfmt 和差异检查。浏览器 1280px/526px 均无页面横向溢出，网页环境无六位假股票代码且控制台 warning/error 为 0，显式重新核验仍保持真实不可用。
- `observed`：东方财富单一来源、14 日窗口、权威席位身份、题材关系和长期历史仍未补齐，两个工作区及产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-29-hot-money-shared-snapshot-design.md`、`docs/superpowers/plans/2026-08-29-hot-money-shared-snapshot.md`、`apps/desktop/src/feature/market-overview/hot-money-store.ts`、`tests/features/hot-money-tracking-contract.test.mjs`、`tests/features/hot-money-flows-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 永久日线五筛选有界生命周期阶段

- `confirmed`：第 21“百日新高”、第 22“百日新高趋势”、第 47“放量突破”、第 48“突破前高”和第 49“低位放量”现在使用同一通用 `OnDemandEvidenceStore<T>` 生命周期；每页仍只读取自己的既有命令，不预取或合并业务结果。
- `confirmed`：五个强类型 Store 共用容量为 2 的无计时器 LRU。首订阅读取一次，重入复用最近快照，并发自动/显式刷新合并；第三份有效结果只驱逐最久未使用且无订阅者的可重建前端快照，活跃页面受保护，退订后立即收敛。
- `confirmed`：传输失败有旧数据时完整保留数据、来源、时间、交易日、快照/血缘 ID 和缺失字段并降为 `stale`，首次失败保持 `unavailable`。五页已删除直接 Tauri、`EvidenceEnvelope` 本地状态、`onMount` 和页面级回退，原有 Presenter、公式、搜索、排序、分页、审计和个股钻取不变。
- `confirmed`：新鲜门禁通过根级 Node 合同、87 个 Vitest 文件 325 项、Vite 3744 模块、950 项文件登记、2336 个文本编码扫描、rustfmt 和差异检查。五页在 1280px/526px 均无页面横向溢出，普通网页环境保持真实不可用、无六位假股票代码，控制台 warning/error 为 0；预览恢复为 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：外部交易日历、复权口径和多源确认缺口没有改变，五个工作区及产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-29-daily-screening-bounded-lifecycle-design.md`、`docs/superpowers/plans/2026-08-29-daily-screening-bounded-lifecycle.md`、`apps/desktop/src/feature/shared/on-demand-evidence-store.ts`、`apps/desktop/src/feature/market-overview/daily-screening-stores.ts`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 龙虎榜按需共享生命周期阶段

- `confirmed`：第 50“龙虎榜”新增独立 `DragonTigerStore`，复用通用按需证据生命周期与容量一保留池；首订阅读取、重入复用、并发自动/显式刷新合并，且不与永久日线五筛选共用配额。
- `confirmed`：传输失败有旧数据时完整保留 last-good 并降为 `stale`，首次失败保持 `unavailable`。页面已移除直接 Tauri、`EvidenceEnvelope`、`onMount` 和页面级回退，仍保留搜索、排序、股票/席位双栏、资金仪表、来源审计和个股钻取。
- `confirmed`：新鲜门禁通过根级 Node 合同、87 个 Vitest 文件 325 项、Vite 3745 个模块生产构建、953 项文件登记、2339 个文本编码扫描、rustfmt 和差异检查。浏览器 1280px/526px 无页面横向溢出，网页环境保持真实不可用、无六位假股票代码，显式重新核验后控制台 warning/error 为 0；预览恢复为 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：东方财富单一来源、盘后发布时间二次核验、极端日截断和多年席位历史缺口不变，龙虎榜及产品总体继续保持 `partial`。本阶段未修改 Rust 生产文件、未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-dragon-tiger-shared-lifecycle-design.md`、`docs/superpowers/plans/2026-08-29-dragon-tiger-shared-lifecycle.md`、`apps/desktop/src/feature/market-overview/dragon-tiger-store.ts`、`tests/features/dragon-tiger-list-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 区间统计有界查询 Store 阶段

- `confirmed`：第 23“区间统计”新增容量三的日期键查询 Store；同键进行中请求合并，最近三个有数据区间缓存命中不重复 IPC/SQLite 聚合，第四份按 LRU 驱逐，异键晚到不会覆盖最新选择。
- `confirmed`：传输失败按区间保留 last-good 并降为 `stale`，首次失败保持 `unavailable`，无数据不占缓存。页面恢复最近日期和结果，普通运行缓存优先，刷新图标强制重聚合，并移除直接 Tauri、本地证据信封和错误编排。
- `confirmed`：新鲜门禁通过根级 Node 合同、88 个 Vitest 文件 331 项、Vite 3746 个模块生产构建、957 项文件登记、2343 个文本编码扫描、rustfmt 和差异检查。浏览器 1280px/526px 无页面横向溢出，两类运行入口均可见，网页环境保持真实不可用、无六位假股票代码且控制台 warning/error 为 0；预览恢复为 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：永久日线 SQL、Rust、DTO、交易日对齐和数据库均未修改，冷磁盘实机性能基准仍缺失。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-market-interval-query-store-design.md`、`docs/superpowers/plans/2026-08-29-market-interval-query-store.md`、`apps/desktop/src/feature/market-overview/market-interval-review-store.ts`、`tests/features/market-interval-review-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 盘中异动统一真实时间线阶段

- `confirmed`：信息总览第 01“盘中异动”新增纯函数统一时间线，将现有本机行情检测、明示代码且含真实异动信号的快讯、与事件股票相交的来源题材观测合并；分别保留本机检测、来源发布和来源观测时间语义，不伪造交易所逐笔时间。
- `confirmed`：统一记录使用稳定 ID 去重、有效时间倒序、无效时间置尾和确定性同刻排序，最多 150 条；搜索在完整排序后执行并保留原始序位。Presenter 复用同一时间线生成资讯与题材详情，删除第二套关联聚合逻辑，不新增网络、IPC、数据库、缓存、计时器或依赖。
- `confirmed`：新鲜门禁通过根级 Node 合同、89 个 Vitest 文件 335 项、Vite 3747 模块构建、961 项登记、2347 个文本编码扫描、rustfmt 和项目差异检查。浏览器 1280px/526px 无页面横向溢出，普通网页环境保持真实不可用、无六位假代码且控制台 warning/error 为 0；预览保留为 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：真实分钟序列、交易所时间戳、第二行情/资讯来源、多源确认和板块指数原值仍未接入，第 01、39、41 工作区与产品总体保持 `partial`。本阶段未修改 Rust 生产文件、未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-intraday-unified-timeline-design.md`、`docs/superpowers/plans/2026-08-29-intraday-unified-timeline.md`、`apps/desktop/src/feature/market-overview/intraday-event-timeline.ts`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 盘中异动按需真实分钟走势阶段

- `confirmed`：第 01“盘中异动”只在用户选择一条真实行情检测事件时读取单只股票腾讯当日分钟序列；统一时间线的股票钻取、快讯和题材语义不变，分钟图明确不是交易所逐笔时间戳或事件冻结窗口。
- `confirmed`：新增共享 `StockIntradayStore`，同代码请求合并、最近三份成功快照 LRU、10 秒访问时过期、跨代码晚到门禁、错码拒绝、按代码 last-good 和首次失败真实状态均有测试；不使用轮询或清理计时器。
- `confirmed`：个股观察页复用同一 Store，删除第二套分钟 IPC、序列号和失败合并；首次来源失败仍可手动重试，分钟刷新与研究增强请求序列隔离。
- `confirmed`：新鲜门禁通过全部根级 Node 合同、90 个 Vitest 文件 343 项、Vite 3750 模块生产构建、967 项文件登记、2353 个项目文本编码扫描、rustfmt 和项目差异检查。浏览器 1280px/526px 无页面横向溢出，普通网页环境保持真实不可用、无六位假股票且控制台 warning/error 为 0；预览保留为 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：交易所逐笔时间戳、第二行情/资讯来源、多源确认、事件前后冻结分钟窗口和板块指数原值仍未接入，第 01 及产品总体保持 `partial`；第 39、41 尚未复用分钟 Store。本阶段未修改 Rust 生产文件、未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-intraday-on-demand-minute-trend-design.md`、`docs/superpowers/plans/2026-08-29-intraday-on-demand-minute-trend.md`、`apps/desktop/src/feature/stock-observation/stock-intraday-store.ts`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 异动双工作区按需分钟走势阶段

- `confirmed`：第 39“异动提醒”和第 41“个股异动”现在从用户显式选择的真实关联股票或横截面行调用唯一 `StockIntradayStore`；未选择时零分钟请求，两页没有直接 Tauri、分钟 IPC 或新计时器。
- `confirmed`：新增共享 `MarketStockIntradayDetail.svelte`，只展示股票身份、调用方时间语义、三项既有事实、现有分钟图、重试、个股入口和非逐笔边界；第 01 的事件详情也缩为该组件的字段适配器，三个入口不再重复实现详情布局。第 39 保留提醒优先级、搜索筛选、已读/确认/忽略永久动作和失败回滚；第 41 保留完整排名、透明阈值和快讯线索。
- `confirmed`：提醒发生时间、横截面观测时间和分钟读取时轨迹分别呈现；快讯明示代码不升级为因果，分钟图不冒充交易所逐笔时间或事件前后冻结窗口。同代码请求合并、三份 LRU、10 秒访问 TTL、错码拒绝、竞态门禁、首次 `unavailable` 和 last-good `stale` 继续由共享 Store 唯一实现。
- `confirmed`：新鲜门禁通过根级 Node 合同、90 个 Vitest 文件 343 项、Vite 3751 个模块生产构建、971 项文件登记、2357 个文本编码扫描、rustfmt 和项目差异检查。浏览器第 39/41 在 1280px/526px 无页面横向溢出，普通网页环境保持真实不可用、无六位假股票代码且控制台 warning/error 为 0；预览恢复为 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：交易所逐笔事件时间、第二行情/资讯来源、多源确认和事件前后冻结分钟窗口仍未接入，第 39、41 与产品总体保持 `partial`。本阶段未修改 Rust 生产文件、未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-movement-workspaces-minute-trend-design.md`、`docs/superpowers/plans/2026-08-29-movement-workspaces-minute-trend.md`、`apps/desktop/src/feature/market-overview/MarketStockIntradayDetail.svelte`、`tests/features/market-movement-minute-drilldown-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 异动股票双来源现价核验阶段

- `confirmed`：第 01、39、41 在唯一共享分钟详情内按需比较东方财富横截面现价与腾讯分钟最新价；纯函数严格校验代码、正数价格、交易日和观测时间，以 `0.15%` 容差和 `120` 秒可比窗口区分一致、偏差、时点分离、时点未知、错日、双向单边和不可用，不选择真值或升级陈旧证据。
- `confirmed`：第 39 按代码回查既有异动行，不在提醒模型复制价格；快讯发布时间、横截面价格观测时间和分钟读取时间保持分离。第 01、41 只传递已有字段，三个入口不新增请求、IPC、缓存、计时器、预取或平台专属代码。
- `confirmed`：TDD 失败证据有效；新鲜门禁通过根级 Node 合同、91 个 Vitest 文件 353 项、Vite 3754 模块构建、977 项登记、2363 个文本编码扫描、rustfmt 和项目差异检查。三个工作区在 1280px/526px 无页面横向溢出，网页环境保持真实不可用、无六位假股票代码，控制台 warning/error 为 0；预览恢复为 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：原子同刻双源快照、交易所逐笔事件时间、事件冻结分钟窗口、第三行情/第二资讯来源和来源优先级裁决仍未接入，因此三个工作区及产品总体保持 `partial`。本阶段未生成发布产物、未修改参考工程、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-market-stock-price-cross-confirmation-design.md`、`docs/superpowers/plans/2026-08-29-market-stock-price-cross-confirmation.md`、`apps/desktop/src/feature/market-overview/market-stock-price-confirmation.ts`、`tests/features/market-stock-price-cross-confirmation-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 事件前后分钟窗口按需重建阶段

- `confirmed`：第 01“盘中异动”、第 39“异动提醒”和第 41“个股异动”现在复用既有腾讯分钟快照，按各自调用方时间语义重建事件前后各 5 个自然分钟窗口；上海时区、交易日、连续竞价时段和精确事件分钟均需验证，不用最近点替代缺失锚点，也不跨午休拼接。
- `confirmed`：纯函数区分完整、未来待形成、成熟但不完整、仅事件分钟、错交易日、时间待核验、非连续竞价时段、缺事件分钟和不可用九类状态；来源 `stale` 独立保留。共享组件展示真实分钟格、前后变化和窗口分钟量，不新增请求、IPC、缓存、数据库、计时器、依赖或平台专属代码。
- `confirmed`：新鲜门禁通过全部根级 Node 合同、92 个 Vitest 文件 363 项、Vite 3757 个模块生产构建、983 项文件登记、2369 个文本编码扫描、rustfmt 和项目差异检查。三个工作区在 1280px/526px 均无页面横向溢出，网页环境保持真实不可用、无六位假股票代码，控制台 warning/error 为 0；预览恢复为 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：该窗口是读取时按需重建，不是交易所逐笔事件时间或事件时冻结快照；原子同刻双源、第三行情/第二资讯来源和来源裁决仍缺失，三个工作区及产品总体保持 `partial`。AI+题材、题材挖掘和热点解读没有挂载该详情，其事件窗口缺口不变。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-event-relative-minute-window-design.md`、`docs/superpowers/plans/2026-08-29-event-relative-minute-window.md`、`apps/desktop/src/feature/market-overview/event-relative-minute-window.ts`、`apps/desktop/src/feature/market-overview/MarketEventMinuteWindow.svelte`、`tests/features/event-relative-minute-window-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 信息与题材分钟反应窗口阶段

- `confirmed`：第 03“AI+题材”和第 43“热点解读”只允许用户从当前可见的明示代码证据链选择股票，以各自来源 `publishedAt` 作为信息观察锚点；第 25“题材挖掘”只允许从当前可见运行内异动选择股票，以真实 `detectedAt` 作为本机检测锚点。三页均复用唯一 `StockIntradayStore`、共享分钟详情和事件前后五分钟窗口，不新增请求、IPC、Rust、数据库、缓存、计时器、依赖或平台专属代码。
- `confirmed`：未选择时零分钟请求；搜索、切换题材或刷新使证据离开可见集合时关闭详情，不自动选择或预取。三个适配器传入 `primaryPrice={null}`，不从涨跌幅反推价格；原有个股观察入口继续保留。
- `confirmed`：新鲜门禁通过全部根级 Node 合同、92 个 Vitest 文件 363 项、Vite 3757 个模块生产构建、986 项文件登记、2372 个文本编码扫描、rustfmt 和项目差异检查。第 03、25、43 在 1280px/526px 均无页面横向溢出，网页环境保持真实不可用、无六位假股票代码，控制台 warning/error 为 0；实时预览恢复并保持在总览页。
- `observed`：新闻发布时间和本机检测时间都不是交易所事件或逐笔异动时间；读取时重建窗口不是事件时冻结快照，明示代码连接不证明新闻导致价格变化。多源新闻/公告核验、交易所时间、事件冻结快照、跨日历史与因果证据仍缺失，因此三个工作区及产品总体继续保持 `partial`。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-information-reaction-minute-window-design.md`、`docs/superpowers/plans/2026-08-29-information-reaction-minute-window.md`、`apps/desktop/src/feature/market-overview/AiThemesPanel.svelte`、`apps/desktop/src/feature/market-overview/ThemeMiningPanel.svelte`、`apps/desktop/src/feature/market-overview/HotspotInterpretationPanel.svelte`、`tests/features/information-reaction-minute-window-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 分钟行情第二来源与准确性治理阶段

- `confirmed`：唯一单股分钟链路现在以腾讯为主源，仅在腾讯失败或熔断后按需回退东方财富 `trends2`；两源分别使用 10 秒缓存、请求去重键和 3 次失败/60 秒冷却熔断，不并行、不拼接、不平均。两源均失败时只选择同股观测时间更新的旧快照。
- `confirmed`：新增跨来源分钟校验与东财适配器；腾讯最多接收 320 行原始记录，连续竞价仍限 242 点，合法盘后点单独计数并从曲线排除。`92xxxx` 映射北交所，`900xxx` 保持上海。百度 `ktype=1` 实测为日 K 且北交所样本为空，明确排除在分钟合同之外。
- `confirmed`：分时面板按证据信封显示真实来源，覆盖率排除已知场外点，坏行仍保留 `partial`；旧缓存通过 `serde(default)` 兼容新增质量字段。新鲜验证通过根级合同、92 个 Vitest 文件 363 项、Vite 3757 模块构建、Rust desktop 395 项通过/1 项既有性能测试忽略、updater-core 11 项、991 项登记、2377 个文本编码扫描、rustfmt 和差异检查。
- `confirmed`：浏览器 1280px/526px 页面无页面级横向溢出，普通网页环境保持真实不可用、无六位假代码且控制台 warning/error 为 0；预览继续保留在 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `observed`：该阶段只解决来源单点故障，不构成原子同刻双源交叉确认。交易所逐笔、事件时冻结分钟快照和历史分钟线仍缺失，相关工作区及产品总体保持 `partial`。未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-stock-intraday-fallback-design.md`、`docs/superpowers/plans/2026-08-29-stock-intraday-fallback.md`、`apps/desktop/src-tauri/src/infrastructure/sources/intraday_validation.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_intraday.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_stock_intraday.rs`、`tests/features/stock-intraday-fallback-contract.test.mjs`。

### 2026-08-29 事件分钟证据有界封存阶段

- `confirmed`：第 01“盘中异动”、第 03“AI+题材”、第 25“题材挖掘”、第 39“异动提醒”、第 41“个股异动”和第 43“热点解读”现在只对用户明确选中的真实事件或明示股票封存同分钟证据。前端复用唯一 `StockIntradayStore` 已取得的证据信封，不发起第二次分钟行情请求，也不新增定时器、后台轮询或自动预取。
- `confirmed`：Rust 统一验证稳定事件身份、六位代码、带时区事件时间、上海交易日、连续竞价时段、精确事件分钟和分钟点合法性；只保存事件前后各 5 个自然分钟、最多 11 点，不跨午休、不用邻近点替代锚点。事件来源价与分钟锚点价保留来源独立性、同分钟一致/偏差/时点分离/不可用状态，不选择真值或声称因果。
- `confirmed`：记录复用用户缓存目录中的 `network-cache.sqlite3`，TTL 为 7 天，同前缀最多 300 条；`capturing/partial` 只允许整记录单调升级，完整 `sealed` 记录不可覆盖。来源陈旧保留 `stale`，首次失败保留 `missing/unavailable`，持久化不可用时降为 `partial`，不填充假价格、时间或来源独立性。
- `confirmed`：独立复审关闭提醒身份缺时刻、缓存身份错配、非事务单调写入、缺口误封存、交易时段过宽、前端晚到降级六项问题，并补充损坏同键 payload 的事务内自修复。新鲜门禁通过定向 Rust 21 项、根级合同与 92 个 Vitest 文件 359 项、Vite 3757 模块生产构建、Rust desktop 417 项通过/1 项显式性能基准忽略、updater-core 11 项、1000 项文件登记、2386 个文本编码扫描、rustfmt 和差异检查。1280px 本轮复测无页面级横向溢出，普通网页环境保持真实不可用、无六位假股票代码且控制台 warning/error 为 0；526px 沿用本阶段既有通过证据，本轮应用内浏览器固定视口且安全策略禁止受控窄屏容器，未伪称重新复测。预览保持在 `http://127.0.0.1:1420/market-overview?preview=latest`。
- `obsolete`：上一阶段关于“读取时重建窗口不是事件冻结证据”的当前适用性已被本阶段缩窄；现在的准确口径是“用户选中的同分钟证据在读取既有分钟证据后有界封存”，仍不是所有事件发生时自动捕获。
- `observed`：交易所逐笔事件时间、所有事件自动发生时捕获、原子同一瞬时双源快照、历史分钟回填、更多独立行情/资讯/公告来源和因果证据仍缺失，因此六个工作区、相关功能和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-event-minute-evidence-freeze-design.md`、`docs/superpowers/plans/2026-08-29-event-minute-evidence-freeze.md`、`crates/contracts/src/event_minute_evidence.rs`、`apps/desktop/src-tauri/src/domain/market/event_minute_evidence.rs`、`apps/desktop/src-tauri/src/infrastructure/cache/event_minute_evidence_archive.rs`、`apps/desktop/src-tauri/src/application/use_cases/capture_event_minute_evidence.rs`、`apps/desktop/src/feature/market-overview/event-minute-evidence-store.ts`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 公司研究完整三表与窄屏验收阶段

- `confirmed`：公司研究新增新浪公开来源的资产负债表、利润表和现金流量表，三表按股票与报表类型独立使用 6 小时两级缓存、请求去重和共享熔断；最多四个报告期、每期 240 个原始科目，失败按同股同表保留 last-good 并降为 `stale`。上海和深圳映射已验证，北交所保持真实 `unavailable`。
- `confirmed`：三表与基础研究并行启动，前端只渲染当前表当前期；Store 提供同股请求合并、两只股票 LRU、跨股晚到隔离、强制刷新和真实失败状态。网页环境缺少桌面服务时不生成报表行或示例值。
- `confirmed`：窄屏合同先按预期因缺少单行约束和宽度余量失败；修复后 526px 实测页面宽度 `526/526`、标签组 `212/212`，三个标签均为 42px 高、`nowrap` 和 11px，控制台 warning/error 为 0。预览保留在 `http://127.0.0.1:1420/company-research?preview=latest`。
- `confirmed`：新鲜门禁为 93 个 Vitest 文件 366 项、Vite 3761 模块、Rust desktop 426 项通过/1 项既有性能测试 ignored、updater-core 11 项、1011 项文件登记、2397 个文本编码扫描、rustfmt 和差异检查通过。
- `observed`：三表第二来源、会计重述与审计语义、北交所映射、商业模式/壁垒/催化剂和真实 AI 供应商仍未完成，因此公司研究和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-company-financial-statements-design.md`、`docs/superpowers/plans/2026-08-29-company-financial-statements.md`、`apps/desktop/src/feature/company-research/ResearchFinancialStatementsPanel.svelte`、`tests/features/company-financial-statements-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 公司研究机构研报与原始 EPS 阶段

- `confirmed`：公司研究新增东方财富公开机构研报目录，单次只取首屏最多 20 条，严格校验股票身份、安全报告 ID、日期和有界文本；保留机构、作者、来源原始评级、评级变化、行业和三年原始 EPS，PDF 仅供用户显式点击，不自动下载或送入 AI。
- `confirmed`：每只股票使用 2 小时两级缓存、同股请求合并和专属 3 次失败/60 秒熔断；成功空数组为 `ready`，坏行/丢弃/截断/去重为 `partial`，同股 last-good 为 `stale`，首次失败为 `unavailable`。前端 Store 保留两只股票 LRU、拒绝快照及逐条错码并隔离跨股晚到。
- `confirmed`：全宽面板展示真实来源状态、观测时间、研报/机构/EPS 覆盖、机构原始评级、三年原始 EPS 和原文入口；不计算目标价、前向 PE、PEG、涨跌空间或平台建议。526px 实测页面 `526/526`、研报区 `251/251`，普通网页环境为零行真实不可用且控制台 warning/error 为 0，预览保留在 `http://127.0.0.1:1420/company-research?preview=latest`。
- `confirmed`：新鲜门禁通过全部根级 Node 契约、94 个 Vitest 文件 374 项、Vite 3764 模块、Rust desktop 433 项通过/1 项既有性能测试 ignored、updater-core 11 项、1022 项登记、2408 个项目文本编码扫描、rustfmt 和差异检查。
- `observed`：机构研报第二来源、目标价与全文 PDF 语义、北交所覆盖和 AI 授权接入仍未完成，公司研究和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-company-research-reports-design.md`、`docs/superpowers/plans/2026-08-29-company-research-reports.md`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_research_reports.rs`、`apps/desktop/src/feature/company-research/ResearchReportsPanel.svelte`、`tests/features/company-research-reports-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 公司概况与主营事实阶段

- `confirmed`：公司研究新增东方财富公开 F10 公司概况和主营分析两条独立来源；展示公司名称、证券类型、行业、主营概述、公司简介、经营范围、成立/上市日期、员工、网站、地址、注册资本、主营业务范围、最新行业/产品/地区构成和最新经营评述。股票身份、日期、类别、有限数值、文本和记录上限均有审计，缺失值不替换为零。
- `confirmed`：两个来源分别使用6小时内存/用户缓存、规范请求键、同股请求合并和独立3次失败/60秒熔断，并行完成后保留各自 `ready/partial/stale/missing/unavailable`；单源失败不清空另一源，同股旧值回退为 `stale`。前端 Store 保留两只股票 LRU、强刷、跨股晚到隔离和顶层/嵌套错码拒绝。
- `confirmed`：独立面板展示来源状态、公司档案、五类原始文本和分类主营构成；普通网页环境无桌面 IPC 时保持真实不可用，不生成示例公司或构成行。本阶段未引入 Python、数据库表、计时器、后台任务、平台专属业务代码或新第三方依赖。
- `confirmed`：公共 F10 解析集中到共享模块，来源解析、并发加载和状态组合保持独立职责，三份 Rust 测试拆为独立文件。新鲜门禁通过全部根级 Node 契约、95 个 Vitest 文件 382 项、Vite 3767 模块、Rust desktop 445 项通过/1 项既有性能测试 ignored、updater-core 11 项、1039 项登记、2425 个项目文本编码扫描、rustfmt 和差异检查。1280px 与 526px 页面/面板宽度分别为 `1280/1280`、`1023/1023` 和 `526/526`、`251/251`，无面板溢出后代；网页环境真实不可用、零公司身份/事实/构成行且控制台 warning/error 为 0，预览保留在公司研究页。
- `observed`：公司事实第二来源、可核验竞争壁垒/催化/逻辑失效、审计重述、完整 PDF 语义和真实 AI 供应商仍未完成，因此公司研究与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-company-business-profile-design.md`、`docs/superpowers/plans/2026-08-29-company-business-profile.md`、`crates/contracts/src/company_business_profile.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_company_profile.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_business_analysis.rs`、`apps/desktop/src-tauri/src/application/use_cases/company_business_profile_status.rs`、`apps/desktop/src/feature/company-research/ResearchBusinessProfilePanel.svelte`、`tests/features/company-business-profile-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 公司研究十段账本与十项反方审查阶段

- `confirmed`：公司研究已新增十段固定研究账本和十项确定性反方审查，纯 TypeScript 派生层只复用页面已有财务摘要、完整三表、公司概况、主营构成、机构研报、行业、公告和估值证据；没有新增网络、IPC、数据库、缓存、计时器、后台任务、AI 调用或第三方依赖。
- `confirmed`：同比只比较上年同月同日报告期；现金利润比只在净利润为正时计算；资产负债率和同期毛利率只接受明确三表科目、同报告期和可核验单位。规则状态 `clear/triggered/unavailable` 与证据状态 `ready/partial/stale/missing/unavailable` 独立保存；未触发不代表风险不存在。冻结 20 日波动率、60 日回撤、历史估值分位、可核验同行与市场份额等证据未接入时保持真实不可用，不生成评分、目标价或买卖建议。
- `confirmed`：新鲜门禁通过 98 个 Vitest 文件 393 项、Vite 3772 模块生产构建、Rust workspace 445 项通过且 1 项既有性能测试 ignored、更新核心 11 项、14 个菜单、1050 项文件登记、2436 个项目文本编码扫描、rustfmt、架构和项目差异检查。浏览器在 1280px 与 526px 均无页面或账本横向溢出，十段与十项完整唯一渲染，普通网页模式仅展示真实证据缺口和核验清单，控制台 warning/error 为 0。
- `observed`：主参考根当前已跟踪差异为 0；辅助只读工作树当前存在大量其他改动，本阶段没有对参考根或该工作树执行写操作，也未生成 EXE、安装包或 ZIP。公司研究与产品总体仍因多源确认、历史估值、市场风险冻结、独立催化分类和真实 AI 供应商等缺口保持 `partial`。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-company-research-ledger-design.md`、`docs/superpowers/plans/2026-08-29-company-research-ledger.md`、`apps/desktop/src/feature/company-research/company-research-ledger-presenter.ts`、`apps/desktop/src/feature/company-research/ResearchLedgerPanel.svelte`、`tests/features/company-research-ledger-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 公司市场风险冻结证据阶段

- `confirmed`：公司研究新增独立本地市场风险切片。最近 21 个连续有效收盘价形成 20 个未年化日收益率波动率，最近 60 个连续有效收盘价形成固定窗口最大回撤；六位股票身份、日期、正有限收盘价、重复日期和来源均经 Rust 领域校验，单股只读永久库最多 60 行。
- `confirmed`：读取通过 `spawn_blocking` 与既有远程公司证据并行，继续复用唯一 `load_company_research` IPC。缺数据、数据库失败和有效单源证据分别保持 `missing/unavailable/partial`，不增加网络、缓存、数据库表、计时器、依赖或平台专属业务代码。
- `confirmed`：账本只接收股票、截止日、固定 20/60 窗口和有限指标均合法的嵌套切片；C08 在波动率达到 8% 或回撤达到 -20% 时触发。独立面板展示真实状态、两项指标、样本审计、来源和限制，不生成评分、目标价或买卖建议。
- `confirmed`：新鲜门禁通过 98 个 Vitest 文件 400 项、Vite 3774 模块、Rust desktop 457 项通过且 1 项既有性能测试 ignored、updater-core 11 项、14 个菜单、1056 项登记、2442 个文本编码扫描、rustfmt、架构和项目差异检查。1280px 与 526px 页面/面板宽度分别为 `1280/1280`、`1021/1021` 和 `526/526`、`250/250`，无面板溢出后代；网页环境保持真实不可用和 `--`，C08 固定规则实际渲染，控制台 warning/error 为 0。
- `observed`：未复权日线、外部交易日历、第二日线来源和导入新鲜度仍未完成，公司研究及产品总体保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-company-market-risk-evidence-design.md`、`docs/superpowers/plans/2026-08-29-company-market-risk-evidence.md`、`apps/desktop/src-tauri/src/domain/market/company_market_risk.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_company_market_risk.rs`、`apps/desktop/src/feature/company-research/ResearchMarketRiskPanel.svelte`、`tests/features/company-market-risk-evidence-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 投资日历分红除权官方事项阶段

- `confirmed`：第 32“投资日历”新增东方财富 `RPT_SHAREBONUS_DET` 未来 90 日分红除权切片。分红与限售解禁拥有独立 DTO、来源、缓存前缀、请求键、熔断器、IPC、Store、Presenter 和组件，只共享固定日期窗口与泛型缓存/去重/熔断/旧值回退加载器；每次最多 200 条、缓存 6 小时、同前缀最多 8 个窗口键，不新增轮询、首屏预取、数据库表或平台专属业务调用。
- `confirmed`：除权除息日只使用 `EX_DIVIDEND_DATE`；现金、送股、转增只读取 `PRETAX_BONUS_RMB`、`BONUS_RATIO`、`IT_RATIO`，仅在 `IT_RATIO` 缺失时回退同源 `BONUS_IT_RATIO`。合法事项、确认空窗、同窗旧值和首次失败分别保持 `partial/missing/stale/unavailable`，不从方案文本反解析数值，不生成演示事项。
- `confirmed`：2026-08-29 真实公开来源对 `2026-08-29` 至 `2026-11-27` 返回 51 条，其中 50 条含现金字段、1 条含转增字段。新鲜门禁通过 100 个 Vitest 文件 408 项、Vite 3782 模块、Rust desktop 482 项通过/1 项既有性能测试 ignored、updater-core 11 项、14 个菜单、1092 项登记、2478 个项目文本编码扫描、rustfmt、架构和项目差异检查。
- `confirmed`：1280px 与 526px 页面/分红面板宽度分别为 `1280/1280`、`1021/1021` 和 `526/526`、`250/250`；三个分红标题完整渲染，普通网页环境保持真实来源不可用和零事项，控制台 warning/error 为 0，预览保留在投资日历页。
- `observed`：财报披露、股东大会、未形成除权日的分红预案、第二事项与资讯来源和跨日资讯归档仍缺失，因此投资日历和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-investment-calendar-dividend-events-design.md`、`docs/superpowers/plans/2026-08-29-investment-calendar-dividend-events.md`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_dividend_calendar.rs`、`apps/desktop/src-tauri/src/application/use_cases/investment_calendar_window_loader.rs`、`apps/desktop/src/feature/market-overview/InvestmentDividendEvents.svelte`、`tests/features/investment-calendar-dividend-events-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 投资日历财报预约披露阶段

- `confirmed`：第 32“投资日历”新增东方财富 `RPT_PUBLIC_BS_APPOIN` 未来 90 日财报预约披露切片。财报拥有独立 DTO、两页来源、缓存前缀、请求键、熔断器、IPC、Store、Presenter、组件和样式，只复用固定日期窗口与共享加载器；后端最多顺序读取两页各 500 条，前端每页固定 50 条，缓存 6 小时且同前缀最多 8 个窗口键。
- `confirmed`：预约披露日、报告期、首次预约、最新变更和实际披露日保持独立；发布状态只严格映射来源 `IS_PUBLISH`。坏必填、坏可选字段、重复、排序和截断均保留审计，合法事项、空窗、同窗旧值和首次失败分别保持 `partial/missing/stale/unavailable`，不生成财报结果、日程或演示事项。
- `confirmed`：2026-08-29 对窗口 `2026-08-29` 至 `2026-11-27` 的真实来源复核为总计 922 条、2 页，第一页 500 条、第二页 422 条，当前两页策略完整覆盖。新鲜门禁通过 101 个 Vitest 文件 412 项、Vite 3786 模块、Rust desktop 490 项通过/1 项既有性能测试 ignored、updater-core 11 项、14 个菜单、1109 项登记、2495 个项目文本编码扫描、rustfmt、架构和项目差异检查。
- `confirmed`：1280px 与 526px 页面/财报面板宽度分别为 `1280/1280`、`1022.8/1022.8` 和 `526/526`、`251.2/251.2`；三个财报标题、搜索和状态筛选实际渲染且无页面级溢出，网页环境保持真实来源不可用和零事项，控制台 warning/error 为 0。50 条分页由 Presenter 与跨层合同覆盖，没有注入假数据做视觉验收。
- `observed`：股东大会、未形成除权日的分红预案、第二事项与资讯来源和跨日资讯归档仍缺失，投资日历和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-investment-calendar-financial-disclosures-design.md`、`docs/superpowers/plans/2026-08-29-investment-calendar-financial-disclosures.md`、`crates/contracts/src/investment_calendar_disclosure.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_disclosure_calendar.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_investment_calendar_disclosures.rs`、`apps/desktop/src/feature/market-overview/InvestmentFinancialDisclosures.svelte`、`tests/features/investment-calendar-financial-disclosures-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 投资日历股东大会官方事项阶段

- `confirmed`：第 32“投资日历”新增东方财富 `RPT_GENERALMEETING_DETAIL` 未来 90 日股东大会切片。股东大会拥有独立 DTO、三页来源、缓存前缀、请求键、熔断器、IPC、容量 1 Store、Presenter、组件和样式，只复用固定日期窗口与共享加载器；后端最多顺序读取三页各 500 条，前端每页固定 50 条，缓存 6 小时且同前缀最多 8 个窗口键。
- `confirmed`：会议日只使用 `START_ADJUST_DATE`；登记、网络投票、通知、调整和决议公告日期保持独立。正常、延期、取消、未知只按来源原始状态精确映射；坏必填、坏可选字段、跨页一致性、重复、排序和截断均保留审计，合法事项、空窗、同窗旧值和首次失败分别保持 `partial/missing/stale/unavailable`，不生成投票结果、投资判断或演示事项。
- `confirmed`：2026-08-29 对窗口 `2026-08-29` 至 `2026-11-27` 的真实来源复核为 1484 条、3 页，三页 `500/500/484`；1484 个身份无重复，1482 条正常、2 条延期，议案、地点及网络投票起止日无缺失。新鲜门禁通过 102 个 Vitest 文件 416 项、Vite 3790 模块、Rust desktop 498 项通过/1 项既有性能测试 ignored、updater-core 11 项、14 个菜单、1126 项登记、2512 个项目文本编码扫描、rustfmt、架构和项目差异检查。
- `confirmed`：1280px 与 526px 页面/股东大会面板宽度分别为 `1280/1022.8` 和 `526/251.2`；“股东大会日程”“未来会议安排”“议案与完整性”实际渲染且无页面或面板横向溢出，网页环境保持真实来源不可用和零会议，控制台 warning/error 为 0，预览保留在投资日历页。
- `observed`：未形成除权日的分红预案、第二事项与资讯来源和跨日资讯归档仍缺失，投资日历和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-investment-calendar-shareholder-meetings-design.md`、`docs/superpowers/plans/2026-08-29-investment-calendar-shareholder-meetings.md`、`crates/contracts/src/investment_calendar_meeting.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_meeting_calendar.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_investment_calendar_meetings.rs`、`apps/desktop/src/feature/market-overview/InvestmentShareholderMeetings.svelte`、`tests/features/investment-calendar-shareholder-meetings-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 共享生命周期与事件证据只读审计

- `observed`：共享刷新审计发现涨跌停 Store 的 stale 回退可能丢失旧信封交易日/观测时间；隐藏窗口首个挂载仍可能发起请求；刷新偏好接线缺少 Store 行为测试；大单页面固定刷新文案与用户可配置间隔不一致。
- `observed`：板块资金历史审计发现休市日可能被归档为空间观测日，空/畸形快照可能进入权威历史，七天 TTL 不会自动删除过期 SQLite 记录。
- `observed`：事件分钟封存审计发现同股同日提醒身份可能复用旧封存时间，并发 capture 的读后写存在 partial 覆盖 sealed 的竞态；完整窗口只检查两端点，未验证中间分钟连续性。
- `observed`：以上均为只读审计发现，尚无修复后的完整新鲜证据；产品和相关工作区继续保持 `partial`。
- 来源：`task:01a049ca-e283-7900-aecc-791c039e3f82`、`task:01a04a6c-0af7-7543-ae41-4ec364cacf0a`、`task:01a04bfc-b806-7072-88cf-0412594441a4`、`task:01a04c14-4655-7b20-a29b-1c324deae41d`、对应设计/计划和定向审计输出。

### 2026-08-29 投资日历分红预案观察阶段

- `confirmed`：第 32“投资日历”新增最近 90 日、尚未形成除权日的分红预案观察切片。独立 DTO、两页顺序来源、严格解析、6 小时/8 窗口缓存、请求去重、独立熔断、IPC、容量 1 按需 Store、Presenter、组件和样式已接线；前端每页固定 50 条，不新增轮询、首屏预取、数据库表或平台专属业务调用。
- `confirmed`：预案公告日、来源更新日和报告期保持独立；服务端过滤后仍本地排除非空除权日与精确“实施分配”，阶段只按来源原值映射。现金、送股、转增只读取来源数值字段，不从方案文本推断，页面明确“除权除息日尚未形成”，不预测实施概率或投资结果。
- `confirmed`：2026-08-29 串行复核 `2026-05-31..2026-08-29` 两页公开来源为 `646` 条、分页 `500/146`；53 条带除权日、52 条实施分配，严格过滤后 593 条且身份唯一，阶段为预披露 3、董事会通过 576、股东大会通过 14、未知 0。44 条公告日与更新日不同，现金字段覆盖 582 条、转增字段覆盖 12 条，593 条必需文本完整。
- `confirmed`：新鲜门禁通过 110 个 Node 合同、103 个 Vitest 文件/420 项、Vite 生产构建、Rust desktop 505 项通过且 1 项既有性能基准忽略、updater-core 11 项、14 个菜单、1142 项文件登记、2528 个文本编码扫描、rustfmt 和项目差异检查。1280×720 与 526×900 实页均无页面或组件横向溢出，普通网页环境保持真实不可用和零预案，控制台 warning/error 为 0。
- `observed`：第二事项与资讯来源及跨日资讯归档仍未接入，因此投资日历与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/plans/2026-08-29-investment-calendar-dividend-proposals.md`、`apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_dividend_proposal_calendar.rs`、`apps/desktop/src/feature/market-overview/InvestmentDividendProposals.svelte`、`tests/features/investment-calendar-dividend-proposals-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 投资日历跨日资讯归档阶段

- `confirmed`：第 32“投资日历”已把单次共享快讯投影升级为最近 30 个上海自然日、跨重启的有界归档。新命令复用既有 60 秒两级缓存、请求去重和同一熔断器；东方财富无时区 `showTime` 按上海 `+08:00` 严格规范化，只归档时间合法且原文明示六位 A 股代码的事件。
- `confirmed`：归档继续使用既有用户缓存库，TTL 30 天、最多 31 个日期键、每日最多 200 条；前端使用独立容量 1 Store、纯 Presenter 和组件，日期/搜索过滤先于每日 50 条可见上限。状态保持 `partial/missing/stale/unavailable`，不新增网络源、轮询、后台任务、数据库表、依赖或假事件。
- `confirmed`：一次串行公开来源复核返回 50 行，50 行 `showTime` 均为严格本地时间格式且可按上海时区解析，本次原文明示六位 A 股代码事件为 0；未保存原始标题、摘要或完整响应。新鲜门禁通过 111 个 Node 合同、104 个 Vitest 文件/423 项、Vite 3797 模块、Rust desktop 518 项通过/1 项既有性能测试忽略、updater-core 11 项、1159 项文件登记、2545 个文本编码扫描、rustfmt 和项目差异检查。
- `confirmed`：1280×720 与 526×900 实页的页面/归档宽度分别为 `1280/1280`、`1023/1023` 和 `526/526`、`251/251`，无归档后代横向溢出；标题、日期、搜索、真实不可用和零事件空态均存在，控制台 warning/error 为 0。
- `observed`：第二事项来源、第二资讯来源和应用未运行时全天采集仍未完成，因此投资日历与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-investment-calendar-news-archive-design.md`、`docs/superpowers/plans/2026-08-29-investment-calendar-news-archive.md`、`crates/contracts/src/investment_calendar_news_archive.rs`、`apps/desktop/src-tauri/src/infrastructure/cache/investment_calendar_news_archive.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_investment_calendar_news_archive.rs`、`apps/desktop/src/feature/market-overview/InvestmentNewsArchive.svelte`、`tests/features/investment-calendar-news-archive-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-29 热点播报 30 日时间轴阶段

- `confirmed`：第 24“热点播报”保留东方财富 7×24 共享实时流，并复用投资日历既有跨重启归档形成独立的 30 日热点时间轴。共享纯投影统一严格日期、上海时间、错日/无代码排除和跨日稳定编号，投资日历与热点播报不再重复这组规则。
- `confirmed`：热点播报新增来源信号/股票索引、日期/搜索/信号筛选、最多 50 条事件刻度、来源详情和股票钻取。索引基于完整合法归档按事件去重计数；筛选先于截断，筛选不重排原始编号，真实零信号不补默认标签。
- `confirmed`：组件唯一挂载在实时流之后，复用既有容量 1 Store、唯一 IPC、60 秒缓存、请求去重、熔断器和跨重启归档；未新增 Rust、网络来源、数据库、缓存文件、轮询、计时器、可见性监听、依赖或假事件。
- `confirmed`：新鲜门禁通过 Node 112 项、106 个 Vitest 文件/430 项、Vite 3801 模块、Rust desktop 518 项通过/1 项既有性能测试忽略、updater-core 11 项、14 个菜单、1169 项文件登记、2555 个文本编码扫描、rustfmt、架构和差异检查。
- `confirmed`：1280×720 与 526×900 实页的页面/热点时间轴宽度分别为 `1280/1280`、`1023/1023` 和 `526/526`、`251/251`；三个标题和三类筛选均渲染，组件后代横向溢出为 0，控制台 warning/error 为 0。普通网页环境保持真实不可用和零热点，预览保留在 `http://127.0.0.1:1420/?workspace=hotspot-broadcast`。
- `observed`：第二资讯来源、交易所级发布时间核验和语义级题材关系仍未接入，因此热点播报与产品总体继续保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-29-hotspot-broadcast-archive-design.md`、`docs/superpowers/plans/2026-08-29-hotspot-broadcast-archive.md`、`apps/desktop/src/feature/market-overview/investment-calendar-news-archive-projection.ts`、`apps/desktop/src/feature/market-overview/hotspot-broadcast-archive-presenter.ts`、`apps/desktop/src/feature/market-overview/HotspotBroadcastArchive.svelte`、`tests/features/hotspot-broadcast-archive-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 热点播报同交易日直接题材关系阶段

- `confirmed`：第 24“热点播报”与第 43“热点解读”已复用唯一 `hotspot-topic-linker.ts`。连接器只按快讯原文明示六位代码、合法带时区发布时间和相同上海日期连接同花顺热点股票样本；题材只保留来源原值，错日、非法时间、错日股票、空题材和无交集均保持真实零关系。
- `confirmed`：第 24 Presenter 对最多 6200 条合法归档输入保留最多 200 条同日证据链；日期、搜索、信号和题材筛选均先于 50 条可见上限。历史事件继续展示但 `sourceThemes` 为空，题材索引按唯一事件计数，不从标题、摘要或 AI 推断。
- `confirmed`：父级只把既有热点信封传入唯一归档子组件；页面新增七项摘要、同交易日来源题材索引、题材筛选、事件/详情题材和归档/热点两个独立状态面板，没有新增 Rust、IPC、网络、Store、数据库、缓存、计时器、轮询、依赖或后台任务。
- `confirmed`：新鲜门禁通过 113 个 Node 合同、107 个 Vitest 文件 440 项、Vite 3802 模块、Rust desktop 518 项通过且 1 项既有性能测试忽略、更新核心 11 项、14 个菜单、1174 项登记、2560 个文本编码扫描、rustfmt、架构和差异检查。1280×720 与 526×900 页面/面板宽度分别为 `1280/1023` 和 `526/251`，无横向溢出，控制台 warning/error 为 0。
- `observed`：第二资讯来源、跨日题材历史、交易所级发布时间核验和语义级题材关系仍未接入，因此热点播报和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-30-hotspot-broadcast-topic-link-design.md`、`docs/superpowers/plans/2026-08-30-hotspot-broadcast-topic-link.md`、`apps/desktop/src/feature/market-overview/hotspot-topic-linker.ts`、`apps/desktop/src/feature/market-overview/hotspot-broadcast-archive-presenter.ts`、`apps/desktop/src/feature/market-overview/HotspotBroadcastArchive.svelte`、`tests/features/hotspot-broadcast-topic-link-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 热点播报按需跨日题材归档阶段

- `confirmed`：第 24“热点播报”已把成功、两级缓存命中和可信 stale last-good 同花顺热点快照按上海交易日写入既有 `network-cache.sqlite3`；唯一前缀为 `tonghuashun:hotspot-topic-archive:v1:`，最多保留 31 个日期、TTL 30 天，同日优先保留合法股票覆盖更多或同覆盖观测时间更新的快照。
- `confirmed`：新归档命令空请求只读本地；用户选择尚未归档的历史日期时才复用唯一热点用例读取一次。前端容量 1 Store 合并同日期请求并跳过已归档日期；Presenter 按每个资讯日期复用唯一题材连接器，只按原文明示六位代码和相同上海日期连接来源题材，不从标题、摘要或 AI 推断。
- `confirmed`：页面提供八项摘要、历史日期按需反馈、题材筛选、事件与详情题材，以及资讯归档、当前热点、历史题材归档三份状态。新鲜验证通过 116 项 Node 合同、108 个 Vitest 文件 443 项、Vite 3803 模块、热点归档定向 Rust 9 项、Rust desktop 527 项通过且 1 项既有性能测试忽略、更新核心 11 项、14 个菜单、1186 项登记、2572 个文本编码扫描、rustfmt、架构和差异检查。
- `confirmed`：浏览器 1280×720 页面/组件宽度为 `1280/1280`、`1023/1023`，526×900 为 `526/526`、`251/251`；两种尺寸组件后代横向溢出均为 0，八项摘要、题材筛选和三状态实际渲染，普通网页环境保持真实不可用和零事件，控制台 warning/error 为 0。
- `observed`：第二资讯来源、应用未运行时离线全天采集、交易所级发布时间核验和语义级题材关系仍未接入，因此热点播报与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-30-hotspot-topic-archive-design.md`、`docs/superpowers/plans/2026-08-30-hotspot-topic-archive.md`、`apps/desktop/src-tauri/src/application/use_cases/load_hotspot_topic_archive.rs`、`apps/desktop/src/feature/market-overview/HotspotBroadcastArchive.svelte`、`tests/features/hotspot-topic-archive-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 新闻热点三源个股资讯复审收口

- `confirmed`：新闻一级菜单已形成腾讯财经、东方财富与巨潮公告三源按股工作台。来源记录必须携带并匹配自身股票代码；只有同股、同上海日期且规范化标题完全一致的不同提供方记录才形成多源确认，混合 RFC3339/上海本地时间按真实时刻排序。
- `confirmed`：三路确认空才是 `missing`；一路确认空、两路失败保持 `partial`；三路失败仍返回三份 `unavailable` 来源证据。腾讯/东财解析丢弃会降级，巨潮成功空集合保持 `missing`，缓存命中只使用明确证据。
- `confirmed`：页面只预填默认代码并由用户显式提交，旧标的晚到响应不能覆盖新查询；普通网页环境失败后只显示单一“逐来源状态不可用”。巨潮与前端外链只开放受信 HTTPS 来源域名。
- `confirmed`：新鲜全量证据为根级 Node 合同 116 项、Rust 新闻聚合/并发 9 项、巨潮解析 4 项、空公告分类 1 项、前端链接与 Presenter 5 项、Rust desktop 540 项通过且 1 项既有性能基准忽略、更新核心 11 项、Vite 3810 模块、1200 项文件登记和 2585 个文本编码扫描；最后空态调整后的定向门禁再次通过。
- `confirmed`：浏览器 `1280×720` 页面/工作区宽度为 `1280/1280`、`1023/1023`，`526×900` 为 `526/526`、`251/251`；两种尺寸均无横向溢出，五类筛选、当前标的、事件影响和真实不可用状态存在，控制台 warning/error 为 0。预览保留在 `http://127.0.0.1:1420/news-intelligence`。
- `observed`：全球 7×24 快讯第二来源、逐条行业归因、公告全文语义、市场反应归因和应用未运行时全天采集仍缺失，新闻菜单与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/plans/2026-08-30-multi-source-stock-news.md`、`apps/desktop/src-tauri/src/domain/news/news_workbench.rs`、`apps/desktop/src/feature/news/NewsPage.svelte`、`tests/features/news-workbench-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 公司研究机构资金与筹码证据阶段

- `confirmed`：公司研究新增融资融券日级与股东户数季度两条独立东方财富证据链。融资融券最多保留 30 条，股东户数最多保留 12 条；股票身份、日期、有限数值、重复、排序和容量均严格校验，缺失值保持 `null`，不替换为零。
- `confirmed`：两路各自使用 6 小时内存/用户缓存、规范请求键、同请求去重和独立熔断，复用统一东方财富串行网络门；组合 IPC 并行读取，单源失败不清空另一源，状态保留 `ready/partial/stale/missing/unavailable`，顶层或嵌套错码切片被拒绝。
- `confirmed`：前端容量 2 Store、纯 Presenter 和独立面板已接线；页面展示组合/双来源状态、融资余额、两融余额、股东户数、环比原值和两张记录表，不生成吸筹、出货、利好、利空、买卖建议或目标价。
- `confirmed`：新鲜门禁通过定向 Node 合同、Rust 三组各 5 项、前端 11 项、全量 112 个 Vitest 文件 459 项、Vite 3814 模块构建、Rust desktop 555 项通过/1 项既有性能测试忽略、updater-core 11 项、1221 项文件登记、2606 个文本编码扫描、rustfmt 和项目差异检查。
- `confirmed`：浏览器 `1280×720` 页面/面板为 `1280/1023`，`526×900` 为 `526/251`；两种尺寸无横向溢出，标题、双来源、来源原值、真实不可用和零记录空态均实际渲染，控制台 warning/error 为 0。预览保留在 `http://127.0.0.1:1420/company-research?preview=latest`。
- `observed`：融资融券与股东户数仍为东方财富单来源，第二来源确认和投资解释未完成；公司研究和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-30-company-capital-evidence-design.md`、`docs/superpowers/plans/2026-08-30-company-capital-evidence.md`、`crates/contracts/src/company_capital_evidence.rs`、`apps/desktop/src-tauri/src/application/use_cases/company_capital_evidence.rs`、`apps/desktop/src/feature/company-research/ResearchCapitalEvidencePanel.svelte`、`tests/features/company-capital-evidence-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 公司研究未来限售解禁证据阶段

- `confirmed`：公司研究复用投资日历唯一 `investmentCalendarOfficial` Store 和 `load_investment_calendar_official` IPC，新增按六位股票代码过滤的未来 90 日限售解禁纯投影、容量 2 LRU Store 与独立面板；没有新增 Rust、IPC、网络、数据库、缓存文件、轮询、计时器、依赖或平台专属业务调用。
- `confirmed`：投影保留来源日期、类型、解禁股数、占总股本比例、公告日期和审计字段，坏数值保持缺失；同股请求合并、强刷、跨股晚到、非法代码、容量和 last-good 已覆盖。单一来源有效事项最多为 `partial`，零事项为 `missing`，首次失败为 `unavailable`，同股旧值回退为 `stale`，不生成减持压力、利好利空、买卖建议或目标价。
- `confirmed`：新鲜门禁通过公司解禁 Node 合同、定向 Vitest 10 项、全量 114 个 Vitest 文件 469 项、Vite 3818 模块、Rust desktop 555 项通过且 1 项既有性能测试忽略、updater-core 11 项、14 个菜单、1231 项登记、2616 个文本编码扫描、rustfmt、架构和差异检查。
- `confirmed`：浏览器 `1280×720` 页面/面板宽度为 `1280/1023`，`526×900` 为 `526/251`；两种尺寸无横向溢出，标题、标的 `600519`、真实不可用和零事项空态均实际渲染，控制台 warning/error 为 0。预览保留在 `http://127.0.0.1:1420/company-research?preview=latest`。
- `observed`：第二解禁来源、跨来源确认和投资解释仍缺失，公司研究与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-30-company-unlock-evidence-design.md`、`docs/superpowers/plans/2026-08-30-company-unlock-evidence.md`、`apps/desktop/src/feature/company-research/company-unlock-evidence-projector.ts`、`apps/desktop/src/feature/company-research/company-unlock-evidence-store.ts`、`apps/desktop/src/feature/company-research/ResearchUnlockEvidencePanel.svelte`、`tests/features/company-unlock-evidence-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 公司研究未来公司事项统一时间线阶段

- `confirmed`：公司研究已将财报预约、股东大会、分红除权和限售解禁四类未来 90 日事实合并为独立时间线；统一投影严格校验股票、日期、窗口和稳定身份，最多保留 80 条，取消会议保留但不计入有效待办，坏日期、错码、重复和截断不以默认值修补。
- `confirmed`：容量 2 前端 Store 首次合法加载才懒订阅三条投资日历共享 Store，并复用同页唯一解禁 Store；四路并行、同股合并、强刷、跨股晚到隔离、last-good 和幂等释放均有回归测试，没有新增 Rust、IPC、网络、数据库、缓存文件、计时器、轮询、依赖或平台专属业务调用。
- `confirmed`：统一事项进入研究账本第七段“未来催化”，排在公告和研报待核验事实之前；事项不自动解释为正向催化，十项反方规则计数不变。普通网页环境保持四路真实不可用和零事项，不生成示例记录。
- `confirmed`：新鲜门禁通过全部根级 Node 合同、116 个 Vitest 文件 485 项、Vite 3822 模块、Rust desktop 555 项通过且 1 项既有性能测试忽略、updater-core 11 项、14 个菜单、1241 项登记、2626 个文本编码扫描、rustfmt、架构和项目差异检查。1280x720 与 526x900 实页页面/面板宽度分别为 `1280/1023` 和 `526/251`，无横向溢出，四来源、真实不可用、`600519` 与“未来催化”均渲染，控制台 warning/error 为 0。
- `observed`：四类事项仍各自依赖单一来源，跨来源确认和投资解释未完成，公司研究与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-30-company-upcoming-events-design.md`、`docs/superpowers/plans/2026-08-30-company-upcoming-events.md`、`apps/desktop/src/feature/company-research/company-upcoming-events-projector.ts`、`apps/desktop/src/feature/company-research/company-upcoming-events-store.ts`、`apps/desktop/src/feature/company-research/ResearchUpcomingEventsPanel.svelte`、`tests/features/company-upcoming-events-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 公司研究历史估值分位阶段

- `confirmed`：公司研究新增东方财富 `RPT_VALUEANALYSIS_DET` 五年日级 PE_TTM/PB_MRQ 独立证据链；股票、日期、正有限数值、重复、排序和最多 1300 条容量均严格审计，缺失值不以零、价格反推值或旧交易日值替代。
- `confirmed`：历史序列不阻塞核心研究接口，使用独立按需 IPC、五年单请求、6 小时内存/用户缓存、请求去重、独立熔断和容量 2 前端 Store；公司资本证据 Store 同时复用统一股票证据内核，删除重复 LRU、并发和 last-good 逻辑。
- `confirmed`：前端提供 1/3/5 年窗口与 PE、PB 独立趋势；经验分位按窗口内小于等于当前值的样本占比计算，窗口分别要求至少 120/360/600 个样本和起点后 45 天内覆盖，最新交易日缺值时不向前回填。五年合格事实进入研究账本“估值分位”，十项反方规则不变。
- `confirmed`：全量门禁通过根级 Node 合同、118 个 Vitest 文件 496 项、Vite 3828 模块、Rust desktop 565 项通过/1 项既有性能测试忽略、updater-core 11 项、1259 项文件登记、2644 个文本编码扫描、rustfmt 和差异检查。门禁发现并修复账本指标文件超过 300 行的问题：估值账本转换拆为 40 行独立纯函数，主指标编排器降至 290 行。
- `confirmed`：浏览器 `1280×720` 页面/面板为 `1280/1023`，`526×900` 为 `526/251`；三档窗口逐一切换正确，PE/PB、真实不可用和账本分位均渲染，面板后代无横向溢出，全新标签控制台 warning/error 为 0。预览保留在 `http://127.0.0.1:1420/company-research?preview=latest`。
- `observed`：历史估值仍为东方财富单来源，第二来源交叉确认尚未完成；公司研究和产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-30-company-valuation-history-design.md`、`docs/superpowers/plans/2026-08-30-company-valuation-history.md`、`apps/desktop/src-tauri/src/application/use_cases/company_valuation_history.rs`、`apps/desktop/src/feature/company-research/ResearchValuationHistoryPanel.svelte`、`docs/verification/feature-completion-audit.md`。
### 2026-08-30 个股观察五档盘口阶段

- `confirmed`：个股观察已复用腾讯基础报价同一响应解析买卖五档和来源原生时间；没有新增网络请求、IPC、缓存键、数据库、轮询、计时器、后台任务或依赖。价量必须成对、有限且为正，坏值与缺档保持真实缺口；旧缓存字段通过默认空盘口兼容升级。
- `confirmed`：驾驶舱新增独立盘口证据切片，合法单来源为 `partial`、可信旧缓存为 `stale`、零合法档为 `missing`、无报价为 `unavailable`。来源时间只接受 14 位腾讯原值并规范为上海 `+08:00`，不使用本机时间补齐。
- `confirmed`：独立 Presenter 和面板按卖五至卖一、买一至买五展示；仅完整一侧汇总五档可见量，买一卖一同时合法且未倒挂才计算价差。页面明确该数据不代表交易所完整委托队列，也不包含撤单或逐笔成交。
- `confirmed`：全量门禁通过 119 个 Vitest 文件 500 项、Vite 3831 模块、Rust desktop 570 项通过且 1 项既有性能测试忽略、更新核心 11 项、14 个菜单、1266 项登记和 2651 个文本编码扫描。1280x720 与 526x900 页面/面板分别为 `1280/1021` 和 `526/259`，无横向溢出，控制台 warning/error 为 0；预览保留在 `http://127.0.0.1:1420/a-shares?symbol=600519`。
- `observed`：第二盘口来源、完整委托队列、撤单轨迹和逐笔成交仍缺失，个股观察与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-30-stock-order-book-design.md`、`docs/superpowers/plans/2026-08-30-stock-order-book.md`、`apps/desktop/src-tauri/src/infrastructure/sources/tencent.rs`、`apps/desktop/src/feature/stock-observation/StockOrderBookPanel.svelte`、`tests/features/stock-order-book-contract.test.mjs`。

### 2026-08-30 个股观察 3 秒聚合成交阶段

- `confirmed`：个股观察新增独立腾讯成交时间线与最新页来源链路，最多保留最新页 70 条记录；股票、日期、页号、递增唯一序号、正价格/量/金额、有限涨跌、`B/S/M` 原始方向和交易时段均严格校验，坏行只进入审计，不补零或补时间。
- `confirmed`：应用用例使用独立 5 秒内存/用户缓存、请求去重和成交熔断器；单来源有效值、合法空页、同股旧值和首次失败分别保持 `partial/missing/stale/unavailable`，错股缓存被拒绝。没有新增数据库表、依赖、WebSocket、SSE 或后台常驻任务。
- `confirmed`：独立前端 Store 仅在有订阅、页面可见且股票有效时按用户 5–300 秒偏好自动刷新，休市至少 30 秒，刷新不重叠且跨股晚到隔离。桌面五档与成交双栏，窄屏按盘口、成交、分钟图排列；普通网页环境保持真实不可用和零记录。
- `confirmed`：页面固定声明“3 秒聚合”“不是交易所逐笔”“不含委托/成交编号”和来源方向边界，不把 `B/S/M` 解释为主动买卖或资金流。新鲜门禁通过成交 Rust 12 项、根级 Node 合同、121 个 Vitest 文件 511 项、Vite 3835 模块、Rust desktop 582 项通过/1 项既有性能测试忽略、updater-core 11 项、1282 项登记和 2667 个文本编码扫描。
- `confirmed`：浏览器 `1280×720` 为盘口/成交双栏，`526×900` 为单栏；两种尺寸无页面或成交面板后代横向溢出，边界文案完整，控制台 warning/error 为 0。预览保留在 `http://127.0.0.1:1420/a-shares?symbol=600519`。
- `observed`：当前只接入腾讯公开最新页约 3 秒聚合成交；交易所逐笔、第二成交来源、委托/成交编号、完整委托队列和同刻分钟交叉确认仍缺失，个股观察与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-30-stock-trade-detail-design.md`、`docs/superpowers/plans/2026-08-30-stock-trade-detail.md`、`apps/desktop/src-tauri/src/infrastructure/sources/tencent_trade_detail.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_stock_trade_detail.rs`、`apps/desktop/src/feature/stock-observation/StockTradeDetailPanel.svelte`、`tests/features/stock-trade-detail-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 个股观察事件 K 线阶段

- `confirmed`：个股观察已在分时之后、诊断之前接入独立事件 K 线，复用最多 120 根永久日线和 20 条既有巨潮公告；Rust 合同/纯投影、TypeScript Presenter、SVG 几何、Svelte 面板与样式均独立拆分，没有新增网络、IPC、数据库、计时器、轮询、后台任务或依赖。
- `confirmed`：公告只按上海日期精确映射到相同真实日线；未映射事件保留证据但不移动日期。原生 SVG 展示红涨绿跌蜡烛、成交量和桌面 12/窄屏 3 个事件索引，类别色不表示利好利空，影响方向保持待核验。旧重复公告列表已移除，日线明细仍保留。
- `confirmed`：巨潮解析器拒绝标题中的 Unicode 替换字符；公告缓存键升级为 `cninfo:announcements:v2:{symbol}`，隔离旧未版本化缓存且不删除用户缓存文件。
- `confirmed`：浏览器 1280x720 与 526x900 页面/面板宽度分别为 `1280/1021` 和 `526/259`，顺序正确、无页面横向溢出，控制台 warning/error 为 0；普通网页环境按真实状态显示不可用和零日线。
- `confirmed`：新鲜门禁通过全部根级 Node 合同、123 个 Vitest 文件 518 项、Vite 3839 模块、Rust desktop 585 项通过且 1 项既有性能测试忽略、updater-core 11 项、14 个菜单、1294 项登记、2679 个项目文本编码扫描、rustfmt 和项目差异检查；Vault 验证器及其 5 项单测同时通过。
- `observed`：永久库当前没有可用于该标的的日线，因此非空真实蜡烛和事件标记的浏览器验收仍未完成；非空几何仅由单元测试证明。多源新闻/题材事件、AI 影响方向、因果证据和完整法定交易日历仍缺失，产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-30-stock-event-kline-design.md`、`docs/superpowers/plans/2026-08-30-stock-event-kline.md`、`crates/contracts/src/stock_event_timeline.rs`、`apps/desktop/src-tauri/src/application/use_cases/stock_event_timeline.rs`、`apps/desktop/src/feature/stock-observation/StockEventKlinePanel.svelte`、`tests/features/stock-event-kline-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 个股事件 K 线多源资讯与直接题材阶段

- `confirmed`：事件 K 线在基础驾驶舱确认同一股票后，并行复用既有腾讯、东方财富、巨潮个股资讯和同花顺热点能力。新增前端 Store 容量固定为 2，无计时器、轮询或后台常驻任务；同股请求合并、跨股晚到隔离、单源失败保留另一源，刷新失败按来源保留 last-good 并降为 `stale`。
- `confirmed`：纯投影只接受严格同股资讯和同花顺同股同交易日股票样本中的直接题材。新闻工作台的严格同股同上海日期同规范标题多源字段原样保留，官方公告按受信 URL 或日期加规范标题去重；题材不从标题、公司名、行业或 AI 推断。最新完整证据容量为 80，图中仍只按真实日线同日映射桌面 12 条、窄屏 3 条。
- `confirmed`：面板已展示“永久日线 × 三源资讯 × 直接题材”、四项摘要、三源资讯与当前直接题材状态、核验标签、题材原值、多来源入口和真实空态。多源一致、官方公告与直接题材均不解释为利好利空、买卖建议或因果关系。
- `confirmed`：新鲜验证通过 4 个定向 Vitest 文件 18 项、4 个相关 Node 合同、全量 125 个 Vitest 文件 529 项和全部根级合同、3841 模块生产构建、Rust desktop 585 项通过/1 项既有性能测试忽略、updater-core 11 项、14 个菜单、1301 项文件登记、2686 个文本编码扫描、rustfmt 与项目差异检查。
- `confirmed`：浏览器 `1280x720` 页面/事件面板宽度为 `1280/1021`，`526x900` 为 `526/259`；桌面四列摘要、窄屏两列摘要与单列来源状态实际渲染，两种尺寸无页面或事件面板后代横向溢出，带时间边界重载后的 console warning/error 为 0。预览保留在 `http://127.0.0.1:1420/a-shares?symbol=600519`。
- `observed`：普通网页预览无 Tauri IPC，永久库也没有当前标的可用日线，所以实页保持零日线、零事件的真实不可用状态，未注入假数据展示蜡烛或事件。AI 影响方向、因果证据、历史题材自动加载、第二热点来源和完整法定交易日历仍缺失；个股观察与产品总体继续保持 `partial`。本阶段未生成发布产物、未修改参考项目、未执行 Git 写操作。
- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-30-stock-event-multisource-evidence-design.md`、`docs/superpowers/plans/2026-08-30-stock-event-multisource-evidence.md`、`apps/desktop/src/feature/stock-observation/stock-event-evidence-projector.ts`、`apps/desktop/src/feature/stock-observation/stock-event-evidence-store.ts`、`apps/desktop/src/feature/stock-observation/StockEventKlinePanel.svelte`、`tests/features/stock-event-multisource-evidence-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 个股观察事件影响研究阶段

- `confirmed`：选中事件新增独立影响研究链路。Rust 纯域按上海交易日、真实前收和最多前后五根日线冻结同日/后 1/3/5 日反应与五日量比；盘后事件、缺前收、缺后续窗口和单源证据保留限制，不授予方向资格。冻结快照使用 30 分钟双层缓存并重验身份；AI 仅由用户显式点击，严格引用冻结证据并使用 7 天合格解释缓存，失败不覆盖事实。
- `confirmed`：前端新增类型化 IPC Client、容量 2 Store、纯 Presenter、独立影响面板与样式；同键冻结和同快照 AI 请求合并，事件切换晚到隔离，AI 失败保留事实。普通浏览器不伪造 Tauri 结果，事实与 AI 均显示真实不可用/未冻结状态，生成按钮保留为禁用态。
- `confirmed`：新鲜全量门禁通过根级 `pnpm test`（128 个 Vitest 文件、542 项）、Vite 3846 模块生产构建、Rust workspace 离线测试（desktop 617 项通过、1 项既有性能测试忽略；updater-core 11 项通过）、格式、架构登记、UTF-8/乱码扫描和项目差异检查。浏览器桌面 `1280x720` 页面宽度/滚动宽度为 `1280/1280`，窄屏 `526x900` 为 `526/526`；影响面板事实/AI 双栏切单列，标题、真实不可用状态和禁用按钮可见，控制台 warning/error 为 0。
- `observed`：普通网页验收未具备 Tauri IPC 和可用永久日线，因此没有非空实页反应数字或 AI 解释；交易所事件/逐笔时间、复权、基准超额收益、完整交易日历、第二资讯/行情来源和因果识别仍是缺口。个股观察与产品总体继续保持 `partial`。本阶段未生成发布产物，未修改参考项目，未执行 Git 写操作。
- 来源：`docs/superpowers/plans/2026-08-30-stock-event-impact-research.md`、`crates/contracts/src/stock_event_impact.rs`、`apps/desktop/src-tauri/src/domain/market/stock_event_impact.rs`、`apps/desktop/src-tauri/src/application/use_cases/generate_stock_event_explanation.rs`、`apps/desktop/src/feature/stock-observation/StockEventImpactPanel.svelte`、`tests/features/stock-event-impact-research-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 公告全文语义证据阶段收尾

- `confirmed`：公告正文仅在用户点击单条公告的“读取正文”后按需加载；首屏、公告列表和事件 K 线不预取。来源层只接受 `https` 的 `cninfo.com.cn` 域名族，响应体上限 2 MiB，支持 UTF-8/GBK HTML 或纯文本清洗，PDF、二进制和不可核验编码保持 `unavailable` 并保留受信原文入口。
- `confirmed`：正文快照绑定股票代码、公告身份、标题、发布时间、原文 URL、内容类型和规范化文本 SHA-256；用例读取缓存前重复校验身份和受信 URL，复用现有两级缓存、请求去重与熔断内核，缓存 TTL 固定 30 分钟，网络失败或熔断时同公告 last-good 降为 `stale`，错公告内容拒绝显示。
- `confirmed`：HTML 正文在规范化前移除 `script`/`style` 块，并解码常见命名、十六进制和十进制数值实体；实现使用 Rust 标准库有界扫描，不新增依赖，不改变 2 MiB 上限与正文哈希口径。
- `confirmed`：前端 typed IPC、容量 2 Store 和独立正文面板已挂载到公告验证与事件影响两处；正文失败不清除事件事实，同键请求合并，跨公告晚到响应隔离，正文内容局部换行且没有新增计时器或轮询。普通网页没有 Tauri IPC 时保持真实 `missing/unavailable`，不注入正文或示例数据。
- `confirmed`：定向公告合同、Rust 来源/用例测试和 Store 测试通过；全量 `pnpm test` 为 129 个 Vitest 文件、545 项通过，Vite 构建完成 3850 个模块；`cargo test --workspace --offline` 为 desktop 629 项通过、1 项既有性能测试忽略，updater-core 11 项通过；`cargo fmt --all -- --check`、架构登记（1350 项）、UTF-8/乱码扫描（2742 个文本文件）和 `git diff --check` 均通过。
- `confirmed`：浏览器实页在 `1280x720` 与 `526x900` 验收，页面宽度/滚动宽度分别为 `1280/1280` 与 `526/526`，个股事件面板分别约 `1023` 与 `251`，真实不可用状态、正文按需边界和长文本换行规则实际渲染；视口已恢复默认，实时预览保留在 `http://127.0.0.1:1420/a-shares?symbol=600519`。
- `observed`：普通网页环境无法证明远程巨潮正文的真实非空读取；公告语义结构化核验、第二正文来源、公告与市场反应归因仍未接入，新闻热点、个股观察和产品总体继续保持 `partial`。本阶段未生成 EXE、安装包、便携包或 ZIP，未修改参考项目，未执行 Git 提交或推送。
- 来源：`docs/superpowers/specs/2026-08-30-announcement-full-text-design.md`、`docs/superpowers/plans/2026-08-30-announcement-full-text.md`、`crates/contracts/src/announcement_detail.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/cninfo_announcement_detail.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_announcement_detail.rs`、`apps/desktop/src/feature/news/AnnouncementDetailPanel.svelte`、`tests/features/announcement-full-text-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 公告正文直接线索阶段

- `confirmed`：公告正文成功读取后，面板从同一正文快照派生独立“正文直接线索”区块，只展示正文原文直接出现的股票代码、合法日期、金额文本和 13 类明确章节标题；代码最多 8 条、日期最多 12 条、金额最多 12 条，日期规范化并按首次出现顺序去重。
- `confirmed`：线索解析是纯 TypeScript 函数，不访问网络、IPC、数据库、AI 或计时器，不生成方向、评分、利好利空、投资建议或因果结论；正文失败、线索为空和跨公告晚到只影响线索区块，不清除其他事实。
- `confirmed`：新增 Vitest 行为测试、Node 架构合同及 YAML/Markdown 双登记，根级 `pretest` 已纳入该合同；产品和新闻/个股工作区继续保持 `active/partial`。
- `observed`：普通网页预览无 Tauri IPC，无法证明远程巨潮正文真实非空线索；公告语义一致性、第二正文来源和市场反应归因仍未接入。本阶段未生成发布产物，未修改参考工程，未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-30-announcement-full-text-design.md`、`docs/superpowers/plans/2026-08-30-announcement-full-text.md`、`apps/desktop/src/feature/news/announcement-detail-semantics.ts`、`apps/desktop/src/feature/news/announcement-detail-semantics.test.ts`、`tests/features/announcement-detail-semantics-contract.test.mjs`。

### 2026-08-30 个股观察第二行情来源交叉核验

- `confirmed`：个股驾驶舱新增 `StockQuoteConfirmationEvidence`，保存腾讯主源与东方财富第二源的紧凑现价、股票身份、交易日、观测时间和各自 `ready/partial/stale/missing/unavailable` 状态；没有使用假价格或本机时间填补缺口。
- `confirmed`：第二行情独立用例复用 `eastmoney:intraday:{symbol}` 两级缓存、统一请求去重器和东方财富熔断器，10 秒 TTL；不新增轮询、常驻任务、数据库表或第三方依赖。共享价格核验函数由市场详情和个股观察共同复用。
- `confirmed`：定向 Rust 合同/用例测试、共享核验测试、个股 Presenter 测试和根级 Node 合同通过；生产构建完成 3855 个模块；文件登记、设计和实施计划已同步。
- `observed`：普通网页预览无 Tauri IPC，双来源非空价格无法在浏览器页面证明，当前仍显示真实不可用状态。第二盘口、第二成交、原子同刻快照、交易所逐笔时刻、第三来源裁决和完整跨源一致性仍是缺口，产品继续保持 `active/partial`。
- 来源：`docs/superpowers/specs/2026-08-30-stock-quote-confirmation-design.md`、`docs/superpowers/plans/2026-08-30-stock-quote-confirmation.md`、`crates/contracts/src/stock_quote_confirmation.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_stock_quote_confirmation.rs`、`apps/desktop/src/feature/shared/stock-price-confirmation.ts`、`apps/desktop/src/feature/stock-observation/StockQuoteConfirmationPanel.svelte`、`tests/features/stock-quote-confirmation-contract.test.mjs`。

### 2026-08-30 个股观察驾驶舱并发编排阶段

- `confirmed`：基础腾讯行情返回后，东方财富第二行情、巨潮公告和本地永久日线读取改为并发编排；本地 SQLite 日线读取与股票目录写入统一移入 `spawn_blocking`，不占用异步命令线程。
- `confirmed`：并发改造继续复用既有缓存、请求去重、熔断和真实状态信封，不新增网络来源、轮询、数据库表或第三方依赖；任一支路失败只追加对应警告，不清除其他支路的真实结果。
- `confirmed`：新增驾驶舱并发架构合同，要求 `load_stock_cockpit_for_state` 保留并发等待和阻塞线程池边界；定向合同、全量 `pnpm test`（131 个 Vitest 文件、550 项）和 Rust 定向测试通过，`cargo fmt --all -- --check` 与 `git diff --check` 通过。
- `observed`：普通网页预览仍无 Tauri IPC，无法从浏览器直接测量三路真实数据的并发延迟；第二盘口、第二成交、原子同刻快照和完整跨源一致性仍未关闭，个股观察与产品总体保持 `partial`。

- 来源：`apps/desktop/src-tauri/src/commands/core_menu.rs`、`tests/features/stock-quote-confirmation-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 个股观察成交分钟级双来源核验

- `confirmed`：复用驾驶舱既有东方财富分时缓存、请求去重和熔断，在第二源紧凑观测中传播最后真实分钟点 `latestMinute`；不新增网络源、请求、轮询、数据库或依赖。
- `confirmed`：新增纯 TypeScript 核验器和独立面板，将腾讯最新合法 3 秒聚合成交与东方财富分钟 OHLC 点按股票、交易日和分钟比较，明确区分 `confirmed/divergent/time_separated/session_mismatch/primary_only/secondary_only/unavailable`，缺字段与错股保持审计。
- `confirmed`：页面不把分钟点解释为交易所逐笔、Level-2、委托编号或主动买卖方向；普通网页无 Tauri IPC 时继续显示真实不可用状态。新增计划、生产文件和架构合同已同步登记。
- `observed`：原子同刻快照、第二盘口、交易所逐笔时刻、完整委托队列和第三来源裁决仍未接入，个股观察和产品总体保持 `partial`。本阶段未生成发布包，未修改参考工程，未执行 Git 写操作。

- 来源：`docs/superpowers/plans/2026-08-30-stock-trade-confirmation.md`、`crates/contracts/src/stock_quote_confirmation.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_stock_quote_confirmation.rs`、`apps/desktop/src/feature/stock-observation/stock-trade-confirmation.ts`、`apps/desktop/src/feature/stock-observation/StockTradeConfirmationPanel.svelte`、`tests/features/stock-trade-confirmation-contract.test.mjs`。

### 2026-08-30 AI+选股冻结候选解释阶段

- `confirmed`：AI+选股单只候选解释新增独立 Rust 领域校验、应用用例、Tauri 命令、TypeScript 客户端、容量 2 Store 和解释面板。请求精确绑定服务端重验后的冻结 `snapshotId`、六位候选代码和完整 `evidenceIds`；模型严格 JSON 输出必须带冻结引用，交易指令和确定性涨跌承诺会被拒绝。
- `confirmed`：解释结果使用七天内存/用户缓存，缓存读取重新校验候选身份、证据集合和模型输出；同键请求复用既有请求去重、单并发 AI 网络和 60 秒熔断。配置缺失、缓存失效或普通网页无 Tauri IPC 时保持真实 `unavailable`，不生成假解释。
- `confirmed`：AI+选股候选操作已替换为独立冻结证据与 AI 解释面板，解释失败不会清除规则事实；新增文件已同步登记到 YAML/Markdown 双注册表，根级 Node 136 个 Vitest 文件 561 项、Rust workspace 642 项通过，生产构建、架构、编码、格式和差异检查通过。预览保持在 `http://127.0.0.1:1420/?workspace=ai-selection`。
- `observed`：普通浏览器预览没有桌面 IPC 与有效 AI 凭据，无法证明远程模型非空返回；跨日回放、第二行情来源和长期效果归因仍未关闭，AI+选股与产品总体保持 `partial`。本阶段未生成 EXE/安装包/ZIP，未修改参考工程，未执行 Git 写操作。
- 来源：`docs/superpowers/specs/2026-08-30-ai-selection-explanation-design.md`、`docs/superpowers/plans/2026-08-30-ai-selection-explanation.md`、`apps/desktop/src-tauri/src/domain/selection/ai_selection_explanation.rs`、`apps/desktop/src-tauri/src/application/use_cases/generate_ai_selection_explanation.rs`、`apps/desktop/src-tauri/src/commands/ai_selection_explanation.rs`、`apps/desktop/src/feature/market-overview/AiSelectionExplanationPanel.svelte`、`tests/features/ai-selection-explanation-contract.test.mjs`。

### 2026-08-30 AI+选股跨日回放阶段

- `confirmed`：AI+选股新增跨日实际回放链路，按冻结 `snapshotId` 与交易日从本地永久 SQLite 只读读取候选后续第 1、5、20 个有效日收盘，并计算 20 日最大有利/不利价格变化；数据库读取在阻塞线程池执行，不增加轮询或网络请求。
- `confirmed`：回放缓存键按冻结身份和规范化 `maxCandidates` 隔离，缓存命中前重验来源快照、交易日、候选代码顺序和覆盖率；冻结身份错配、缓存篡改和数据库损坏均保持真实 `unavailable`，不泄漏错误结果。
- `confirmed`：领域、数据库、用例、前端 client/store/presenter 和面板均按单一职责拆分，新增文件已登记到 YAML/Markdown 双注册表；候选截断顶层缺失字段仅按实际返回集合计算，TDD 回放定向测试通过。
- `confirmed`：冻结成功后同步写入独立 `ai-selection-freeze-archive:v1:{snapshotId}` 归档，TTL 30 天、最多 128 条；热缓存过期后可从用户缓存库只读恢复并重新校验冻结身份，归档裁剪不触碰业务数据，定向测试覆盖写入、恢复和容量上限。
- `observed`：完整法定交易日历、第二行情来源和长期效果归因仍未接入；普通网页预览没有 Tauri IPC 与永久日线，只能验证真实不可用状态。AI+选股与产品总体保持 `partial`，本阶段未生成 EXE、安装包或 ZIP，未修改参考工程，未执行 Git 写操作。

- 来源：`docs/superpowers/specs/2026-08-30-ai-selection-replay-design.md`、`docs/superpowers/plans/2026-08-30-ai-selection-replay.md`、`apps/desktop/src-tauri/src/application/use_cases/replay_ai_selection.rs`、`apps/desktop/src/feature/market-overview/AiSelectionReplayPanel.svelte`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 交易日历领域边界阶段

- `confirmed`：新增跨平台纯 Rust `TradingCalendar`，支持周末、注入的已核验休市日、临时开市日和跨日期查询；事件影响、分钟证据与 AI+选股回放保留旧签名并提供带日历参数的变体。
- `confirmed`：自定义休市日不会被映射为市场反应、分钟锚点或回放有效日；日线源包含休市记录时明确拒绝/标记 `daily_bars_calendar`，不静默修正或填充。
- `observed`：官方完整法定交易日历来源与跨重启同步尚未接入，默认仍仅排除周末；相关工作区与产品总体保持 `partial`。本阶段未生成 EXE、安装包或 ZIP，未修改参考工程，未执行 Git 写操作。

- 来源：`docs/superpowers/plans/2026-08-30-trading-calendar.md`、`apps/desktop/src-tauri/src/domain/market/trading_calendar.rs`、`apps/desktop/src-tauri/src/domain/market/stock_event_impact.rs`、`apps/desktop/src-tauri/src/domain/market/event_minute_evidence.rs`、`apps/desktop/src-tauri/src/domain/selection/ai_selection_replay.rs`。

### 2026-08-30 权威交易日历来源接入阶段

- `confirmed`：官方日历缓存命中后重新计算规范化 SHA-256；内存或持久缓存被篡改时不会进入业务层。
- `confirmed`：Tauri `CoreMenuState` 保存最近一次来源校验通过的日历，事件影响冻结和 AI+选股跨日回放命令优先注入该日历；休市、临时开市及权威窗口外日期保持保守未知边界。
- `confirmed`：未配置来源、来源失败或窗口不在官方快照范围时继续保留真实 `unavailable/stale/partial`，前端客户端只在用户配置来源地址后请求固定前后 180 天窗口，没有硬编码未来节假日或伪造数据。
- `confirmed`：成功快照写入独立持久缓存，后续启动按新鲜度和规范化 SHA-256 重验后恢复；新增客户端与测试已登记到 YAML/Markdown 双注册表，根级日历合同覆盖启动条件、窗口和 IPC 参数。
- `confirmed`：本轮收尾门禁通过 1431 项文件登记、14 个菜单源码清单、2826 个项目文本文件 UTF-8 扫描、Rust workspace 671 项通过且 1 项既有性能测试 ignored、前端 140 个 Vitest 文件 569 项通过、3871 模块 Vite 生产构建、rustfmt 和 `git diff --check`；本地预览服务 PID 21108 返回 HTTP 200。
- `observed`：默认官方端点、跨来源裁决和后台自动同步仍待补齐；普通网页预览已保持在 `http://127.0.0.1:1420/?workspace=ai-selection`，无 Tauri IPC 时显示真实不可用状态。

- 来源：`apps/desktop/src-tauri/src/application/use_cases/load_trading_calendar.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_trading_calendar_tests.rs`、`apps/desktop/src-tauri/src/commands/trading_calendar.rs`、`apps/desktop/src-tauri/src/commands/core_menu.rs`、`apps/desktop/src/shared/calendar/trading-calendar-client.ts`、`apps/desktop/src/shared/calendar/trading-calendar-client.test.ts`、`apps/desktop/src/app/App.svelte`、`tests/features/trading-calendar-contract.test.mjs`、`docs/superpowers/specs/2026-08-30-authoritative-trading-calendar-design.md`。

### 2026-08-30 SSE 年度休市来源阶段

- `confirmed`：默认交易日历来源切换为上海证券交易所官方年度休市安排页面；JSON 解析失败时仅对 SSE 官方域名回退到年度 HTML 解析，用户显式配置地址仍优先。
- `confirmed`：来源层限制 512 KiB 响应，复用 UTF-8/GB18030 解码，按请求窗口选择相交的 `YYYY年休市安排`，解析单日/区间休市条款并生成公告年份工作日集合；“起照常开市”不会被误计为休市。
- `confirmed`：请求窗口限制 0–370 天；无年份交集、坏编码/日期、无休市证据和超限响应均拒绝，多年度页面只选择相交年份，公告年份外保持未知；快照重算 SHA-256，状态为 `partial` 并记录 `calendar_year_coverage`。
- `confirmed`：新增 SSE 来源夹具 8 项定向测试，覆盖窗口、年度选择、实体、GB18030、编码、回退边界和身份哈希；双源裁决新增 2 项 Rust 测试。最终门禁通过 Rust workspace 679 项（1 项既有性能测试 ignored）、前端 Vitest 140 个文件/570 项、Vite 3,871 个模块、14 菜单源码清单、双注册表 1,433 项、项目文本 UTF-8 扫描 2,830 个文件、Vault 校验、rustfmt 和 `git diff --check`；源码职责已登记到 YAML/Markdown 双注册表，参考工程仍只读。
- `observed`：跨交易所裁决、跨年度自动合并、临时开市公告和后台同步仍未接入；普通网页预览无 Tauri IPC，事件影响、AI 回放和产品总体继续保持 `partial`。本阶段未生成发布包，未执行 Git 写操作。

- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`docs/superpowers/specs/2026-08-30-sse-trading-calendar-design.md`、`docs/superpowers/plans/2026-08-30-sse-trading-calendar.md`、`apps/desktop/src-tauri/src/infrastructure/sources/official_trading_calendar.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/official_trading_calendar_tests.rs`、`apps/desktop/src-tauri/src/commands/settings.rs`、`apps/desktop/src/shared/settings/user-settings-types.ts`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 交易日历双源严格裁决边界阶段

- `confirmed`：跨平台领域层新增 `adjudicate_snapshot_pair`/`CalendarConsensus`，严格验证两份不同官方快照的市场、窗口、公式版本、日期集合互斥和 SHA-256；任何冲突、重复或身份复用均拒绝，不做多数投票或静默补齐。
- `confirmed`：裁决结果保留主快照原始事实，同时记录排序后的来源 ID/URL，作为未来接入深圳官方日历端点的统一防护边界；新增 2 项 Rust 测试、根级日历合同和双注册表职责更新。
- `observed`：第二官方网络端点尚未接入，因此默认 SSE 年度来源仍为 `partial`，跨年度合并、临时开市公告和后台同步仍是下一步缺口；未生成发布包、未修改参考工程、未执行 Git 写操作。

- 来源：`task:01a03785-a8a0-7a42-88d4-836458a08fb1`、`apps/desktop/src-tauri/src/domain/market/trading_calendar.rs`、`apps/desktop/src-tauri/src/domain/market/trading_calendar_tests.rs`、`tests/features/trading-calendar-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 深圳证券交易所官方交易日历接入阶段

- `confirmed`：新增深圳证券交易所逐月官方来源 `monthList?month=YYYY-MM`；年度 12 个月并发读取，单月响应上限 512 KiB，解析结果必须覆盖公告年份全部 365/366 个自然日。
- `confirmed`：来源层校验月份归属、ISO 日期、重复日期、`jybz` 标记和年度完整覆盖；工作日 `jybz=0` 记为闭市，周末 `jybz=1` 单独记为临时开市，普通周末不重复计入闭市集合；快照重新计算 SHA-256。
- `confirmed`：交易日历用例现并发读取 SSE/SZSE，两个来源使用独立缓存前缀与熔断器，来源 URL 哈希参与缓存键；双源成功后严格调用 `adjudicate_snapshot_pair`，任一失败、覆盖不足或冲突均保留真实主/次源事实并降级，不投票、不拼接、不静默补齐。
- `confirmed`：定向 Rust 交易日历测试 26 项、Node 交易日历合同、文件登记和格式检查通过；文档与项目记忆已同步，参考项目保持只读，未生成发布包、未执行 Git 提交或推送。
- `confirmed`：本阶段收尾全量门禁通过：Rust workspace 686 项通过、1 项既有性能测试忽略；前端 Vitest 140 个文件/570 项通过；Vite 生产构建完成 3,871 个模块；文件登记 1,435 项、项目文本编码扫描 2,832 个文件、`cargo fmt --all -- --check`、`git diff --check` 和 Vault 校验均通过。
- `confirmed`：已发布年度的跨年窗口可由 SSE 页面年度段和 SZSE 逐月年度集合分别合并；缺少任一涉及年度公告时仍拒绝并保持未知，不猜测未来节假日。
- `observed`：交易所临时公告、后台自动同步和完整法定日历覆盖未完成。普通网页预览无 Tauri IPC，继续显示真实 `unavailable/partial` 边界，事件影响、AI 回放和产品总体保持 `partial`。

- 来源：`docs/superpowers/plans/2026-08-30-calendar-cross-source.md`、`apps/desktop/src-tauri/src/infrastructure/sources/szse_trading_calendar.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/szse_trading_calendar_tests.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_trading_calendar.rs`、`docs/verification/feature-parity-matrix.md`、`docs/verification/data-source-matrix.md`、`docs/verification/feature-completion-audit.md`。

### 2026-08-30 当前工作区收尾复核

- `confirmed`：跨年度日历阶段收尾后，Vite 生产构建转换 3,871 个模块；前端全量测试 140 个 Vitest 文件/570 项通过，Rust workspace 688 项通过、1 项既有性能测试忽略。
- `confirmed`：文件登记 1,435 项、项目文本 UTF-8/乱码扫描 2,832 个文件、rustfmt、`git diff --check` 和 Vault 验证器通过；参考工程保持只读，未执行 Git 写操作，未生成 EXE/安装包/ZIP。
- `confirmed`：个股观察预览在 `1280x720` 和 `526x900` 均无页面横向溢出，控制台 warning/error 为 0；普通网页没有 Tauri IPC 时，成交分钟级双来源核验保持真实不可用，不填充假数据。
- `observed`：交易所临时公告、后台自动同步、交易所逐笔成交、原子同刻多源快照和完整因果归因仍为缺口；产品保持 `active/partial`。

- 来源：`docs/superpowers/plans/2026-08-30-calendar-cross-source.md`、`docs/superpowers/plans/2026-08-30-stock-quote-confirmation.md`、`apps/desktop/src/feature/stock-observation/StockTradeConfirmationPanel.svelte`、`tests/features/stock-trade-confirmation-contract.test.mjs`。

### 2026-08-30 交易日历生命周期刷新收尾

- `confirmed`：交易日历生命周期控制器已接入应用启动、重新获得焦点、页面可见性恢复和网络恢复；并发事件共享同一 Promise，停止时移除监听器，不增加轮询、定时器、后台常驻任务或额外来源。
- `confirmed`：设置读取与日历加载通过注入函数进入 `apps/desktop/src/shared/calendar/calendar-lifecycle.ts`；`App.svelte` 只负责启动/停止，业务层不直接调用 Tauri、Windows 或 macOS API。交易日历合同已从旧的 App 内嵌配置判断同步为新的生命周期边界。
- `confirmed`：本轮门禁为根级 `pnpm test` 141 个 Vitest 文件/573 项、Vite 3,872 模块、Rust workspace 688 项通过且 1 项既有性能测试忽略、文件登记 1,440 项、编码扫描 2,837 个文本文件、rustfmt、差异检查和 Vault UTF-8 校验通过。
- `confirmed`：本地预览保持 `http://127.0.0.1:1420/a-shares?symbol=600519`；普通网页无桌面 IPC 时继续显示真实 `unavailable/partial`，未生成发布包、未修改参考工程、未执行 Git 写操作。
- `observed`：交易所临时公告、后台日历自动同步、交易所逐笔成交、原子同刻多源快照和完整因果归因仍是后续缺口，项目状态继续为 `active/partial`。

- 来源：`docs/superpowers/specs/2026-08-30-calendar-lifecycle-refresh-design.md`、`docs/superpowers/plans/2026-08-30-calendar-lifecycle-refresh.md`、`apps/desktop/src/shared/calendar/calendar-lifecycle.ts`、`apps/desktop/src/shared/calendar/calendar-lifecycle.test.ts`、`tests/features/calendar-lifecycle-contract.test.mjs`、`tests/features/trading-calendar-contract.test.mjs`。

### 2026-08-30 SSE 年度临时开市事实

- `confirmed`：SSE 年度休市页面解析器会把条款中明确写出的周末“照常开市/临时开市”日期放入 `adHocOpenDates` 并纳入交易日集合；工作日常规开市日期不进入临时集合，休市与临时开市冲突拒绝快照。
- `confirmed`：跨年度解析沿用相同的周末过滤和冲突校验，快照身份哈希包含临时开市事实；来源回归测试与交易日历合同通过。
- `observed`：独立临时公告流、公告撤回/修订追踪和后台自动同步仍未接入；项目继续保持 `active/partial`，未生成发布包、未修改参考工程、未执行 Git 写操作。

- 来源：`docs/superpowers/plans/2026-08-30-sse-trading-calendar.md`、`apps/desktop/src-tauri/src/infrastructure/sources/official_trading_calendar.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/official_trading_calendar_tests.rs`、`tests/features/trading-calendar-contract.test.mjs`、`docs/verification/data-source-matrix.md`。

### 2026-08-30 个股观察第二盘口来源交叉核验阶段

- `confirmed`：个股驾驶舱在腾讯五档之外按需并发读取新浪公开五档，独立使用 5 秒两级缓存、请求去重和新浪专属熔断；原腾讯五档证据不被覆盖，失败只降级新浪支路。
- `confirmed`：前端新增独立盘口双源合同、Presenter 和面板，固定卖五至买五逐档展示两来源价格/数量与一致性；只有同股票、观测相差不超过 5 秒、十档价量全部一致才标记 `ready`，否则保留 `partial/stale/unavailable`。
- `confirmed`：定向 Rust 合同/来源/用例测试、Vitest Presenter 测试、Node 架构合同、根级 Vitest 143 个文件/578 项、Rust workspace 699 项通过且 1 项既有性能测试忽略、Vite 3,879 模块构建、格式/架构/编码/差异检查通过；源码已登记到项目双注册表（1,464 项），预览继续使用 `http://127.0.0.1:1420/`。
- `observed`：两来源不构成交易所原子同刻、完整委托队列、撤单轨迹、逐笔成交、成交编号或主动买卖方向；交易所逐笔时刻、第三来源裁决和完整队列仍未接入，产品保持 `active/partial`。本阶段未生成发布包，未修改参考工程，未执行 Git 写操作。

- 来源：`docs/superpowers/plans/2026-08-30-stock-order-book-cross-confirmation.md`、`crates/contracts/src/stock_order_book_confirmation.rs`、`apps/desktop/src-tauri/src/infrastructure/sources/sina_order_book.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_stock_order_book_confirmation.rs`、`apps/desktop/src/feature/stock-observation/StockOrderBookConfirmationPanel.svelte`、`tests/features/stock-order-book-cross-confirmation-contract.test.mjs`。

### 2026-08-30 个股驾驶舱统一刷新阶段

- `confirmed`：新增 `apps/desktop/src/feature/stock-observation/stock-cockpit-store.ts`，作为 `load_stock_cockpit` 的单一前端入口；它负责同股票请求去重、响应股票身份校验、交易时段单次刷新调度、页面隐藏暂停、共享刷新偏好和 `last-good -> stale` 降级。
- `confirmed`：`StockObservationPage.svelte` 已移除基础驾驶舱的直接 IPC 调用，订阅 Store 后自动更新报价、五档、双源核验、诊断和日线。研究证据仍由页面独立低频请求，已冻结研究覆盖层不会被基础行情刷新清除，也不会因高频刷新重复调用。
- `confirmed`：页面隐藏时选择标的不会发起网络请求，重新可见时 Store 恢复读取；页面订阅回调只启动一次事件/研究证据加载。未新增网络源、数据库表、第三方依赖、后台常驻任务或重复驾驶舱计时器。
- `confirmed`：定向 Store 测试 4 项、既有个股 Store 回归 19 项、个股架构合同、文件登记 1,466 项和 `pnpm build`（Vite 3,880 模块）通过；项目内计划为 `docs/superpowers/plans/2026-08-30-stock-cockpit-refresh.md`。
- `observed`：普通网页预览无 Tauri IPC，仍显示真实 `unavailable/partial`；交易所逐笔成交、原子同刻多源快照和后台来源覆盖仍未关闭。本阶段未生成 EXE、安装包或 ZIP，未修改参考项目，未执行 Git 写操作。

- 来源：`docs/superpowers/plans/2026-08-30-stock-cockpit-refresh.md`、`apps/desktop/src/feature/stock-observation/stock-cockpit-store.ts`、`apps/desktop/src/feature/stock-observation/StockObservationPage.svelte`、`apps/desktop/src/feature/stock-observation/stock-cockpit-store.test.ts`、`tests/features/stock-observation-contract.test.mjs`。

### 2026-08-30 交易日历后台再同步阶段

- `confirmed`：`calendar-lifecycle.ts` 在应用持续运行期间按默认 6 小时使用单次 `setTimeout` 重新核验已配置的官方日历；刷新完成后才安排下一次，焦点、联网与重新可见事件共享同一个 in-flight Promise。
- `confirmed`：官方日历两级缓存 TTL 已调整为 6 小时，与后台再同步周期一致，避免定时触发长期命中 7 天旧缓存；来源失败仍保留同窗口 stale 快照。
- `confirmed`：页面隐藏时不启动或执行日历请求，隐藏和停止会取消待执行计时器并移除监听器；无官方来源地址时不安排后台任务，失败继续沿用既有缓存的 `stale/unavailable` 状态。
- `confirmed`：定向生命周期测试与 Node 合同已覆盖后台调度、并发合并、隐藏暂停、停止清理和平台解耦；新增计划与生产/测试文件已登记到双注册表。
- `observed`：独立交易所临时公告流、跨重启自动同步和未发布年度覆盖仍未完成，项目保持 `active/partial`；本阶段未生成发布包、未修改参考项目、未执行 Git 写操作。

- 来源：`docs/superpowers/plans/2026-08-30-calendar-background-refresh.md`、`apps/desktop/src/shared/calendar/calendar-lifecycle.ts`、`apps/desktop/src/shared/calendar/calendar-lifecycle.test.ts`、`tests/features/calendar-lifecycle-contract.test.mjs`。

### 2026-08-30 交易所临时公告阶段

- `confirmed`：新增独立交易所临时公告合同、严格 SSE/SZSE HTTPS 解析器、6 小时两级缓存用例和领域叠加；缓存使用专属前缀，最多保留 8 个窗口，支持跨重启恢复、stale-if-error、请求去重与熔断。
- `confirmed`：临时开市日期同时进入 `adHocOpenDates` 与 `tradingDates`，临时休市从交易集合移除并进入 `closedDates`；撤回记录只参与快照身份，不改变日历；基线快照始终保持不变。
- `confirmed`：设置、客户端和生命周期支持可选 `officialTradingCalendarNoticeUrl`，默认空值；同一刷新周期只发起一次 `load_trading_calendar` IPC，桌面命令在基础双源裁决后叠加公告。
- `observed`：具体公告端点仍需用户配置并完成官方来源验证，未硬编码未经核实地址；普通网页预览继续显示真实 `unavailable/partial`，未生成 EXE/安装包/ZIP，未修改参考项目，未执行 Git 写操作。

- 来源：`docs/superpowers/specs/2026-08-30-temporary-trading-notices-design.md`、`docs/superpowers/plans/2026-08-30-temporary-trading-notices.md`、`apps/desktop/src-tauri/src/application/use_cases/load_trading_calendar_notices.rs`、`apps/desktop/src-tauri/src/commands/trading_calendar.rs`、`apps/desktop/src/shared/calendar/trading-calendar-client.ts`。

### 2026-08-30 新闻事件状态与外链安全边界复核

- `confirmed`：新闻工作台切换股票、提交无效代码或选择另一条新闻时，统一清除旧事件影响信封；未选择事件为 `missing`，读取中的新事件不展示旧标的证据，序列号仍隔离晚到响应。
- `confirmed`：事件影响、公告交叉验证和公告正文三个前端面板统一复用 `trustedNewsSourceUrl`，只允许提供方对应的 HTTPS 受信域名后调用外链，不再直接打开未经校验的 URL。
- `confirmed`：新增 `news-event-impact-state.ts` 及 Vitest 1 项，新闻工作台契约、相关 Vitest 4 项、Rust 新闻用例 12 项、双注册表和 Vite 3,881 模块构建均通过；普通预览继续保留真实 `unavailable/partial`。
- `observed`：新闻第二资讯来源、逐条行业归因、公告正文完整语义结构化和市场反应归因仍是产品级缺口，项目总体保持 `active/partial`；参考项目只读，未生成发布包，未执行 Git 写操作。

- 来源：`apps/desktop/src/feature/news/news-event-impact-state.ts`、`apps/desktop/src/feature/news/news-event-impact-state.test.ts`、`apps/desktop/src/feature/news/NewsPage.svelte`、`apps/desktop/src/feature/news/EventImpactPanel.svelte`、`apps/desktop/src/feature/news/AnnouncementVerificationPanel.svelte`、`apps/desktop/src/feature/news/AnnouncementDetailPanel.svelte`、`tests/features/news-workbench-contract.test.mjs`。

### 2026-08-30 公告正文直接事实索引阶段

- `confirmed`：公告正文面板新增独立 `announcement-detail-facts.ts`，复用既有正文代码/日期/金额线索，按原文顺序去重并提取有限动作词，保留最多 140 字符局部上下文，最多 24 项。
- `confirmed`：直接事实索引只用于检索和审计，不识别利好/利空，不生成方向、评分、推荐或因果结论；实现没有网络、IPC、计时器、随机逻辑或新依赖。3 项 Vitest、公告正文合同、Vite 3882 模块构建和文件注册表检查通过。
- `observed`：完整公告实体关系、第二正文来源、逐条行业归因和市场反应归因仍未接入，新闻工作台与产品总体保持 `active/partial`。

- 来源：`apps/desktop/src/feature/news/announcement-detail-facts.ts`、`apps/desktop/src/feature/news/announcement-detail-facts.test.ts`、`apps/desktop/src/feature/news/AnnouncementDetailPanel.svelte`、`tests/features/announcement-detail-semantics-contract.test.mjs`。

### 2026-08-30 本地网页预览保持可用

- `confirmed`：开发预览服务持续监听 `127.0.0.1:1420`，`/a-shares?symbol=600519` 返回 HTTP 200，页面标题为“个股观察 - 一树-A股观测台”。
- `confirmed`：预览标签已在 Codex 浏览器中打开并标记为可交付，用户可直接查看当前进度；预览没有 Tauri IPC 时继续展示真实 `unavailable/partial` 状态，不填充假行情。
- `observed`：该服务是开发预览，不代表 Windows/Mac 发布包；暂不生成 EXE、安装包或 ZIP。

- 来源：`http://127.0.0.1:1420/a-shares?symbol=600519`、当前任务浏览器验证记录。

### 2026-08-31 实时两市成交来源阶段

- `confirmed`：顶部市场脉冲新增独立东方财富实时成交切片，仅读取上证 `000001`、深证 `399001` 的 `f6` 成交额与 `f124` 来源时间；两条记录同一上海交易日且来源时刻相差不超过 5 秒时才计算实时合计，否则保留 `partial` 并不相加。
- `confirmed`：链路复用共享网络客户端、请求去重、5 秒两级缓存和专属熔断器，本地永久日线仍在阻塞线程池独立读取，不写入历史库。前端优先显示有有效总额的实时证据并展示来源时间，实时缺失或 stale 时回退本地高覆盖交易日。
- `observed`：普通网页预览无 Tauri IPC，仍显示真实不可用边界；第三实时来源、交易所原子快照和逐笔成交仍未接入，产品总体保持 `active/partial`。本阶段未生成发布包、未修改参考项目、未执行 Git 写操作。

- 来源：`docs/superpowers/specs/2026-08-31-market-turnover-realtime-design.md`、`docs/superpowers/plans/2026-08-31-market-turnover-realtime.md`、`apps/desktop/src-tauri/src/application/use_cases/load_market_realtime_turnover.rs`、`apps/desktop/src/feature/market-overview/market-turnover-presenter.ts`。

### 2026-08-31 实时两市成交阶段收尾验证

- `confirmed`：补齐 `MarketPulseState` 的前端测试夹具，并将实时切片严格保持为独立 `MarketRealtimeTurnoverSlice`，不再误用通用 `EvidenceEnvelope`；根级 `pretest` 已纳入 `market-turnover-realtime-contract`。
- `confirmed`：定向前端 5 个文件/23 项、实时来源 5 项、实时聚合 3 项、前端生产构建和 Node 跨层合同通过；Web 全量 `146` 个 Vitest 文件/`594` 项通过，Rust workspace `719` 项通过、`1` 项既有性能测试忽略。
- `confirmed`：全量复核中发现并修正投资日历窗口测试的时序竞态：并发分支原先固定 `1ms` TTL 却等待 `10ms`，会导致第二次 fetch；现让并发夹具使用 `60s` TTL，过期缓存分支仍保留 `1ms`，聚焦和全量 Rust 测试均以退出码 `0` 通过。
- `confirmed`：`cargo fmt --all -- --check`、架构登记（`1490` 条）、编码扫描（`2894` 个文本文件）、`git diff --check` 和 Vite 生产构建均通过；预览 `http://127.0.0.1:1420/a-shares?symbol=600519` 标题正确、无横向溢出、控制台 warning/error 为 0，并保持可见。
- `observed`：普通网页预览无 Tauri IPC，实时成交仍显示真实不可用边界；第三实时来源、交易所原子快照、逐笔成交及产品其余历史缺口未关闭，项目总体保持 `active/partial`。本阶段未生成 EXE、安装包或 ZIP，未修改参考项目，未执行 Git commit/push。

- 来源：`docs/superpowers/plans/2026-08-31-market-turnover-realtime.md`、`apps/desktop/src/app/market-pulse.test.ts`、`apps/desktop/src/feature/market-overview/review-statistics-presenter.test.ts`、`apps/desktop/src/feature/today-decision/today-decision-workbench-presenter.test.ts`、`apps/desktop/src-tauri/src/application/use_cases/investment_calendar_window_loader_tests.rs`、本轮测试与预览验证记录。

### 2026-08-31 通达信原生分笔阶段

- `confirmed`：新增通达信原生 TCP 分笔跨层链路：`stock_tdx_transaction` 合同、`tdx_wire` 帧/变长整数解析、`tdx_transaction` 实时读取、应用用例缓存/去重/熔断/阻塞线程池、Tauri IPC 和个股观察独立前端面板。TDX 与腾讯 3 秒聚合成交物理分开，不逐条合并。
- `confirmed`：服务器地址与端口加入 Rust/TypeScript 用户设置，默认空值/0；无配置不建立 TCP 连接，配置仍通过用户数据目录原子保存，业务层不直接依赖 Windows/macOS API。
- `confirmed`：分笔记录只在价格、手数、时间和方向通过校验时展示；成交额按价格×手数×100 计算，来源时间和限制原文可追溯，失败保持 `unavailable/stale/partial`，不填充零值或主动买卖结论。TDX 协议、应用用例、前端 Presenter、Node 合同、Vite 构建和 Rust check 已通过；生产文件已同步登记到 YAML/Markdown。
- `observed`：公共 TDX 服务器 SLA、交易所逐笔编号、完整委托队列、原子同刻快照和第三来源裁决仍缺失；普通网页预览无 Tauri IPC，继续显示真实不可用边界。未修改参考项目，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`docs/superpowers/specs/2026-08-31-tdx-transaction-detail-design.md`、`docs/superpowers/plans/2026-08-31-tdx-transaction-detail.md`、`apps/desktop/src-tauri/src/application/use_cases/load_stock_tdx_transaction.rs`、`apps/desktop/src-tauri/src/commands/stock_tdx_transaction.rs`、`apps/desktop/src/feature/stock-observation/StockTdxTransactionPanel.svelte`、`tests/features/stock-tdx-transaction-contract.test.mjs`。

### 2026-08-31 TDX 分笔前端生命周期复核

- `confirmed`：新增 `stock-tdx-transaction-store.test.ts`，覆盖同股并发请求只调用一次加载器、隐藏页面不发请求且恢复可见后继续、失败保留最后有效快照并降为 `stale`、切换股票时旧响应不能覆盖新股票。
- `confirmed`：根 `package.json` 的 `pretest` 已纳入 `stock-tdx-transaction-contract.test.mjs`；定向合同、Presenter 和 Store 共 6 项前端测试通过，Store 测试已登记到双文件注册表。
- `observed`：公共 TDX 服务可用性、交易所成交编号、完整队列、原子同刻快照和第三来源裁决仍未解决；普通网页预览没有 Tauri IPC，未配置服务器时继续显示真实 `unavailable`，不注入测试行情。

来源：`apps/desktop/src/feature/stock-observation/stock-tdx-transaction-store.test.ts`、`package.json`、`docs/architecture/file-registry.yaml`、`docs/verification/data-source-matrix.md`。

### 2026-08-31 可转债查询生命周期阶段

- `confirmed`：可转债页不再直接导入 Tauri IPC，改为独立 `convertible-bonds-store.ts`；查询键会合并并发请求，最多缓存两个查询结果，失败保留 last-good 并降级 `stale`，换债时晚到响应不会覆盖当前结果。
- `confirmed`：新增 `convertible-bonds-contract.test.mjs`，Store、页面和双注册表均已登记；全量 Web 测试 149 个文件/603 项，Vite 3887 模块构建和定向合同通过。
- `observed`：可转债发现池的条款完整性、候选筛选和第二来源仍是 `partial` 缺口；本阶段未生成 EXE/安装包/ZIP，未修改参考项目，未执行 Git commit/push。

来源：`apps/desktop/src/feature/convertible-bonds/convertible-bonds-store.ts`、`apps/desktop/src/feature/convertible-bonds/ConvertibleBondPage.svelte`、`tests/features/convertible-bonds-contract.test.mjs`、`docs/verification/feature-parity-matrix.md`。

### 2026-08-31 历史复盘 Store 生命周期阶段

- `confirmed`：历史复盘页面已将价格复盘与决策账本的 IPC、并发、缓存和错误边界收敛到 `apps/desktop/src/feature/history/history-review-store.ts`。查询键包含股票、精确交易日和窗口；同键请求共享 in-flight Promise，复盘和账本分别使用有界 LRU，显式运行支持强制刷新。
- `confirmed`：任一支路失败时另一支路结果继续保留；已有复盘证据信封失败降为 `stale`，账本旧快照失败标记 `stale`，交易日身份不一致拒绝显示；切换查询时晚到响应不覆盖当前状态；清空输入只重置查询，不删除已加载快照。
- `confirmed`：`HistoryReviewPage.svelte` 只负责输入校验、消息和三个独立面板展示，不再导入 Tauri IPC 或使用 `Promise.allSettled`；新增 5 项 Store Vitest、历史复盘/决策账本合同，根级前端 150 个文件/608 项通过，Vite 构建 3888 个模块，双注册表 1511 项通过。
- `observed`：本阶段只改善生命周期与层边界，未扩大通达信日线、永久账本、建议快照、逐条归因或外部交易日历覆盖；普通网页预览无 Tauri IPC 时保持真实 `unavailable/partial`。参考项目仍只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/history/history-review-store.ts`、`apps/desktop/src/feature/history/history-review-store.test.ts`、`apps/desktop/src/feature/history/HistoryReviewPage.svelte`、`tests/features/history-review-contract.test.mjs`、`tests/features/decision-ledger-contract.test.mjs`、`docs/architecture/file-registry.yaml`。

### 2026-08-31 风险工作台 Store 生命周期阶段

- `confirmed`：风险页面的四路首刷和持仓/观察篮子动作已收敛到 `apps/desktop/src/feature/risk/risk-workbench-store.ts`。同一首刷共享 in-flight Promise，持仓与观察风险证据信封分别使用 `keepLastGood`，一支读取失败不会清除另一支；保存/移除只定向重算受影响风险分支，避免重复请求。
- `confirmed`：`RiskPage.svelte` 只订阅 Store、转发刷新和面板动作，不再直接导入 Tauri 或在页面维护并发/错误状态；新增 3 项 Store Vitest、风险跨层合同和双注册表条目，生产构建 3889 个模块通过。
- `observed`：该阶段不改变风险领域公式、持仓/观察篮子存储或行情来源覆盖；普通网页预览无 Tauri IPC 时仍显示真实 `unavailable/partial`。参考项目保持只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/risk/risk-workbench-store.ts`、`apps/desktop/src/feature/risk/risk-workbench-store.test.ts`、`apps/desktop/src/feature/risk/RiskPage.svelte`、`tests/features/risk-workbench-contract.test.mjs`、`docs/architecture/file-registry.yaml`。

### 2026-08-31 监控中心 Store 生命周期阶段

- `confirmed`：监控中心新增 `monitor-center-store.ts`，统一规则列表、运行时快照、规则保存、条件测试、启停和删除的前端 IPC；规则与运行时首刷并行执行并共享同一 in-flight Promise。
- `confirmed`：任一首刷支路失败时另一支路继续保留成功结果；连续测试失败时保留上一份真实测试证据并降为 `stale`。页面只订阅 Store，`MonitorCenterPage.svelte` 不再直接导入 Tauri 或维护命令字符串，`RuleEditor.svelte` 复用 Store 导出的草稿类型。
- `confirmed`：新增 Store Vitest 5 项、监控跨层合同和 YAML/Markdown 双注册表登记；定向测试和前端生产构建通过。本阶段不新增行情来源、通知通道或后台轮询，监控菜单仍按真实数据覆盖保持 `implemented/partial`。
- `observed`：普通网页预览没有 Tauri IPC，监控规则和运行时仍显示真实不可用边界；参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/monitor-center/monitor-center-store.ts`、`apps/desktop/src/feature/monitor-center/monitor-center-store.test.ts`、`apps/desktop/src/feature/monitor-center/MonitorCenterPage.svelte`、`tests/features/monitor-rule-contract.test.mjs`、`docs/architecture/file-registry.yaml`。

### 2026-08-31 新闻工作台 Store 生命周期收尾

- `confirmed`：修复新闻 Store 快照、事件影响和纠错写回遗漏传递 `maxEntries` 的问题；自定义缓存上限现在同时约束股票资讯缓存和事件影响缓存，避免长期运行超出配置边界。
- `confirmed`：新增事件影响缓存上限回归测试；新闻工作台前端测试全量通过（153 个文件、622 项），此前新闻跨层合同和 Vite 构建保持通过。
- `observed`：新闻来源覆盖不足仍按真实证据显示 `partial/unavailable`；本阶段未新增来源、未修改参考项目、未执行 Git 写操作，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/news/news-workbench-store.ts`、`apps/desktop/src/feature/news/news-workbench-store.test.ts`、`docs/superpowers/plans/2026-08-31-news-workbench-store.md`。

### 2026-08-31 股票选择器 Store 解耦阶段

- `confirmed`：股票选择器新增独立 `stock-selector-store.ts`，统一搜索、最近标的读取和记忆写入；同查询共享 in-flight Promise，查询序列隔离晚到响应，辅助记忆失败不会清除当前展示。
- `confirmed`：`StockSelector.svelte` 已移除 Tauri IPC，只保留输入防抖、弹层和选择回调；股票搜索合同验证组件无直连、Store 持有三个命令，生产和测试文件已登记到 YAML/Markdown 双注册表。
- `confirmed`：Store 3 项 Vitest、根级 `pnpm test`（154 个前端测试文件、625 项）、Vite 构建、架构/编码检查和 Rust workspace 730 项通过（1 项既有性能测试忽略）。
- `observed`：普通网页预览无桌面 IPC 时继续显示真实不可用状态；参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/stock-observation/stock-selector-store.ts`、`apps/desktop/src/feature/stock-observation/stock-selector-store.test.ts`、`apps/desktop/src/feature/stock-observation/StockSelector.svelte`、`tests/features/stock-search-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-stock-selector-store.md`。

### 2026-08-31 公司研究主快照 Store 解耦阶段

- `confirmed`：公司研究主快照新增独立 `company-research-store.ts`，负责选股、强制刷新、有限缓存、`last-good -> stale` 回退和换股晚到响应隔离；财务、研报、资金、解禁、事项和估值子 Store 保持独立。
- `confirmed`：`CompanyResearchPage.svelte` 已移除 `load_company_research` 直接 IPC，只订阅主研究 Store；公司研究合同验证页面无直连、Store 持有命令，生产和测试文件已登记到双注册表。
- `confirmed`：主研究 Store 4 项 Vitest、根级前端 155 个测试文件/629 项、Vite 构建、架构和编码检查通过。
- `observed`：研究来源覆盖和 AI 适配器配置仍按真实状态保持 `partial/unavailable`；参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/company-research/company-research-store.ts`、`apps/desktop/src/feature/company-research/company-research-store.test.ts`、`apps/desktop/src/feature/company-research/CompanyResearchPage.svelte`、`tests/features/company-research-live-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-company-research-store.md`。

### 2026-08-31 公司研究对比客户端阶段

- `confirmed`：`ResearchComparison.svelte` 已移除 Tauri IPC 与 `invokeEvidence` 直连，新增 `company-research-comparison-client.ts` 统一封装 `compare_company_research`，按有序双代码请求。
- `confirmed`：客户端复用共享证据信封，桌面服务缺失时保持 `unavailable`，不新增轮询、缓存、网络源或后台任务；新增 Vitest 2 项和跨层合同断言。
- `observed`：对比结果仍受研究来源覆盖限制，产品总体保持 `active/partial`；参考项目只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`apps/desktop/src/feature/company-research/company-research-comparison-client.ts`、`apps/desktop/src/feature/company-research/company-research-comparison-client.test.ts`、`apps/desktop/src/feature/company-research/ResearchComparison.svelte`、`tests/features/company-research-comparison-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-company-research-comparison-client.md`。

### 2026-08-31 公司研究 AI 解释客户端阶段

- `confirmed`：`ResearchAiPanel.svelte` 已移除 Tauri IPC 与 `invokeEvidence` 直连，新增 `company-research-ai-client.ts` 封装 `explain_company_evidence`；请求仍严格绑定股票、冻结研究版本和原始证据文本。
- `confirmed`：客户端复用共享证据信封，网页预览或未配置 AI 时保持真实 `unavailable`，不生成文本、不新增网络或轮询；新增 Vitest 2 项和跨层合同断言。
- `observed`：AI 供应商适配器和安全校验仍由 Rust 后端唯一负责，产品总体保持 `active/partial`；参考项目只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`apps/desktop/src/feature/company-research/company-research-ai-client.ts`、`apps/desktop/src/feature/company-research/company-research-ai-client.test.ts`、`apps/desktop/src/feature/company-research/ResearchAiPanel.svelte`、`tests/features/company-research-live-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-company-research-ai-client.md`。

### 2026-08-31 量化预测 Store 解耦

- `confirmed`：Kronos 预测请求由 `ForecastPanel.svelte` 收敛到 `quant-forecast-store.ts`；Store 统一处理六位代码与 1-30 日校验、同键并发去重、容量 2 缓存、`last-good -> stale` 回退、响应身份校验和换标晚到隔离。
- `confirmed`：面板只订阅 Store 并显式触发检查，`run_kronos_forecast` 只保留在 Store 默认加载器；未新增网络源、定时器或依赖，真实 `missing/unavailable/stale` 状态继续透传。
- `confirmed`：Store 4 项 Vitest、量化任务跨层合同、TypeScript 编译和文件注册门禁通过；工程审计记录位于 `docs/verification/feature-completion-audit.md`，计划位于 `docs/superpowers/plans/2026-08-31-quant-forecast-store.md`。
- `observed`：量化回测任务启动/取消/进度和导出面板仍待后续按同一边界拆分；项目总体保持 `active/partial`，本阶段未修改参考项目、未执行 Git 写操作、未生成 EXE/安装包/ZIP。

来源：`apps/desktop/src/feature/quant-analysis/quant-forecast-store.ts`、`apps/desktop/src/feature/quant-analysis/quant-forecast-store.test.ts`、`apps/desktop/src/feature/quant-analysis/ForecastPanel.svelte`、`tests/features/quant-task-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-quant-forecast-store.md`。

### 2026-08-31 量化回测任务 Store 解耦

- `confirmed`：回测任务的参数校验、启动/等待/取消编排、进度投影、结果 JSON 解析和错误状态已集中到 `quant-backtest-store.ts`；`QuantAnalysisPage.svelte` 只维护参数、订阅 Store 和渲染面板，不再直接调用 Tauri、任务事件或轮询定时器。
- `confirmed`：同一完整请求共享 in-flight Promise；换股会中止旧等待并隔离晚到结果；同股票失败保留上一份真实回测并降为 `stale`，错股或损坏 JSON 不显示。
- `confirmed`：Store 4 项 Vitest、量化任务跨层合同和 TypeScript 编译通过，双文件注册表、工程审计和计划文档已同步。
- `observed`：结果导出面板仍待下一阶段改为独立客户端边界；普通网页预览没有 Tauri IPC 时保持真实 `missing/unavailable`，项目总体继续 `active/partial`。本阶段未修改参考项目、未执行 Git 写操作、未生成 EXE/安装包/ZIP。

来源：`apps/desktop/src/feature/quant-analysis/quant-backtest-store.ts`、`apps/desktop/src/feature/quant-analysis/quant-backtest-store.test.ts`、`apps/desktop/src/feature/quant-analysis/QuantAnalysisPage.svelte`、`tests/features/quant-task-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-quant-backtest-store.md`。

### 2026-08-31 量化回测导出客户端阶段

- `confirmed`：`BacktestExportPanel.svelte` 已移除 Tauri IPC 直连，新增 `quant-export-client.ts` 统一封装 `export_backtest_result`；客户端只接受 JSON/CSV，路径仍由 Rust 原子写入用户数据目录返回。
- `confirmed`：面板错误信息统一使用共享 IPC 错误转换；普通网页预览没有桌面服务时保持真实不可用提示，不生成假路径或额外请求。
- `confirmed`：新增客户端 2 项 Vitest、量化验证跨层合同断言，并同步更新 YAML/Markdown 文件注册表与工程审计。
- `observed`：导出内容格式、用户目录隔离与原子写入仍由 Rust 导出基础设施负责；产品总体保持 `active/partial`，参考项目只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`apps/desktop/src/feature/quant-analysis/quant-export-client.ts`、`apps/desktop/src/feature/quant-analysis/quant-export-client.test.ts`、`apps/desktop/src/feature/quant-analysis/BacktestExportPanel.svelte`、`tests/features/quant-validation-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-quant-export-client.md`。

### 2026-08-31 今日研判冻结客户端阶段

- `confirmed`：今日研判页面的冻结动作已收敛到独立 `decision-freeze-client.ts`，页面只负责请求编排、忙碌状态和用户反馈，不再直接导入或持有 Tauri 命令字符串。
- `confirmed`：客户端统一封装 `freeze_current_decision`，复用共享 IPC 错误转换；桌面桥接不存在（含网页预览的 `window is not defined`）时返回“桌面数据服务尚未启动”，不生成假账本记录。
- `confirmed`：客户端 2 项 Vitest、今日研判工作台合同、决策账本合同和文件注册表检查通过；新增生产文件、测试和计划已登记到 YAML/Markdown 双注册表。
- `observed`：交易日校验、幂等写入和永久账本存储仍由 Rust 决策账本链路负责；普通网页预览无 Tauri IPC 时保持真实 `unavailable`，项目总体继续保持 `active/partial`。本阶段未修改参考工程、未执行 Git commit/push、未生成 EXE/安装包/ZIP。

来源：`apps/desktop/src/feature/today-decision/decision-freeze-client.ts`、`apps/desktop/src/feature/today-decision/decision-freeze-client.test.ts`、`apps/desktop/src/feature/today-decision/TodayDecisionPage.svelte`、`tests/features/today-decision-workbench-contract.test.mjs`、`tests/features/decision-ledger-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-decision-freeze-client.md`。

### 2026-08-31 候选情绪客户端与 Store 阶段

- `confirmed`：候选情绪弹层已新增 `candidate-sentiment-client.ts` 与 `candidate-sentiment-store.ts`，候选读取按任务/股票键合并并发、最多保留两项成功缓存，刷新失败保留 last-good 并降为 `stale`，旧标的响应不能覆盖当前选择。
- `confirmed`：候选新闻 AI 解释已新增 `candidate-news-explanation-client.ts`；解释面板只在用户点击后发送冻结新闻证据 ID，不再直接导入 Tauri 或持有命令字符串。
- `confirmed`：候选情绪和新闻解释客户端/Store 共 6 项 Vitest、两份跨层合同通过；新增生产、测试和计划文件已登记到 YAML/Markdown 双注册表。
- `observed`：候选新闻第二来源、交易所事件时间、跨日回放和真实 AI 覆盖仍按既有边界保持 `partial/unavailable`；参考工程只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`apps/desktop/src/feature/candidate-sentiment/candidate-sentiment-client.ts`、`apps/desktop/src/feature/candidate-sentiment/candidate-sentiment-store.ts`、`apps/desktop/src/feature/candidate-sentiment/candidate-news-explanation-client.ts`、`apps/desktop/src/feature/candidate-sentiment/CandidateSentimentDetail.svelte`、`apps/desktop/src/feature/candidate-sentiment/CandidateNewsExplanationPanel.svelte`、`tests/features/candidate-sentiment-contract.test.mjs`、`tests/features/candidate-news-explanation-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-candidate-sentiment-client-store.md`。

### 2026-08-31 新闻纠错客户端阶段

- `confirmed`：人工纠错保存动作已从 `NewsCorrectionPanel.svelte` 收敛到独立 `news-correction-client.ts`；组件只负责表单校验、忙碌状态和 `saved` 事件，不再直接依赖 Tauri IPC。
- `confirmed`：客户端统一封装 `save_news_correction`，处理桌面桥接缺失和可读错误；Rust 领域校验、公告候选约束和数据库幂等写回保持唯一实现，未复制到前端。
- `confirmed`：客户端 3 项 Vitest、事件影响跨层合同及双文件注册登记已完成；定向测试通过。
- `observed`：普通网页预览没有桌面 IPC 时保存动作保持真实“桌面数据服务尚未启动”；参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/news/news-correction-client.ts`、`apps/desktop/src/feature/news/news-correction-client.test.ts`、`apps/desktop/src/feature/news/NewsCorrectionPanel.svelte`、`tests/features/event-impact-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-news-correction-client.md`。

### 2026-08-31 运维安全客户端阶段

- `confirmed`：备份恢复面板的安全诊断、备份校验和恢复演练已收敛到 `operations-safety-client.ts`；数据契约独立位于 `operations-safety-types.ts`，面板不再直接依赖 Tauri IPC。
- `confirmed`：客户端统一处理三个运维安全命令的参数和错误转换；Rust 继续唯一负责清理预览、路径安全、完整性校验和恢复到新库。
- `confirmed`：客户端 4 项 Vitest、运维恢复跨层合同及双文件注册登记已完成；定向测试通过。
- `observed`：普通网页预览没有桌面 IPC 时安全面板保持真实不可用状态；参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/operations/operations-safety-types.ts`、`apps/desktop/src/feature/operations/operations-safety-client.ts`、`apps/desktop/src/feature/operations/operations-safety-client.test.ts`、`apps/desktop/src/feature/operations/BackupRecoveryPanel.svelte`、`tests/features/operations-recovery-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-operations-safety-client.md`。

### 2026-08-31 运维页面客户端阶段

- `confirmed`：`OperationsPage.svelte` 已移除 Tauri IPC、`waitForTask` 和命令字符串直连；普通运维动作统一进入 `operations-client.ts`，后台任务统一进入 `operations-task-client.ts`，契约独立位于 `operations-types.ts`。
- `confirmed`：客户端覆盖状态读取、缓存清理、数据库维护、备份、通达信导入、长任务启动/控制/重试和终态等待；页面只保留生命周期、按钮状态和用户消息。
- `confirmed`：客户端 4 项 Vitest、运维任务和 TDX 导入跨层合同及双文件注册登记已完成；全量前端测试与构建通过。
- `observed`：普通网页预览没有桌面 IPC 时运维页面保持真实不可用状态；Rust 侧任务、数据库和导入实现未修改，参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/operations/operations-types.ts`、`apps/desktop/src/feature/operations/operations-client.ts`、`apps/desktop/src/feature/operations/operations-task-client.ts`、`apps/desktop/src/feature/operations/operations-client.test.ts`、`apps/desktop/src/feature/operations/operations-task-client.test.ts`、`apps/desktop/src/feature/operations/OperationsPage.svelte`、`tests/features/operations-task-contract.test.mjs`、`tests/features/tdx-import-contract.test.mjs`、`docs/architecture/file-registry.yaml`。

### 2026-08-31 个股研究增强客户端阶段

- `confirmed`：`StockObservationPage.svelte` 已移除 `load_stock_research_cockpit` 直接 IPC，新增 `stock-research-client.ts` 统一封装研究增强请求和共享证据状态转换。
- `confirmed`：页面继续在基础驾驶舱与分时读取完成后按需启动研究增强，股票/请求序列隔离、无轮询和不填充假数据边界保持不变。
- `confirmed`：客户端 3 项 Vitest、研究证据跨层合同及双文件注册登记已完成。
- `observed`：研究五类证据覆盖仍由 Rust 来源、缓存和冻结用例决定；普通网页预览无桌面 IPC 时继续显示真实 `unavailable`，参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/feature/stock-observation/stock-research-client.ts`、`apps/desktop/src/feature/stock-observation/stock-research-client.test.ts`、`apps/desktop/src/feature/stock-observation/StockObservationPage.svelte`、`tests/features/stock-research-evidence-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-stock-research-client.md`。

### 2026-08-31 顶栏更新状态客户端阶段

- `confirmed`：顶栏更新组件 `UpdateStatus.svelte` 已移除 Tauri IPC 直连；新增 `update-client.ts` 统一封装 `check_for_update`、`download_update_package` 和 `apply_downloaded_update` 三条命令。
- `confirmed`：客户端复用共享 IPC 错误转换；更新源配置缺失时组件不发请求，网页预览或桌面桥接缺失时保持真实不可用状态，不生成版本、路径或更新包假数据。
- `confirmed`：新增 4 项客户端 Vitest、更新状态跨层合同和独立计划；生产文件、测试、计划已登记到 YAML/Markdown 双注册表。
- `confirmed`：根级前端门禁通过：170 个 Vitest 文件、669 项测试，Vite 3906 个模块，文件注册表 1565 项，编码扫描 2976 个文本文件，`git diff --check` 通过。
- `observed`：签名校验、下载完整性、原子激活、用户目录保护和回滚仍由 Rust 更新核心唯一负责；项目总体继续保持 `active/partial`。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/app/update-client.ts`、`apps/desktop/src/app/update-client.test.ts`、`apps/desktop/src/app/UpdateStatus.svelte`、`tests/features/update-status-client-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-update-status-client.md`。

### 2026-08-31 更新自动检测生命周期阶段

- `confirmed`：顶栏在更新清单、公钥配置存在时启动独立 `update-check-lifecycle.ts`，首次异步检查并响应窗口焦点、联网恢复事件；同一时间只保留一个检查请求。
- `confirmed`：单次定时器在检查完成后进入六小时冷却，卸载时清理定时器和事件监听；生命周期只做检测提示，不自动下载或应用更新，不使用 `setInterval` 或后台常驻轮询。
- `confirmed`：配置缺失时不启动生命周期、不发 IPC；验签、下载完整性、原子激活、用户目录保护和回滚仍由 Rust 更新核心负责。
- `confirmed`：新增 3 项生命周期 Vitest 和跨层合同，双注册表及根 `pretest` 已同步；定向测试和 Vite 3907 模块构建通过。
- `observed`：普通网页预览无 Tauri IPC，不能证明远程清单非空或自动检测成功，项目总体继续保持 `active/partial`。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src/app/update-check-lifecycle.ts`、`apps/desktop/src/app/update-check-lifecycle.test.ts`、`apps/desktop/src/app/UpdateStatus.svelte`、`tests/features/update-check-lifecycle-contract.test.mjs`、`docs/superpowers/plans/2026-08-31-update-check-lifecycle.md`。
### 2026-08-31 可重建缓存总量治理

- `confirmed`：`PersistentCache::prune_to_payload_bytes` 在用户缓存库事务内按创建时间和键名裁剪最旧 payload，默认总量上限 256 MiB；零上限拒绝，单条超限也会删除，永久业务库不受影响。
- `confirmed`：本地运维清理动作现在合并过期删除与容量裁剪，前端提示不再误称“仅过期缓存”；生产实现、行为测试、架构登记和审计已同步。
- `observed`：缓存压缩/SQLite VACUUM 与永久数据库归档仍按后续容量治理阶段推进；参考项目只读，未执行 Git 写操作，未生成 EXE/安装包/ZIP。

### 2026-08-31 缓存 SQLite 空间回收

- `confirmed`：`PersistentCache::compact` 仅对可重建网络缓存连接执行 `wal_checkpoint(TRUNCATE)` 与 `VACUUM`；运维清理在过期删除或 payload 容量裁剪删除记录后才调用，空闲清理不产生额外压缩开销。
- `confirmed`：新增行为测试覆盖删除 512 KiB payload 后缓存库主库/WAL 总占用下降，以及存活记录仍可读取；永久业务数据库不受影响。
- `observed`：缓存空间回收完成后，永久业务数据库的归档、分片和长期压缩仍属于后续容量治理范围；参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`apps/desktop/src-tauri/src/infrastructure/cache/cache_store.rs`、`apps/desktop/src-tauri/src/commands/operations.rs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-31 可转债后端缓存与熔断阶段

- `confirmed`：新增 `application/use_cases/load_convertible_bonds.rs`，发现池与单债行情分别使用 6 小时、10 秒两级缓存，并复用共享请求去重和独立熔断器；网络不可用或熔断时只回退同一可转债域的 `stale` 证据。
- `confirmed`：`research.rs` 仅保留薄 IPC，`CoreMenuState` 新增发现池/行情两路熔断器；可转债不会用股票或其他债券字段替代，stale 文案也保持债券语义。
- `confirmed`：3 项 Rust 行为测试、跨层契约、架构登记和格式检查通过。
- `observed`：条款完整性、候选筛选、第二行情来源和正股联动仍是 `partial`；参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_convertible_bonds.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/company_evidence_loader.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/convertible-bonds-contract.test.mjs`。

### 2026-08-31 可转债第二行情来源交叉核验

- `confirmed`：可转债页面新增新浪公开行情适配层 `sina_convertible_bond.rs`，与腾讯主源分别使用 10 秒缓存、请求去重和独立熔断器，并发读取；统一转换为 `ConvertibleBondQuote`。
- `confirmed`：`convertible_bond_quote_confirmation.rs` 只在同码、来源时间差不超过 5 秒、现价/昨收偏差不超过 0.15%、成交额偏差不超过 5% 时授予 `confirmed`；其余结果明确为 `divergent/time_separated/time_unverified/primary_only/secondary_only/unavailable`。
- `confirmed`：前端新增 `ConvertibleBondQuoteConfirmationPanel.svelte`，仅展示后端双源证据、时间和偏差，不直接调用 IPC 或网络；无报价时 `quoteConfirmation` 为 `null` 并显示未形成核验的真实空态。
- `confirmed`：新浪源、确认纯域、测试和设计/实施文档已写入 `docs/architecture/file-registry.yaml` 与 Markdown 视图，跨层合同增加来源、面板和登记断言。
- `observed`：辅助新浪来源 stale 不会单独把整体 envelope 降为 stale；主源或发现池 stale 才降级整体，页面仍保持可转债 `partial`，因为条款、候选、正股联动、原子快照和第三行情来源未完成。参考工程只读，未生成 EXE/安装包/ZIP，未执行 Git commit/push。

### 2026-08-31 可转债正股联动观察阶段

- `confirmed`：可转债快照新增独立 `linkedStockQuote`，只在具体债券查询且发现池存在正股代码时按需请求腾讯正股行情；正股使用独立缓存键、请求去重和独立熔断器，失败保留真实 `stale/unavailable` 状态。
- `confirmed`：新增独立 `ConvertibleBondLinkedStockPanel.svelte`，与债券主行情、双源债券报价核验、债券诊断分区展示；正股数据不回填债券价格、转股价值、溢价率或诊断结果。
- `observed`：正股第二来源、联动历史序列、交易所原子快照和条款完整性仍未完成；参考工程只读，未生成 EXE/安装包/ZIP，未执行 Git commit/push。

来源：`crates/contracts/src/research.rs`、`apps/desktop/src-tauri/src/application/use_cases/load_convertible_bonds.rs`、`apps/desktop/src-tauri/src/commands/core_menu.rs`、`apps/desktop/src/feature/convertible-bonds/ConvertibleBondLinkedStockPanel.svelte`、`tests/features/convertible-bonds-contract.test.mjs`。

### 2026-08-31 可转债条款完整性审计阶段

- `confirmed`：新增纯前端 `convertible-bond-terms-presenter.ts` 与 `ConvertibleBondTermsPanel.svelte`，基于发现池已有真实字段统计样本量、完整条目、完整度和字段缺口分布；空发现池保持 `missing`，不以零值或其他资产字段补齐。
- `confirmed`：条款审计只消费现有可转债 Store 快照，不新增 IPC、网络请求、定时器或数据库表；Presenter 单元测试、跨层合同、Vite 构建、架构与编码检查通过。
- `observed`：完整条款文本、候选筛选策略、正股第二来源、原子快照和更多可转债来源仍未完成；菜单继续保持 `partial`。参考工程只读，未生成 EXE/安装包/ZIP，未执行 Git commit/push。

来源：`apps/desktop/src/feature/convertible-bonds/convertible-bond-terms-presenter.ts`、`apps/desktop/src/feature/convertible-bonds/ConvertibleBondTermsPanel.svelte`、`tests/features/convertible-bonds-contract.test.mjs`、`docs/verification/feature-completion-audit.md`。

### 2026-08-31 可转债候选池阶段

`confirmed`：新增纯前端 `convertible-bond-candidates-types.ts`、`convertible-bond-candidates-presenter.ts` 和 `ConvertibleBondCandidatesPanel.svelte`。候选规则只消费现有发现池字段：转股溢价率不高于 50%、剩余规模不低于 0.5、剩余期限不少于 30 天，并要求正股代码、转股价、转股价值等字段有效；阈值不满足标为 `excluded`，字段不足标为 `observe_only`，空发现池标为 `missing`。面板提供严格候选/观察/排除统计、搜索和状态筛选。

`confirmed`：候选池复用现有可转债 Store 快照，不新增 IPC、网络请求、定时器或数据库表；普通网页预览没有桌面服务时继续保持真实 `unavailable/missing`，不生成模拟候选。新增文件已登记到 YAML/Markdown 双注册表，Presenter 测试和前端构建已执行。

`observed`：候选池仍未接入后端完整诊断中的强赎状态、成交额门槛、双源原子快照和完整条款文本；因此可转债菜单及候选池继续保持 `partial`，不等同于投资建议。

来源：`apps/desktop/src/feature/convertible-bonds/convertible-bond-candidates-types.ts`、`apps/desktop/src/feature/convertible-bonds/convertible-bond-candidates-presenter.ts`、`apps/desktop/src/feature/convertible-bonds/convertible-bond-candidates-presenter.test.ts`、`apps/desktop/src/feature/convertible-bonds/ConvertibleBondCandidatesPanel.svelte`、`docs/verification/feature-parity-matrix.md`、`docs/verification/feature-completion-audit.md`。

### 2026-08-31 可转债正股双源确认阶段

`confirmed`：可转债正股联动新增新浪公开行情适配层。腾讯与新浪正股分别使用独立缓存键、请求去重和独立熔断器，并发读取；后端确认域仅在同代码、来源时间差不超过 5 秒且价格偏差不超过 0.15% 时标记 `confirmed`，否则保持 `divergent/primary_only/secondary_only/time_unverified/unavailable` 等真实状态。

`confirmed`：`ConvertibleBondSnapshot` 同时保留 `linkedStockQuote`、`linkedStockSecondaryQuote` 和 `linkedStockQuoteConfirmation`；前端联动面板展示两路价格、来源时间、时间差、价格偏差、缺失字段和差异，不覆盖腾讯主源，也不直接调用 IPC、网络或定时器。

`observed`：定向 Rust 测试、前端 Store 测试、双源跨层合同、可转债合同和前端构建已通过；交易所原子快照、正股历史联动序列、完整条款文本、批量成交额门禁和更多来源仍未完成，菜单与产品总体继续保持 `partial`。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/sina_stock_quote.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/bonds/convertible_bond_linked_stock_confirmation.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_convertible_bonds.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/ConvertibleBondLinkedStockPanel.svelte`、`docs/verification/feature-completion-audit.md`。

补充：已修正可转债正股腾讯/新浪两路请求的编排，使其在同一异步边界内并发读取；新增 Store 回归测试确认第二正股 DTO 与确认 DTO 跨层保留。新浪响应测试夹具已按真实 32 字段协议生成，Rust 定向测试重新通过。正股历史联动序列仍是后续缺口。

## 2026-08-31 可转债正股历史联动序列阶段

`confirmed`：新增 `ConvertibleBondLinkedStockHistoryRequest`、`ConvertibleBondLinkedStockHistorySnapshot` 及独立 Tauri 命令，严格校验债券/正股代码，复用 `stock_queries::load_daily_bars` 读取用户目录 `business.sqlite3`；历史日线与实时正股、债券行情和诊断字段物理分离。

`confirmed`：前端新增历史类型、IPC client、请求去重/缓存 store、纯 presenter 与 `ConvertibleBondLinkedStockHistoryPanel.svelte`。只有精确六位可转债代码才触发历史读取；简称搜索不会误请求。无本地日线保持 `missing/unavailable`，不以实时价格或零值填充。

`confirmed`：Rust 历史数据库行为测试、3 项前端 Vitest、跨层合同、Vite 构建、架构登记、编码扫描和 `git diff --check` 已通过。

`observed`：当前历史序列仅覆盖本地已经导入的日线；远程历史源、交易所级完整覆盖和实时历史流仍未接入，可转债菜单总体保持 `partial`。参考工程只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/convertible_bond_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/database/convertible_bond_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/convertible_bond_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/ConvertibleBondLinkedStockHistoryPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/convertible-bond-linked-stock-history-contract.test.mjs`。

## 2026-08-31 可转债候选池批量成交额门禁阶段

`confirmed`：可转债候选规则新增 `convertible-bond-candidate-v2` 流动性门禁。生产命令接入独立腾讯批量成交额来源，按每批 100 个债券代码拆分、最多 4 批并发，使用 30 秒两级缓存、请求去重和独立熔断器；单债已有有效成交额时直接复用，不重复批量请求。

`confirmed`：成交额缺失、零值、负值或非有限值保持 `observe_only`，行缺口标记 `turnover_amount`，风险标记 `liquidity_unverified`；有效成交额低于 20,000,000 元标记 `excluded/low_liquidity`；达到门槛且其他条款通过才标记 `candidate`。前端只展示后端成交额、门槛和覆盖率，不重新计算规则。

`observed`：批量来源仍是公开 HTTP 行情，不能证明交易所原子同刻成交额；第三行情来源、完整条款文本、正股历史远程覆盖和交易所级快照仍为后续缺口。参考项目保持只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/tencent_convertible_bond_batch.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/bonds/convertible_bond_candidate.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_convertible_bonds.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/ConvertibleBondCandidatesPanel.svelte`。

## 2026-08-31 可转债候选池 stale 流动性防护阶段

`confirmed`：批量成交额证据信封过期时，`load_convertible_bonds` 保留整体 `stale` 状态并清空规则层成交额映射；候选池行因此保持 `observe_only`，不会用过期成交额释放严格候选。新增 Rust 回归测试覆盖过期缓存路径，未新增来源、数据库表或后台轮询。

`observed`：新鲜批量成交额仍来自公开 HTTP，交易所原子同刻成交额、完整条款文本、第三行情来源、正股历史远程覆盖和复权日线仍未完成；参考项目只读，未执行 Git commit/push，未生成 EXE/安装包/ZIP。

## 2026-08-31 个股按需双源复权日线阶段

`confirmed`：个股观察新增独立前复权（qfq）与后复权（hfq）日线链路。腾讯解析 `qfqday/hfqday`，东方财富复用既有日线解析核心并传入 `fqt=1/2`；两路请求并发执行，各自使用独立 6 小时两级缓存、请求去重和熔断器。复权结果只在个股观察页按标的与模式按需读取，不写入永久业务数据库，也不改变既有未复权 TDX 主日线。

`confirmed`：后端合同、来源校验、应用用例、Tauri 命令和前端类型/客户端/Store/Presenter/面板均已拆分。前端按 `symbol:mode` 隔离缓存与 in-flight 请求，支持前复权/后复权切换、显式刷新、last-good 降级和错标响应拒绝；面板展示两路来源状态、核验结论、窗口和最近 30 根真实记录，金额缺失保持 `null`。

`confirmed`：复权合同测试 2 项、复权相关 Rust 测试 8 项、前端 Store/Presenter 测试 5 项、跨层 Node 合同、`cargo fmt --all -- --check`、架构登记和 UTF-8 编码扫描均通过；前端 Vite 生产构建通过。根级 `pretest`/`test` 已纳入复权跨层合同。

`observed`：公开来源的复权因子版本、交易所原子快照、完整公司行动与交易日历仍未完成；普通网页预览无 Tauri IPC 时保持真实 `unavailable/missing`，不以零值或未复权数据冒充复权结果。个股观察与产品总体继续保持 `partial`。参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/stock_adjusted_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/tencent_adjusted_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_adjusted_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_stock_adjusted_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/StockAdjustedDailyPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/stock-adjusted-daily-contract.test.mjs`。

## 2026-08-31 个股真实技术指标阶段

`confirmed`：个股诊断新增独立 Rust `technical_indicators` 领域模块，按固定口径计算 MACD(12/26/9)、RSI(14)、布林带(20) 和 ATR(14)，追加到既有趋势分区通用指标 DTO；只使用已经通过诊断校验的未复权日线，O(n) 单次扫描，不新增网络、数据库、缓存或轮询。

`confirmed`：样本不足、非有限收盘价和不完整 OHLC 保持 `None`，趋势分区按真实覆盖降为 `partial`；前端只渲染后端指标并明确未复权研究口径，不生成交易信号、因果判断或投资建议。领域测试、诊断回归、跨层合同、双注册表、Rust/前端全量门禁、构建、架构和编码检查均通过。

`observed`：复权因子版本、交易所原子快照和完整交易日历仍为个股观察缺口，菜单与产品总体继续保持 `partial`。参考项目只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/technical_indicators.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/stock_diagnosis.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/stock-technical-indicators-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/verification/feature-completion-audit.md`。

## 2026-08-31 开盘检查单冻结阶段

`confirmed`：第 42“开盘啦”新增独立冻结合同 `MarketOpenFreezeRequest/MarketOpenFreezeSnapshot`。Rust 纯领域层要求七项检查按 `indices`、`breadth`、`turnover`、`sentiment`、`hotspots`、`auction-gap`、`opening-freeze` 固定顺序提交，校验交易日、身份和值说明，并对规范 JSON 计算 SHA-256 快照身份；冻结时间不参与身份计算，同一输入重复冻结保持幂等。

`confirmed`：冻结用例使用独立可重建缓存库，热记录 TTL 1 小时，归档 TTL 30 天、最多 64 条；请求去重、读取时重建校验和快照 ID 校验均已接入。永久业务数据库不被触碰，非法请求、非法快照 ID、缓存损坏和网页无 Tauri 桥接均保持真实 `unavailable`，七项来源的 `ready/partial/stale/missing/unavailable` 状态不会被伪造或降级为零值。

`confirmed`：前端新增 `market-open-freeze-types.ts`、`market-open-freeze-client.ts`、`market-open-freeze-store.ts`、`market-open-freeze-presenter.ts`，并在 `MarketOpenPanel.svelte` 增加用户显式“冻结当前检查单”按钮。Store 容量 2、同请求合并、迟到响应隔离，无新定时器、网络请求或重复规则；面板展示冻结状态、时间、哈希尾段、就绪计数、缺口和警告。

`observed`：全市场竞价字段、竞价队列、多源竞价确认和交易所原子快照仍未接入；冻结只是当前可核验事实的时间点封存，不代表竞价结果、方向判断或交易建议。定向 Rust/Vitest/Node 合同和前端构建、架构登记已通过；参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/market_open_freeze.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/market_open_freeze.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/freeze_market_open.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_open_freeze.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/MarketOpenPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-open-freeze-contract.test.mjs`。
## 2026-08-31 异动历史归档查询阶段

`confirmed`：新增 `MarketMovementHistoryRequest`、`MarketMovementHistoryDay` 和 `MarketMovementHistorySnapshot` 合同。历史查询最多连续七日、最多返回 300 条事件；只读取现有 `network-cache.sqlite3` 异动归档，不访问网络、不写 `business.sqlite3`。

`confirmed`：缓存层新增带 `expires_at` 的前缀读取接口，应用用例校验归档键日期、`session_date` 与事件身份，按代码过滤、事件 ID 去重并稳定排序；新鲜、过期、损坏、无记录和无缓存分别保持 `partial/stale/missing/unavailable` 真实状态。

`confirmed`：历史复盘页面新增独立异动历史类型、IPC client、Store、Presenter 和 `MarketMovementHistoryPanel.svelte`，支持日期范围和六位代码筛选、归档统计、事件表及证据状态展示。合同、Rust 行为、前端 Vitest、Node 跨层合同、构建和双文件注册表已通过。

`observed`：归档仍受每日 300 条和七日 TTL 限制，交易所级逐笔时间戳、多源确认、七日之外历史和完整回填未完成；普通网页预览无 Tauri 桥接时保持 `unavailable`。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/market_movements_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/cache/cache_store.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_market_movement_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_movement_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/history/MarketMovementHistoryPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-movement-history-contract.test.mjs`。

## 2026-08-31 历史复盘跨期对比阶段

`confirmed`：历史复盘新增 `HistoryReviewComparisonRequest`、跨期快照和 1/5/20 日汇总合同。后端一次读取用户目录 `business.sqlite3` 的单股日线，按精确交易日筛选日期范围，最多保留最新 60 个复盘锚点；每个锚点复用既有 `evaluate_history_review`，不复制单日规则。

`confirmed`：跨期用例和独立 Tauri 命令保持真实 `ready/partial/stale/missing/unavailable` 状态。空库、非法日期/代码和无本地交易日不生成空行或邻近替代；有效日线只汇总实际存在的后续结果，缺失样本进入 `missingFields`。

`confirmed`：前端新增独立 client、Store、Presenter 和 `history-comparison-panel.svelte`。Store 同请求合并、最多两条缓存、响应身份校验和 last-good 降级；Presenter 将锚点倒序分页且每页最多 20 行，面板不直连 IPC、网络或计时器。定向 Rust/Vitest/Node 合同、Vite 构建和双文件注册表检查通过。

`observed`：跨期只覆盖本地已导入日线，第二日线来源、交易所级 SSE/逐笔、新闻行业归因、AI 因果判断和自动长期采集仍未接入；历史复盘与产品总体继续保持 `partial`。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包、便携包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/history_review_comparison.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/history/history_review_comparison.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/run_history_review_comparison.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/history_comparison.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/history/history-comparison-panel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/history-review-comparison-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-31-history-review-comparison.md`。
## 2026-08-31 百日新高趋势与量化 Store 收尾验证

`confirmed`：百日新高趋势的 Rust 6 项定向测试、前端 Presenter 3 项测试、跨层合同、TypeScript 编译、生产构建和全量工程门禁均通过。`pnpm test` 为 189 个 Vitest 文件/711 项，`cargo test --workspace --offline` 为 820 项通过、1 项既有性能测试忽略；文件登记、架构、编码、rustfmt 和差异检查通过。趋势工作区保留独立 100 日基线与 20 日观察路径，不把有效零突破转换为缺失。

`confirmed`：量化回测 Store 与预测 Store 的最终门禁已完成，任务生命周期、预测请求、导出客户端均保持独立模块和真实状态边界；未新增网络源、后台轮询或依赖。

`observed`：浏览器预览 `http://127.0.0.1:1420/?workspace=hundred-day-high-trends` 在无 Tauri 服务时显示真实不可用与 0 条趋势；非空真实趋势路径仍需桌面服务和本地 120 个统一交易日永久日线，外部交易日历、复权和多源确认仍是后续缺口。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/hundred_day_high_trends.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/HundredDayHighTrendsPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/hundred-day-high-trends-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-27-hundred-day-high-trends.md`。

## 2026-08-31 事件分钟交易日历置信门禁

`confirmed`：事件分钟封存用例在没有当前经核验交易日历时，仍保留真实分钟点和来源元数据，但强制快照生命周期与证据信封为 `partial`，补齐 `external_trading_calendar` 缺口和审计警告；仅按周末筛选的结果不再宣称 `ready/sealed`。

`confirmed`：无日历的 partial 记录可以写入既有七天、300 条上限的事件分钟归档，待同一事件得到官方日历后按现有候选比较和 revision 规则升级为 `sealed/ready`；已有经日历确认的 sealed last-good 记录在日历暂时不可用时仍可返回。

`observed`：该门禁不等于完整法定节假日、临时休市、交易所逐笔事件时刻或所有事件自动捕获已经完成；产品和个股观察继续保持 `active/partial`。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/capture_event_minute_evidence.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/trading_calendar.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/cache/event_minute_evidence_archive.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-31-event-minute-calendar-confidence.md`。

## 2026-08-31 TDX 历史分笔日期校验修复

`confirmed`：TDX 历史分笔请求的日期校验已复用 `time::Date::from_calendar_date` 与 `time::Month`，拒绝不存在的年月日（如非闰年 2 月 29 日、2 月 31 日），有效闰日仍可构造请求；无效输入继续返回 `InvalidEncoding`，不触碰网络或用户数据。

`confirmed`：新增回归测试覆盖无效日期与有效闰日；定向 Rust 测试 5 项通过，`cargo fmt --all -- --check`、架构登记（1722 项）、UTF-8/乱码扫描（3133 个文本文件）和 `git diff --check` 均通过。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/tdx_wire.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/tdx_wire_tests.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/file-registry.yaml`。

## 2026-08-31 开盘竞价缺口共享证据阶段

`confirmed`：开盘检查单 Presenter 现在复用已有 `marketMovements` 共享快照中的 `openGapPct`，按股票代码去重后展示有效样本数、平均缺口和覆盖计数；有界来源样本保持 `partial`，陈旧来源保持 `stale`，没有有效样本继续 `missing/unavailable` 并保留阻断项。刷新按钮复用既有异动 Store，不新增网络请求、IPC、定时器或数据库。

`observed`：交易所集合竞价时间戳、委托队列、撤单轨迹、多源原子快照和全市场完整覆盖仍未接入，不能据此生成方向或交易建议。参考项目只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-open-types.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-open-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/MarketOpenPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-open-presenter.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-open-contract.test.mjs`。

## 2026-09-01 可转债第三行情来源观察阶段

`confirmed`：新增东方财富 `push2.eastmoney.com/api/qt/stock/get` 可转债第三行情适配器，按精确六位债券代码按需读取；`f43/f60/f170/f48/f86` 解析为现价、昨收、涨跌幅、成交额和来源时间，执行市场路由、缩放、返回代码和载荷边界校验。

`confirmed`：第三来源拥有独立缓存键、请求去重和 `eastmoney_convertible_bond_breaker`，与腾讯主源、 新浪第二来源并发但互不覆盖。双源确认仍只比较腾讯与新浪；若双源均不可用而第三来源有数据，前端独立展示观察卡并标注不参与双源裁决。

`confirmed`：新增来源解析/缓存恢复测试、前端第三来源空态合同断言、YAML/Markdown 文件登记和功能审计同步。参考项目只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

`observed`：公开 HTTP 第三来源不能证明交易所原子同刻快照、完整债券来源覆盖或条款完整性；普通网页预览无 Tauri 服务时仍保持真实 `unavailable/missing`，可转债菜单和产品总体继续为 `partial`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/eastmoney_convertible_bond.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_convertible_bonds.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/convertible-bonds/ConvertibleBondQuoteConfirmationPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/convertible-bonds-contract.test.mjs`。

## 2026-09-01 市场脉冲来源时间一致性阶段

`confirmed`：顶部市场脉冲新增独立时间一致性 DTO 和纯领域判定，记录指数、宽度、成交、情绪四路来源的状态、来源、观测时间与数据存在性。固定 10 秒窗口内且四路均为 `ready` 才标记 `ready`；缺时间、不可解析、超窗或状态不齐为 `partial`；仅过期回退为 `stale`；无来源为 `unavailable`，不填充默认时间。

`confirmed`：后端复用既有并发聚合结果，前端复用事件总线和共享 Store，在顶部市场带显示“可比/部分可比/过期回退”等状态与时间差。新增 5 项 Rust 测试、前端回归、Node 合同和文件登记；不新增网络源、数据库、后台轮询或依赖。

`observed`：公开 HTTP 来源的观测时间接近仍不等于交易所原子同刻、逐笔成交或撮合时刻；市场脉冲和产品总体继续保持 `partial`。参考项目只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/market_pulse_temporal_consistency.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/market_pulse_temporal_consistency.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_pulse.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`。

## 2026-09-01 新闻市场反应证据阶段

`confirmed`：新闻工作台选中一条同股新闻后，新增独立市场反应证据链。后端在 `spawn_blocking` 中从用户永久目录的 `business.sqlite3` 读取最多 120 根日线，校验事件 ID、六位代码、来源元数据和上海发布时间后，复用既有 `freeze_stock_event_impact` 与 `StockEventImpactSnapshot`，不复制价格反应公式，也不写入永久业务库新表。

`confirmed`：本地事件影响冻结完成后，后端按本地日线最早/最新合法交易日派生有界窗口，并发复用东方财富与新浪未复权日线加载器、六小时缓存、请求去重和独立熔断器；通过 `assemble_confirmation` 将结果作为可选 `dailyConfirmation` 附加到当前响应。远程双源不可用只降级嵌套证据和 warning，不清空已形成的本地事件事实。

`confirmed`：前端新增独立 client、Store、Presenter 和 `NewsMarketReactionPanel.svelte`，复用 `StockDailyConfirmationPanel`；Store 容量 2、同事件请求去重、last-good 降级和晚到响应隔离；新闻页面只在选中事件后按需加载，不新增轮询。新增 Rust 用例边界回归、Presenter Vitest 和 Node 跨层合同。

`observed`：普通网页预览没有 Tauri 数据桥接时保持真实 `unavailable/missing`；公开未复权日线不等于交易所原子同刻快照、复权序列、完整交易日历或逐笔事件时间，也不能证明新闻因果关系。新闻菜单与产品总体继续为 `partial`。参考项目仍只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_news_market_reaction.rs`（实现与边界测试）、`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/stock_event_impact.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/NewsMarketReactionPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/news-market-reaction-presenter.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/news-market-reaction-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-news-daily-confirmation.md`。

## 2026-09-01 新闻事件分钟反应证据阶段

`confirmed`：新闻页新增独立 `NewsEventMinuteReactionPanel.svelte` 和 `news-event-minute-reaction-presenter.ts`。用户明确选中一条新闻后，面板才复用共享 `stockIntraday` 读取当前股票分钟信封，再复用 `eventMinuteEvidence` 形成事件前后最多 11 个分钟点；未选中、身份非法或网页无 Tauri 桥接时保持真实 `missing/unavailable`。

`confirmed`：事件身份使用 `news-event-minute:<eventId>`，事件价格保持 `null`，不从标题、日线或横截面推算。面板复用 `MarketEventMinuteWindow` 展示生命周期、窗口点数、来源和同分钟核验边界，不新增 IPC、数据库、计时器或行情公式。Presenter Vitest、Node 跨层契约、生产构建和双份文件登记已通过。

`observed`：分钟点仍是用户查看时取得的公开来源观测，无法证明交易所逐笔事件发生时间、完整法定交易日历或新闻因果关系；新闻工作台与产品总体继续保持 `partial`。参考项目只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/news-event-minute-reaction-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/NewsEventMinuteReactionPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/news-event-minute-reaction-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-news-minute-reaction.md`。

## 2026-09-01 新闻事件基准相对表现阶段

`confirmed`：新闻事件市场反应用例在同一个阻塞数据库任务中读取股票与市场映射指数的永久 `daily_bars`，附加可选 `benchmarkRelative` 证据切片。领域纯函数只按共同合法交易日计算股票变化、指数变化和相对变化，点列上限 120、缺口明细上限 20；前端新增独立类型、Presenter 和面板并严格校验股票身份。

`confirmed`：无指数日线返回 `missing`，不足两个共同交易日返回 `partial`，数据库错误仍保留本地事件事实；不新增网络请求、数据库表、轮询、缓存或第三方依赖，普通网页预览继续保持真实 `unavailable/missing`。

`confirmed`：本阶段最终验证通过：Rust workspace 桌面库 863 项、更新核心 13 项通过（另有 1 项既有性能测试忽略），`pnpm test` 为 195 个 Vitest 文件/729 项，生产构建、1782 条文件登记、3195 个文本文件编码扫描、rustfmt、Vault 验证和 `git diff --check` 均通过。此前遗漏的 `StockEventImpactSnapshot` 合同测试 fixture 已补齐 `benchmark_relative: None`，旧 JSON 反序列化兼容断言仍通过。

`confirmed`：本地预览 `http://127.0.0.1:1420/` 已实际渲染信息总览及 50 个入口；无 Tauri 桥接时真实显示 `unavailable/missing`，控制台 error/warn 为 0，预览标签保持打开，可继续观察后续开发。

## 2026-09-01 事件影响复审与架构登记校准

`confirmed`：事件影响 Store 当前已严格区分未选事件的 `missing` 与非法事件/服务失败的 `unavailable`，现有 7 项 Store 测试和跨层合同通过；`stock_event_impact_metrics` 与 `stock_event_impact_identity` 的注册依赖已核对为实际使用的 `sha2`/无额外依赖。

`confirmed`：架构治理脚本 `check-source-inventory`、`check-file-registry` 已在 YAML/Markdown 双份文件注册表标记为 `active`，架构门禁通过；该记录仅校准记忆，不改变参考项目和用户数据。

`observed`：本地指数覆盖、交易所原子快照、复权因子、完整交易日历和事件因果仍未证明；相对变化不等同超额收益、预测或交易建议。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/stock_benchmark_relative.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/stock_benchmark_relative.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_news_market_reaction.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/StockBenchmarkRelativePanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/news-benchmark-relative-performance-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-news-benchmark-relative-performance.md`。

## 2026-09-01 板块扩散覆盖率分母校准

`confirmed`：今日研判九因子中的板块扩散覆盖率改用行业资金来源声明的 `raw_count` 作为来源总行数；仅当旧快照总行数为零时回退到有效条目数。被丢弃、重复或字段非法的行业行不会从分母中隐去，避免部分覆盖被误报为完整覆盖。

`confirmed`：新增 Rust 领域回归测试覆盖 `raw_count` 大于有效条目的情况；既有上海交易日一致性门禁、60 秒缓存、请求去重、熔断和真实状态语义保持不变。定向市场情绪测试 8 项通过；未新增网络来源、数据库表、轮询或第三方依赖。

`observed`：风险偏好、风格风险偏好和跨交易日周期轨迹仍没有满足同刻、可追溯、跨端稳定要求的直接来源，继续保持真实缺口；行业资金流仍为单一公开来源，不能证明交易所原子快照或因果方向。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/market_sentiment.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-26-market-sentiment.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/verification/feature-parity-matrix.md`。

## 2026-09-01 情绪周期跨交易日观察档案阶段

`confirmed`：第 16“情绪周期”已接入独立跨交易日观察档案。当前九因子形成有效快照后，后端按真实交易日幂等写入既有用户缓存库 `network-cache.sqlite3`，使用隔离前缀 `market-sentiment-history:v1:`，最多保留 30 个点、TTL 180 天；不新增永久业务表、网络请求、后台轮询或第三方依赖。

`confirmed`：前端新增独立 client/store/presenter/panel；Store 合并在途请求、首次订阅只自动读取一次、显式刷新才重取、失败保留 last-good 为 `stale`，页面只比较相邻真实观察点，不补造日期或重算九因子。工作区和功能审计已将板块扩散改为已接入，将跨日轨迹标记为“应用观察档案已接入、完整历史回填仍缺失”。

`confirmed`：最终门禁通过 Rust workspace 873 项、1 项按设计忽略，Vitest 197 个文件/736 项，Vite 3973 个模块生产构建、1795 项文件登记、3208 个文本文件 UTF-8/乱码扫描、rustfmt 和 `git diff --check`；普通网页预览 `http://127.0.0.1:1420/?workspace=sentiment-cycle` 已实际渲染跨日面板与真实空档案状态，控制台 error/warn 为 0。

`observed`：该轨迹只包含应用实际运行后观察到的快照，不是完整市场历史回填，也不证明交易所原子同刻、完整法定交易日历或跨源连续覆盖；风险偏好和风格偏好仍保持真实缺口。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/market_sentiment_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/cache/market_sentiment_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_market_sentiment_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_sentiment_history.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/sentiment-cycle-history-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/SentimentCycleHistoryPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/sentiment-cycle-history-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-sentiment-cycle-history.md`。
## 2026-09-01 市场情绪风险偏好与风格偏好共享横截面阶段

`confirmed`：今日研判新增风险偏好与风格风险偏好两个九因子分项。两项均只使用东方财富 A 股全市场横截面直接字段：风险偏好按上涨/下跌股票成交额方向加权；风格风险偏好按来源流通市值排序形成约三分位小盘/大盘组，再比较两组成交额加权涨跌幅。

`confirmed`：新增共享 `load_market_cross_section` 用例，统一复用四秒内存缓存、请求去重和熔断器。市场异动和今日研判共用同一原始快照；横截面过期时异动只保留已存事件流，不推进游标，今日研判不使用过期横截面计算新分数。

`confirmed`：前端情绪周期 Presenter/面板将两个分项明确标记为“横截面代理”，无 Tauri 服务时仍显示真实 `unavailable/missing`。日期无法核验、来源字段缺失或有效金额分母为零时不生成分数；限制说明保留单一公开来源、非交易所原子快照和非交易建议边界。

`confirmed`：Rust 情绪/异动定向测试、前端 Presenter 测试和 `tests/features/market-sentiment-risk-style-contract.test.mjs` 已加入；文件登记、功能对照和完成审计同步更新。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_market_cross_section.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/market_sentiment.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_sentiment.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_market_movements.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/SentimentCyclePanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-sentiment-risk-style-contract.test.mjs`。

## 2026-09-01 共享横截面合同边界复核

`confirmed`：合同测试已跟随实现边界调整，4 秒缓存、请求去重、熔断、过期回退由 `load_market_cross_section` 统一验证；`load_market_movements` 只验证对共享加载器的调用及异动归档行为，避免测试把实现错误地绑定在业务用例内部。

`confirmed`：最终门禁通过：`pnpm test` 为 197 个 Vitest 文件/737 项，`cargo test --workspace --offline` 为 876 项通过、1 项按设计忽略，Vite 生产构建 3973 个模块，文件登记 1798 项，编码扫描 3213 个文本文件，rustfmt 与 `git diff --check` 通过。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

`observed`：本地预览 `http://127.0.0.1:1420/?workspace=sentiment-cycle` 已保持打开并可继续验收；普通网页无 Tauri 桥接时继续展示真实 `unavailable/missing`，不代表桌面数据服务已启动。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-movements-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-market-sentiment-risk-style.md`。

## 2026-09-01 涨停复盘次日纪律反馈

`confirmed`：第 28“涨停复盘啦”面板新增独立次日反馈 Presenter，复用昨涨停永久日线基线与共享行情快照，按交易日和昨收一致性门禁展示次日开盘、价格反应与成交确认；板块扩散和第二来源交叉确认保持 `missing`。

`confirmed`：面板刷新并发复用 `limitEcology`、`marketMovements`、`previousLimitUps`，展示四项指标、最多 20 条明细和三个来源状态面板；未新增网络源、IPC、数据库表、定时器或重复行情公式。生产构建、定向 Presenter 测试和 Node 合同已通过。

`observed`：普通网页预览没有 Tauri 数据桥接时继续显示真实 `unavailable/missing`；盘后长期冻结、完整板块成员、第二来源同刻确认和交易所原子快照仍缺失，第 28 菜单与产品总体保持 `partial`。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/limit-up-review-next-day-types.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/limit-up-review-next-day-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/limit-up-review-next-day-presenter.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/LimitUpReviewPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/limit-up-review-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-08-27-limit-up-review.md`。

## 2026-09-01 开盘冻结记录自动恢复阶段

`confirmed`：第 42“开盘啦”新增按交易日自动恢复最近冻结记录。后端从既有 `market-open-freeze-archive:v1:` 可重建缓存最多扫描 64 条归档，按交易日过滤、排除过期记录，复用 `valid_record` 完整性校验并选择最新 `frozen_at`；不新增永久业务表、网络来源或后台轮询。

`confirmed`：新增 `load_latest_market_open_freeze` Tauri 命令及前端 `loadLatestMarketOpenFreeze`、Store `loadLatest` 接线。页面仅在共享交易日确认且日期变化时请求一次；Store 合并同日请求、容量上限保持 2，并隔离换日后的迟到响应。无记录为真实 `missing`，桌面桥接失败为 `unavailable`，成功恢复后主检查单继续复用冻结证据信封。

`confirmed`：Rust 恢复用例测试、前端 Store 去重/换日测试、Node 跨层合同、YAML/Markdown 文件登记和第 42 菜单定义已同步；冻结按钮原有显式冻结路径未改变。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

`observed`：竞价字段、委托队列和交易所原子快照仍缺失；恢复的冻结记录只是当前七项可核验事实的时间点封存，不代表开盘方向或交易建议。普通网页预览无 Tauri 桥接时继续保持真实 `unavailable/missing`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/freeze_market_open.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_open_freeze.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-open-freeze-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/MarketOpenPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-open-freeze-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-market-open-freeze-restore.md`。
### 2026-09-01 异动统计跨重启历史阶段

`confirmed`：第 30“异动统计大全”新增独立历史统计 Presenter、类型和面板，复用既有 `marketMovementHistory` Store 查询最多七日的异动归档，可选精确六位股票代码，按交易日、方向和事件明细展示；不新增网络请求、IPC、数据库表或轮询。

`observed`：无日期输入、归档不存在、过期或损坏时继续保持真实 `missing/stale/unavailable`，不会从当前横截面倒推或填充模拟事件。交易所时间戳与多源确认仍未完成，工作区和产品总体保持 `partial`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/movement-statistics-history-types.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/movement-statistics-history-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/MovementStatisticsHistoryPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-movement-statistics-history.md`。

## 2026-09-01 开盘竞价缺口全市场覆盖

`confirmed`：第 42“开盘啦”复用既有共享 A 股横截面请求，在矩阵和异动榜截断前对全部已解析来源行单次遍历，生成固定大小的 `openingGapSummary`，包含有效数、缺失数、正负方向数、平均缺口和五个稳定区间；6000 行股票明细不进入 IPC 或 UI。

`confirmed`：摘要字段为可选 camelCase 合同。新快照优先走全市场摘要，旧 JSON 缺字段时继续走 Presenter 的行级回退；开盘价或昨收缺失、非正或非有限时只计入缺失，不补零。没有新增网络请求、IPC、数据库表、定时器或平台 API。

`confirmed`：聚焦 Rust 4 项、合同 3 项、Presenter 4 项和跨层 Node 合同已通过；第 42 菜单剩余缺口更新为交易所竞价时间戳/委托队列与多源确认，工作区保持 `partial`。

`observed`：公开横截面摘要不等于交易所集合竞价原子快照、撤单轨迹或完整竞价历史；普通网页预览无 Tauri 桥接时保持真实 `unavailable/missing`。参考项目只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/market_movements.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/market/stock_movements.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-open-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/market-open-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-market-open-auction-coverage.md`。

## 2026-09-01 个股历史题材自动加载

`confirmed`：个股观察新增独立 `stock-topic-history-store.ts`，有效股票选定后只调用已有 `load_hotspot_topic_archive` 的本地归档路径（`requestedDate: null`），对归档请求去重并复用 last-good；切股、非法输入和离开页面均清理 Store，不新增网络轮询、数据库表、平台 API 或重复行情请求。

`confirmed`：`stock-topic-history-presenter.ts` 逐日校验归档日期、快照观察时间、股票代码和来源题材原值，只保留同股同日记录并有界合并到事件 K 线；当前题材与归档重叠时去重。状态保持 `ready/partial/stale/missing/unavailable`，空归档不生成事件，不从新闻标题、价格或 AI 推断题材。

`observed`：当前只自动复用应用已经归档的日期，不等于完整跨日历史回填；第二题材来源、交易所级发布时间核验、语义关系和因果识别仍缺失，个股观察与产品总体保持 `partial`。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-topic-history-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-topic-history-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-event-evidence-projector.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/StockObservationPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/StockEventKlinePanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/stock-topic-history-auto-load-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-stock-topic-history-auto-load.md`。

`confirmed`：阶段收尾门禁全部通过：`pnpm test` 为 201 个 Vitest 文件、752 项测试；桌面前端 Vite 生产构建完成 3979 个模块；源码清单、1814 项文件登记、3229 个项目文本文件 UTF-8/乱码扫描、`cargo fmt --all -- --check` 和 `git diff --check` 均通过；Rust workspace 离线测试 878 项通过，1 项既有性能测试按设计忽略。

`observed`：本阶段只复用已有持久化热点题材归档，不等于完整跨日历史回填；第二题材来源、交易所级发布时间核验、语义关系和因果识别仍未接入，个股观察和产品总体继续保持 `partial`。本地网页预览保持运行，普通网页环境无 Tauri 桥接时继续显示真实 `unavailable/missing`，不填充假数据。参考工程只读，未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-01-stock-topic-history-auto-load.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-topic-history-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/stock-observation/stock-topic-history-presenter.ts`。

## 2026-09-01 全局排版可读性治理

`confirmed`：主题层新增统一字号令牌并收敛全局排版基线：正文/控件 14px、辅助信息 12px、三级标题 17px、二级标题 20px、页面标题 28px；保留指标数字的独立强调字号。50 项高密度功能入口保留 13px 专用字号以减少标签截断。通过全局主题层覆盖各面板的过小辅助文字，未修改业务逻辑、数据链路或组件职责。

`confirmed`：Vite 生产构建完成 3979 个模块，全量 `pnpm test` 通过 201 个 Vitest 文件、752 项测试；UTF-8/乱码扫描与 `git diff --check` 通过。浏览器复查个股观察页为 1280/1280，无横向溢出，标题、正文、数据卡和状态文案层级清晰。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/theme.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/verification/feature-completion-audit.md`。

## 2026-09-01 市场脉冲与全站视觉层级修复

`confirmed`：市场脉冲顶部改为主指标、核心指数、关键指标三层布局，解决 1280px 首屏中指数、数据源和情绪信息争抢同一行的问题；固定高度搜索控件升至 32px，避免文字裁切。主题令牌收敛为正文 14px、辅助 12px、标签 13px、面板标题 18px、页面标题 26px，通用指标卡数字为 24px；审计、来源、状态、边界、警告、空态和核验行统一执行 12px 可读下限。

`confirmed`：本轮只修改 `GlobalMarketPulse.svelte` 和 `theme.css` 的表现层，不新增网络请求、IPC、数据库、轮询或平台适配代码；个股观察与公司研究首屏已在本地预览复查，1280x720 个股观察内容区没有低于 12px 的可见文字且无横向溢出。全量 201 个 Vitest 文件/752 项测试、3979 模块生产构建、1814 项文件登记、3229 个文本文件编码扫描和 Vault 验证通过，页面保持真实 `unavailable/missing` 状态。

`observed`：后续新增面板继续复用上述字号令牌，不再新增 8–10px 正文性文字；参考工程保持只读，未执行 Git 写操作，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/theme.css`、`http://127.0.0.1:1420/a-shares?symbol=600519`、`http://127.0.0.1:1420/company-research?preview=latest`。

## 2026-09-01 排版层级二次收敛

`confirmed`：主题层将字号固定为有限的 14/12/13/16/19/27px 层级。内容区普通 `span/time/code/dt/dd` 不得低于 12px；市场条标签和固定高度搜索控件使用 13px；指标数字保留独立强调字号；50 项功能入口维持 13px 以避免标签截断。此次只改 `theme.css`，不改变业务逻辑、数据来源或状态语义。

`confirmed`：桌面前端构建、201 个 Vitest 文件/752 项测试、架构登记（1814 项）、UTF-8/乱码扫描和 `git diff --check` 均通过。参考工程保持只读，未执行 Git 写操作，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/theme.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/verification/feature-completion-audit.md`。
## 2026-09-01 公告详情真实身份与字段展示阶段

`confirmed`：公告交叉验证结果原样透传巨潮公告列表已有的真实公告 ID；前端仅在真实 ID、受信 URL 和股票代码同时存在时启用既有按需正文读取，不再用 URL 充当 ID，也不从 URL 推导 ID。缺少 ID 时保留受信原文入口并显示真实缺口。

`confirmed`：新增独立纯 Presenter，统一投影 `ready/partial/stale/missing/unavailable` 与标题、发布时间、公告编号、正文类型、来源、SHA-256 摘要和截断状态。五态在无正文数据时仍可见，面板正文和辅助字号不低于 12px；未新增网络源、IPC、缓存、数据库、定时器或平台 API。

`observed`：正文实体关系、修订全文差异和市场影响语义仍未完成，新闻菜单与产品总体继续保持 `partial`。参考工程只读，未执行 Git commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/news/news_event.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/announcement-detail-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/AnnouncementDetailPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/announcement-detail-fields-contract.test.mjs`。

## 2026-09-01 并行 agent 统筹与阶段收尾

`confirmed`：本轮按用户授权启用多个并行 agent。事件影响 agent 修复未选中事件的 `missing` 状态语义并复核非法事件仍为 `unavailable`；公告详情 agent 完成真实公告 ID 透传、受信 URL 门禁、加载态与五态字段展示；热点 agent 对第二题材来源进行了只读审计，确认现有东方财富/通达信链路不具备同交易日、同身份安全交叉确认条件，未引入不可靠实现。

`confirmed`：主 agent 统一完成 202 个 Vitest 文件/758 项测试、Rust workspace 878 项通过且 1 项按设计忽略、桌面生产构建 3980 个模块、架构登记 1818 项、UTF-8/乱码扫描、rustfmt 与 `git diff --check`。本地预览 `http://127.0.0.1:1420/news-intelligence` 在 1280x720 复查无横向溢出、可见文字无低于 12px 项、控制台无 error/warn。

`confirmed`：并行审计报告已保存于 `D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/market-hotspot-crosscheck-report.md` 与 `D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/next-sprint-gap-ranking.md`。下一迭代按真实性与性能优先级排序为：08 连板表现跨日核验、09 龙头晋级跨日闸门、20 七大人气榜复用异动归档、15 题材库归档时间线、50 龙虎榜交易日有界翻页。

`observed`：参考工程 `D:/Users/90090/Documents/金融财经` 保持只读；本轮未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。公告正文实体关系、修订全文差异、市场影响语义、第二题材源、交易所竞价队列与完整历史回填仍保持真实 `partial/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/market-hotspot-crosscheck-report.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/next-sprint-gap-ranking.md`、`http://127.0.0.1:1420/news-intelligence`。

## 2026-09-01 数据大屏视口回归修复阶段

`confirmed`：数据大屏进入时强制回到页面顶部，并为外层工作台增加独立视口类；数据大屏在桌面视口使用单视口布局，固定 `100vh`，通过 `min-height: 0`、`max-height: 100vh` 和受限 Grid 行避免内容把外层撑高，从而移除标题被顶出和右侧页面滚动条问题。全屏状态统一使用 `overflow: hidden`；小于 1250px 时恢复自然高度和普通滚动，避免窄屏被硬裁切。

`confirmed`：当前工作树 Web 全量测试为 139 个文件、813 项通过，生产构建通过；便携 EXE 已重新构建到 staged 目录并保留持久化目录。实际 EXE smoke 能启动并进入 API 检查，但在既有量化策略刷新门禁处停止（4326ms 超过 3000ms），该性能阻断与数据大屏视口修复无关，未将其误报为完整 smoke 通过。

`observed`：仍需在用户实际 Windows 最大化窗口中复核投影仪字体比例和显卡渲染差异；量化策略既有 3 秒门禁仍是全量 smoke 的独立阻断项。未控制通达信，未覆盖正在使用的正式 EXE。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/dashboard/Dashboard.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreenViewport.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/docs/superpowers/plans/2026-09-01-data-screen.md`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable-staged-30138a017dc44a02934e65c21f77cb04/XiaoQiBao-Portable/xiaoqibao.exe`。
## 2026-09-01 信息总览五项并行迭代

`confirmed`：本轮按用户授权启用多个并行 agent，完成第 08 连板表现永久日线同股同日核验、第 09 龙头晋级跨日高度闸门、第 20 七大人气榜本地异动归档观察、第 15 题材库归档版本时间线、第 50 龙虎榜交易日有界翻页。所有实现均为独立文件职责，复用既有 Store、缓存和来源，不新增后台轮询，不修改参考项目。

`confirmed`：全量前端测试 202 个文件、768 项通过；Rust workspace 881 项通过、1 项按设计忽略；桌面前端生产构建 3980 个模块通过；架构登记 1818 项、UTF-8/乱码扫描、rustfmt 和 `git diff --check` 通过。未执行 Git commit/stage/push，未生成 EXE、安装包或 ZIP。

`observed`：第 08/09 的严格跨日结论仍受永久日线覆盖、交易日历和多源确认边界约束；第 15/20 仅展示应用实际保存的归档，不等同完整历史或官方榜单；第 50 仍是单一公开来源，超页或超载荷时保持 `truncated/partial`。交易所竞价队列、官方人气、第二题材源、权威席位身份和原子同刻快照继续保持缺口。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/docs/verification/feature-parity-matrix.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/reference-parity-ledger.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/next-sprint-gap-ranking.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/consecutive-limit-performance-report.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/dragon-tiger-pagination-report.md`。

## 2026-09-01 Windows x64 EXE 验收构建

`confirmed`：按用户要求生成当前阶段 Windows x64 release 桌面产物，前端 Vite 生产构建成功（3980 modules），Rust release 同时生成 `yishu-desktop.exe`、`yishu-updater.exe` 和 `yishu-news-collector.exe`。独立验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-120010`；主程序 SHA-256 为 `96E6AD41A5E46AB1729A1A84C03E8229C3D892844DAFDB1D2109435B4B94661C`。

`confirmed`：主程序启动烟测持续运行 8 秒后由主 agent 主动结束，未出现启动即退出；情绪周期历史、放量突破及放量突破跨日轨迹定向 Vitest 12 项、两个 Node 合同测试均通过。未生成安装包或 ZIP，未修改参考工程，未执行 Git commit/stage/push。

## 2026-09-01 便携版旧版本启动根因与更新切换修复

`confirmed`：排查确认金融财经工作树正式便携目录 `dist/XiaoQiBao-Portable` 当时被旧版进程占用，构建脚本因此按保护策略将新版本放到 staged 目录并写入 `pending-update.json`；旧版 EXE 与最新 staged EXE 的 SHA-256 不同，用户若继续启动旧正式目录会看到旧版本。

`confirmed`：修复 `qibao_desktop/entrypoint.py`：启动时自动把延期清单 `pending-update.deferred.json` 原子恢复为 `pending-update.json`，让旧进程退出后后续启动可以重试更新；更新成功后清理旧延期清单，避免新版本切换后再次排队旧版本。新增回归测试覆盖两条行为，桌面入口/更新测试 21 项通过，前端全量测试 139 文件、813 项通过，生产构建与 `git diff --check` 通过。

`confirmed`：最新便携 EXE 已构建到 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable-staged-b10356fcbd3c4eada7699b5217ff2d20/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 为 `49C17C43DBA9E1280A8F12E9BEB2AE726DB43C7B24C574C7129882A165C7694B`。正式目录保持未覆盖，当前 `pending-update.json` 指向该 staged 版本；用户需先正常退出当前旧程序，再从正式目录启动一次，更新助手会自动完成切换。

`observed`：暂存版实际启动并创建窗口；完整便携 smoke 在公司研究数据源请求超时处停止，不能据此宣称所有数据菜单均已通过。未关闭通达信，未强制结束用户进程，未删除任何持久化目录或数据。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/api/src/qibao_desktop/entrypoint.py`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/api/tests/desktop/test_entrypoint.py`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable-staged-b10356fcbd3c4eada7699b5217ff2d20/XiaoQiBao-Portable/xiaoqibao.exe`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/docs/superpowers/plans/2026-09-01-data-screen.md`。

## 2026-09-01 第49低位放量跨日轨迹增强

confirmed：低位放量 Presenter 与面板新增会话内真实多日轨迹，按同一股票的实际快照交易日展示区间位置和量能倍数变化；只有至少两个真实交易日点才可比较，单日保持 missing，不补造历史日期。

来源：D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/low-position-volume-presenter.ts、D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/LowPositionVolumePanel.svelte、D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/low-position-volume-trajectory-report.md。

## 2026-09-01 Windows x64 阶段性 EXE 复验构建（13:07）

`confirmed`：包含第27龙头梯队会话内跨日状态链的最新源码已完成 Rust release 构建，生成 `yishu-desktop.exe`、`yishu-updater.exe` 和 `yishu-news-collector.exe`，独立验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-130708`。

`confirmed`：主程序启动 8 秒后保持存活；主程序 SHA-256 为 `51DAA01BCB2454A39FAB27673824E0432A490F4B7E53214DC4642D8B590F6008`。本阶段未生成安装包或 ZIP，参考项目与用户数据目录未触碰，未执行 Git commit/stage/push。

`observed`：该产物用于当前阶段验收，不代表所有远程数据源在任意网络环境下均为 `ready`；现有 `partial/stale/missing/unavailable` 状态边界保持不变。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-130708/yishu-desktop.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

## 2026-09-01 Windows x64 阶段性 EXE（13:51）

`confirmed`：第20历史异动边界复核、第15题材归档时间线和第50龙虎榜有界翻页整合后，Windows x64 release 三可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-135152`。主程序启动 8 秒保持存活，SHA-256 为 `04D81D54F570ADF2E753F8A98F1CF86A4BB382D9BE8EC3A5151A3135CDC6E0BB`；未生成安装包/ZIP，参考工程和用户数据目录未触碰。

## 2026-09-01 Windows x64 阶段性 EXE 复验构建

`confirmed`：在第49低位放量跨日轨迹接入后，重新完成前端 Vite 生产构建（3980 modules）与 Rust release 构建，生成独立 Windows x64 验收目录 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-124328`，包含 `yishu-desktop.exe`、`yishu-updater.exe` 和 `yishu-news-collector.exe`。主程序 SHA-256 为 `684555C793592F927ECFC8DC92A60726BDF144279C0601CD364C5F26A4BCF289`。

`confirmed`：主程序启动 8 秒烟测保持存活；更新助手成功切换与失败回滚烟测通过；低位放量合同测试通过、Vitest 202 个文件/775 项通过；架构登记 1818 项、编码扫描 3244 个文本文件、rustfmt 和 `git diff --check` 通过。未生成安装包或 ZIP，未修改参考工程，未执行 Git commit/stage/push。

`observed`：本产物是阶段性验收 EXE，不代表所有远程数据源在任意网络环境都 ready；真实 `partial/stale/missing/unavailable` 边界保持不变。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-124328/yishu-desktop.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/low-position-volume-contract.test.mjs`。

## 2026-09-01 第49低位放量跨日轨迹增强

confirmed：低位放量 Presenter 增加会话内真实多日快照轨迹，按同股实际交易日展示区间位置和量能倍数变化，最多保留 30 个观测日；单日或无后续真实点保持 missing，无网络、轮询或数据库新增。

来源：D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/low-position-volume-presenter.ts、D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/LowPositionVolumePanel.svelte、D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/low-position-volume-trajectory-report.md。

## 2026-09-01 第49低位放量跨日轨迹增强

confirmed：低位放量新增会话内真实多日快照轨迹，按同股实际交易日显示区间位置与量能倍数变化，最多 30 个观测日；无效/重复日期剔除，单日或无后续点保持 missing，不补造历史、不新增网络/轮询/数据库。

来源：D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/low-position-volume-presenter.ts、D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/LowPositionVolumePanel.svelte、D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/low-position-volume-trajectory-report.md。
## 2026-09-01 Windows x64 阶段性 EXE（14:01）

`confirmed`：按用户验收请求重新构建当前最新源码。前端 Vite 生产构建完成 3981 个模块，Rust release 生成 `yishu-desktop.exe`、`yishu-updater.exe` 和 `yishu-news-collector.exe`，独立验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-140121`。

`confirmed`：主程序启动 8 秒保持运行后由验收脚本正常结束；主程序 SHA-256 为 `9A4D298B05730BFFEB2106C0F40F9D10071F4B58E1EE885B6B79ADF4720874CD`，更新助手 SHA-256 为 `11306F33FAAFD350BC9CACB61AF9182F68EC822C808B6FBEDE203AD1FB94A55D`，后台快讯采集器 SHA-256 为 `978F1B4A6916E88F907C2AD4D7F613E9B8E8A6A70579E255176AD56CF81ED19C`。本次仅生成阶段性 EXE，不生成安装包或 ZIP；参考工程及用户数据目录未触碰，未执行 Git commit/stage/push。

`observed`：该产物用于当前阶段 Windows 验收，不代表所有远程数据源在任意网络环境下均为 `ready`；既有 `partial/stale/missing/unavailable` 边界保持不变。

## 2026-09-01 Windows x64 阶段性 EXE（14:25）

`confirmed`：按用户验收请求重新生成当前工作区 Windows x64 阶段性三件套。前端 Vite 生产构建 3982 个模块通过；Rust release 构建生成 `yishu-desktop.exe`、`yishu-updater.exe` 和 `yishu-news-collector.exe`，独立验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-142538`。主程序启动 8 秒保持存活，主程序 SHA-256 为 `9A4D298B05730BFFEB2106C0F40F9D10071F4B58E1EE885B6B79ADF4720874CD`。

`confirmed`：本次新增龙头梯队跨重启归档文件已登记到 YAML/Markdown 双份文件注册表；定向归档、跨日 Presenter 测试 3 个文件共 11 项通过；Rust workspace 881 项通过、1 项既有性能测试按设计忽略；架构登记 1823 条、编码扫描 3252 个文本文件、rustfmt 和 `git diff --check` 通过。

`observed`：该阶段性 EXE 只用于当前 Windows 验收，未生成安装包或 ZIP；未修改参考项目和用户数据目录，未执行 Git commit/stage/push。远程来源继续按真实 `partial/stale/missing/unavailable` 状态呈现；龙头梯队归档只覆盖应用实际运行期间观察到的快照，不等同未运行期间完整历史回填。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-142538/yishu-desktop.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/leader-tiers-cross-day-archive.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

## 2026-09-01 第47/49轨迹日期校验与 Windows x64 阶段性 EXE（14:51）

`confirmed`：放量突破与低位放量轨迹 Presenter 改为严格年月日校验，拒绝 `2026-02-31` 等不存在日期；新增低位放量回归测试。全量前端 204 个 Vitest 文件、788 项测试通过，前端生产构建 3982 个模块，Rust workspace 881 项通过、1 项按设计忽略，架构登记 1823 条，编码扫描 3253 个文本文件，rustfmt 与 `git diff --check` 通过。

`confirmed`：Windows x64 三可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-145112`：主程序 `yishu-desktop.exe` SHA-256 `F684114A74D61533BF1BF48E821B896CECCF0E29D309241C79066A9B16E86FFC`，更新助手 `4F0547EFCB5CFA7654934B764FA48DC6331D2F156B74B058C755B5D4C925C8A5`，后台快讯采集器 `130F81FACE4F328BEB595104B12C5B7D2FECE3E879C1ECBF8CAD9B0005F08CF7`。主程序独立启动 8 秒保持存活；未生成安装包或 ZIP，未修改参考项目或用户数据目录，未执行 Git 写操作。

`observed`：阶段性 EXE 仅证明本机构建与启动稳定，远程来源继续按真实 `partial/stale/missing/unavailable` 状态呈现，不代表所有菜单在任意网络环境下均为 `ready`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/volume-breakout-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/low-position-volume-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-145112/yishu-desktop.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

## 2026-09-01 第15题材库时间线真实性修复与 Windows x64 阶段性 EXE（15:07）

`confirmed`：第15题材库版本时间线先去重有效归档日，以最早日为基线；只有至少两个不同真实交易日才计算题材/成员变化，单日归档返回空时间线，Store 局部状态为 `missing` 并提示缺少跨日事实。定向 12 项与全量前端 204 文件/790 项通过；生产构建 3982 个模块，Rust workspace 881 项通过、1 项按设计忽略，架构登记 1823 条，编码扫描 3254 个文本文件，rustfmt 与 `git diff --check` 通过。

`confirmed`：Windows x64 三可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-150748`；主程序 `yishu-desktop.exe` SHA-256 `1DC1C47F589E097CF4E4A93B3A022860D498E78BF31A2881E3216CC4D27167E4`，更新助手 `6B09DB9FCD25E8484EC96188061EFA9F7D4E658544D2FB882DF18C7807C76F72`，后台快讯采集器 `192C166EBBAA7D2E024AAA91486580A2884FD57D98A64A79A97B4D749D05AC9A`。主程序启动 8 秒保持存活，未生成安装包或 ZIP，未修改参考项目或用户数据目录，未执行 Git 写操作。

`observed`：第二题材来源、逐条新闻关系、未运行期间完整自动归档、交易所级时间核验和官方全市场人气排名仍缺少安全事实源，相关工作区继续保持 `partial`。

## 2026-09-01 Windows x64 阶段性 EXE（15:19）

`confirmed`：当前源码重新完成前端生产构建与 Rust release 构建。前端 3982 个模块成功，Rust workspace 881 项通过、1 项按设计忽略；架构登记 1823 条、编码扫描 3254 个文本文件、架构验证通过。三个 Windows x64 可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-151902`：`yishu-desktop.exe` SHA-256 `55A9490A30ACDD2EFF52668E34B876391F8960FD1D4962FD7890C235E55FFC0F`，`yishu-updater.exe` `617976783F073E17EDD25144522A75F184F1D83A849BFDAA02F9B6DD6B09E94D`，`yishu-news-collector.exe` `BCDC7E320D290B2E6A83D1F448CB78A7B0B0BBE82EF814F3DD58DB4C4CF7525E`。主程序独立启动 8 秒保持存活后正常结束，未残留进程。

`observed`：本次仅生成阶段性 EXE，不生成安装包或 ZIP；参考工程及用户数据目录未触碰，未执行 Git commit/stage/push。该产物证明当前本机构建和启动稳定，不代表所有远程来源在任意网络环境下均为 `ready`，既有 `partial/stale/missing/unavailable` 边界保持不变。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-151902/yishu-desktop.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-151902/yishu-updater.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-151902/yishu-news-collector.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-hotspot-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/theme-library-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-150748/yishu-desktop.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/event-evidence-next-gap.md`。

## 2026-09-01 数据大屏 C3 投影布局完成

`confirmed`：金融财经工作树的数据大屏完成 C3 布局收敛。主网格采用左侧市场广度、中部三段 ECharts、右侧板块与选股的紧凑三栏结构；顶部通栏补充上证指数、深证成指、创业板指、两市成交额、上涨/下跌、涨停/跌停、北向资金状态和市场阶段；北向资金在当前响应未提供时明确显示“当前来源未提供”，未伪造数值。指数图表增加可读的三大指数摘要条，避免关键信息只存在于图形内部。

`confirmed`：图表动态导入在 DataScreenView 测试中使用隔离 mock，保留生产 ECharts 能力并消除 jsdom 动态模块等待。前端全量 139 个测试文件、816 项通过，TypeScript 和 Vite 生产构建通过；便携 EXE 已重建，SHA-256 为 `6D099FF040783EDC0976FCBD08DEF7EC985A65F5FBF9D8CF7B15F75C17C09FDF`。冷启动便携烟测通过：窗口 104ms 可见、API 3000ms 就绪、14/14 菜单性能门禁通过、验证总耗时 9434ms，退出后无残留 `xiaoqibao.exe`。

`observed`：烟测环境的通达信专业模块、量化策略、来源健康和北向资金仍按真实 `unavailable/partial` 状态呈现；公司研究请求约 4783ms 后返回 partial，未设置 10 秒硬超时。数据大屏尚需在用户实际投影仪和最大化窗口中复核视觉比例；ECharts 供应商包仍较大，后续可继续做缓存和分包优化。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenCharts.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/release/XiaoQiBao-Portable/release-manifest.json`。

## 2026-09-01 数据大屏 C3 字段贯通与最终便携版复验（15:25）

`confirmed`：数据大屏继续按 C3 规格交付：顶部市场指标、左侧行业板块与条件命中、中央三段 ECharts、右侧可编辑选股条件与结果、底部实时快讯；保留暗黑科技视觉、扫描线、粒子网格、流光呼吸、数字跳动、行闪烁和新闻新到高亮。后端 `OverviewFeatureStock` 新增可选真实字段 `volume_ratio`、`turnover_rate`、`market_cap_yi`，由 TDX 本地行情对象贯通到前端 Presenter；条件筛选在启用字段条件而来源缺失时不再错误放行，明确按未命中处理，结果保持 `--` 事实边界。

`confirmed`：定向 DataScreen/Layout 测试 2 文件 26 项通过；全量前端测试 139 文件、816 项通过；TypeScript 通过；API 市场概览合同测试 41 项通过；Vite 生产构建通过；便携构建成功。最终 EXE 位于 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `04CDB8A536B67229110495C7D7D65C408344529CA46289E25A0719617973172B`。冷启动烟测通过：窗口 290ms 可见、API 5776ms 就绪、14/14 菜单性能通过、验证总耗时 16865ms，退出后无残留 `xiaoqibao.exe`；持久化目录 `config/data/news/cache/logs/models/exports/backups` 均保留。

`observed`：烟测环境仍显示 TDX 专业模块不可用、市场覆盖为 `partial`，北向资金因当前响应未提供保持“当前来源未提供”；这些是来源事实边界，不以模拟数字替代。未关闭通达信、未删除用户数据、未生成独立 HTML 交付物。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/api/src/qibao_api/contracts/market_overview.py`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/api/src/qibao_api/gongbu/tdx_local_overview.py`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/presenter.ts`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-01 数据大屏最终规格复验（15:31）

`confirmed`：顶部核心指标带已收敛为 68px 紧凑通栏，配合页面头部与底部 120px 新闻通栏；C3 主体继续保持 28fr/44fr/28fr 三栏。选股条件说明改为“仅对来源已提供字段进行筛选；缺失字段不会误判为命中”。

`confirmed`：定向 DataScreen/Layout 测试 26 项通过，Vite 生产构建通过，最终便携版重建完成。冷启动烟测通过：窗口 369ms 可见、API 5791ms 就绪、14/14 菜单性能通过、验证总耗时 17278ms，退出后无残留进程。最终 `xiaoqibao.exe` SHA-256 为 `9CC458BD7C969830C63F0AE4DF49259A73AB20244BDC891A12D2DFE0B1057F0D`；`config/data/news/cache/logs/models/exports/backups` 均保留。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-01 数据大屏展示模式收敛与右侧面板替换（16:00）

`confirmed`：数据大屏按“固定展示、无需设置”的投影场景调整。导航标题区加高至 68px；顶部行情指标带保持加高；中央指数摘要条增加上下留白和卡片高度；左侧行业板块区压缩板块强弱间距，同时放宽尾盘候选与今日涨停条目高度。右侧原“选股条件/选股结果”设置区替换为固定的“资金与市场强度”和“行业资金流向”两块展示，分别呈现成交额、涨跌家数、涨跌停生态、市场阶段、板块净流入和大单方向。

`confirmed`：TypeScript、数据大屏定向测试 8 项、生产构建通过；便携版已重新生成。冷启动烟测通过：窗口 104ms 可见、API 2996ms 就绪、14/14 菜单性能通过、验证总耗时 9520ms，退出后无残留进程。最终 EXE SHA-256 为 `995E947B35B57853C6B23E5C837D3AAA1E5BD670C150DE118F5EDC22E34F3828`，路径为 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`；持久化目录保持不变。

`observed`：真实数据源缺失时，资金流向和北向资金继续按真实不可用状态展示，不补造数字；用户应通过上述 EXE 运行新版本。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-03 市场统计指标移入顶部

`confirmed`：数据大屏顶部 KPI 已按盯盘优先级重新排列，在“涨停 / 跌停”之后、“北向资金”之前新增“平盘家数”和“炸板数量”；左侧原“市场统计”框架已移除，避免重复展示和占用空间。顶部栅格同步调整为 11 列，并为窄屏保留 6 列、3 列响应式布局。

`confirmed`：数据大屏定向回归 31 项、前端全量 Vitest 139 个文件/843 项通过；Vite 生产构建、UTF-8/乱码扫描与 `git diff --check` 通过。最新便携版 EXE 为 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `F6A684EF76EB3CE134ED66D3B2924B28218D683A502E232487B4CB66CCF43C4F`。冷启动烟测窗口 74ms 可见、API 4810ms 就绪、完整验证 12391ms 完成，退出后无 `xiaoqibao.exe` 残留；14 菜单性能检查通过。

`observed`：烟测中的部分真实数据源仍可能返回 `unavailable/partial`，这是数据源边界，不影响本轮 KPI 布局调整；未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`confirmed`：交付前复验再次通过：数据大屏回归 31 项、前端全量 139 个文件/843 项、Vite 生产构建和便携版冷启动烟测均为成功；本次烟测窗口 82ms 可见、API 4856ms 就绪、完整验证 12925ms 完成，14 菜单性能检查通过，退出后无残留进程。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-03 行业资金流向独立双列固定展示

`confirmed`：数据大屏右侧将“行业资金流向”从实时资讯内容区拆为资讯下方的独立面板，固定两列五行共 10 个展示位；真实数据按当前排序取前 10 条，少于 10 条时补齐“等待数据”占位，超过 10 条不再挤压版面。资讯区仅保留实时新闻与量化命中/尾盘选股，三者职责和视觉边界清晰。

`confirmed`：新增回归覆盖独立区域、两列五行、超过 10 条截断和不足 10 条占位；前端全量 Vitest 139 个文件/842 项通过，Vite 生产构建通过。便携版已重建至 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `BC0915201E712ABDD1932F4157C1F00DCD0940B12DD528B08587DF1EC7E8FD55`；冷启动烟测通过，窗口 69ms 可见、API 4441ms 就绪、完整验证 13043ms 完成，退出后无 `xiaoqibao.exe` 残留。

`observed`：烟测中的部分真实数据源仍可能为 `partial/unavailable`，这属于数据源边界；本轮未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-02 21:29 最新 Windows x64 阶段验收

`confirmed`：基于当前信息总览视觉密度、响应式成分股展示和动效优化源码，完成 EXE-only release 构建。验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-212927`，包含 `yishu-desktop.exe`（33,264,640 bytes，SHA-256 `B18220DB1365EE7ECB9F286D96A3EAE1F49FA9C17C273704105835277AB33993`）、`yishu-updater.exe`（675,840 bytes，SHA-256 `4626CC86BFD568955D6F6A128428A70CD8C269D01710AC8AB9C82DEEE206FDE8`）和 `yishu-news-collector.exe`（7,112,192 bytes，SHA-256 `39819804AFBC61F2B08D7CBEF14754DC3CBD14EDF4F2C18A24A0E9420C394993`）。主程序 PE machine 为 `0x8664`。

`confirmed`：前端全量 Vitest 218 个文件/876 项通过；Vite 生产构建 4025 个模块通过；视觉合同、架构登记（1896 条）、UTF-8 编码扫描（4642 个文本文件）、`cargo fmt --all -- --check` 与 `git diff --check` 均通过。主程序从独立验收目录启动 3000ms 后进程存活且主窗口句柄有效，终止后无同路径残留进程。未生成安装包或 ZIP，未修改参考项目、用户配置、缓存或业务数据库，未执行 Git stage/commit/push。

`observed`：Rust release 保留既有 unused/deprecated/linker warnings，不影响构建退出码；完整远程数据覆盖、交易所级逐笔、完整 AI 供应商可用性和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewSectorBoard.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewWorkspaceSummary.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewWorkspaceNav.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewWorkspaceHub.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-212927/BUILD-INFO.txt`。

## 2026-09-02 21:00 总览刷新契约与 Windows x64 EXE

`confirmed`：总览刷新控制器新增 `setRefreshInterval`，同一刷新秒数显式转发至市场脉冲和共享异动 Store；异动 Store 只写入共享 `refreshPreferences`，保留既有可见性门控、请求去重、快讯/热点下限和五态证据语义。总览 Hub 的设置加载成功与失败分支均通过控制器设置间隔，消除对 `marketPulse` 旁路副作用的隐式依赖。

`confirmed`：定向控制器/异动 Store 8 项、前端全量 Vitest 218 文件/876 项、仓库合同、TypeScript/Vite 构建、架构登记 1896 条、UTF-8 扫描 4642 个文本文件和 `git diff --check` 通过。基于当前源码完成 Windows x64 EXE-only release，验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-210054`，包含主程序、更新助手、后台快讯采集器和 `BUILD-INFO.txt`；主程序 SHA-256 `5AB4FD78EC1A207E6DD4E99CE6CFF66614E6C1FBAA0E1B245CC332E25EF298AC`，PE machine `0x8664`，独立启动 2000ms 后清理无残留进程。

`observed`：Rust release 仍有既有 unused/deprecated/linker warnings；完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入、macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。参考工程、用户配置、缓存、业务数据未修改，未执行 Git stage/commit/push，未生成安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/overview-refresh-controller.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/market-movements-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-210054/BUILD-INFO.txt`。

## 2026-09-02 20:42 当前源码 Windows x64 阶段 EXE

`confirmed`：基于总览摘要折叠、导航可读性和移动端板块表格收口后的当前源码完成 `scripts/build-windows-exe.ps1` EXE-only release 构建。验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-204240`，包含 `yishu-desktop.exe`、`yishu-updater.exe`、`yishu-news-collector.exe` 与 `BUILD-INFO.txt`，未生成安装包或 ZIP。主程序 33,264,640 bytes，PE machine `0x8664`，SHA-256 `480205D2998599E72388AC4082F4287CCC6A1D7E1744DE4C8D34D0D9B3233FE8`；更新助手 SHA-256 `142B15561B9653D0FCCE403B9D215F6964A27FBC40360CEF13CCCE3460866C7F`；后台采集器 SHA-256 `116B1444A20C886D1BCBBBFA38C0474180ACB06D27A7720EAD9AF08E75585BF7`。

`confirmed`：前端 Vitest 218 个文件/874 项通过；架构登记 1896 条、UTF-8 编码扫描 4642 个文本文件、Windows EXE-only 合同、`cargo fmt --all -- --check` 与 `git diff --check` 通过。主程序从独立验收目录启动 2500ms 后进程存活且主窗口句柄有效，终止后无残留同名进程。未修改参考项目、用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：Vite/Rust release 保留既有未使用代码、弃用 API 与无效 CSS 选择器警告，不影响退出码 0；完整远程数据覆盖、完整 AI 供应商可用性、交易所级逐笔和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewWorkspaceSummary.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewWorkspaceNav.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewSectorBoard.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-204240/BUILD-INFO.txt`。

## 2026-09-02 20:21 当前界面优化后 Windows x64 EXE 验收

`confirmed`：基于信息总览标签化导航、默认折叠说明、响应式卡片/表格和动效优化后的当前源码，重新执行 `pnpm --filter @yishu/desktop build` 与 `scripts/build-windows-exe.ps1`，前端 Vite 处理 4025 个模块，Rust/Tauri release 构建退出码均为 0。验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-202152`，包含 `yishu-desktop.exe`（33,264,640 bytes，SHA-256 `3745DE67C89B6AD1E8B44E1581051DC1C268F1352E081ADEEBCB3054A1C10555`）、`yishu-updater.exe`（675,840 bytes，SHA-256 `534E246E8758AAC52B09EB25C9B08617E274BDC9CE1CCDECEAE5E453495568D7`）和 `yishu-news-collector.exe`（7,112,192 bytes，SHA-256 `080F661C53024CF236F03BD43D2DF98C271307E844BB5272D5B7180463072C49`），仅生成 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP。

`confirmed`：三个 PE 文件均为 `0x8664`；主程序从独立验收目录启动 3 秒后进程存活、主窗口句柄有效且标题为“一树-A股观测台”，终止后无残留同名进程。Windows EXE-only 合同、文件登记（1896 条）、UTF-8 编码扫描（4641 个文本文件）和 `git diff --check` 均通过。参考项目、用户配置、缓存、业务数据未修改，未执行 Git stage/commit/push。

`observed`：release 编译保留既有 Rust unused/deprecated/linker warnings，不影响构建退出码；完整远程数据覆盖、完整 AI 供应商可用性、交易所级逐笔和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/theme.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewWorkspaceHub.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-202152/BUILD-INFO.txt`。

## 2026-09-02 19:27 新闻降噪与日历恢复后的 EXE 验收

`confirmed`：新闻来源详情默认折叠与交易日历重启 stale 快照恢复后的最新 Windows x64 EXE-only 产物位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-192719`。主程序 32,891,904 bytes，更新助手 675,840 bytes，后台采集器 7,120,384 bytes；SHA-256 分别为 `5A2F7DFECF12F7F849FF7E93F0C520A86D3994A1FA26207A12BAFE97807DF3F3`、`9387A251FA5C6E5D088ACA03C451895BF9112BCA6F8221D4B4439B1A70E91F64`、`6FD9AC7C58214EF0AC967EC5F04DDE2DB0FBB99E68EE370C55E1590143F70CE0`；三个 PE machine 均为 `0x8664`。

`confirmed`：主程序独立启动 3 秒后窗口句柄有效，清理后无残留进程；Windows EXE-only 合同通过。目录未包含安装包或 ZIP，参考项目保持只读，用户配置、缓存和业务数据未触碰，未执行 Git stage/commit/push。

`observed`：该 EXE 只代表当前源码的可启动阶段验收，不代表所有远程数据源、完整 AI 供应商或 macOS 实机验证已完成；这些能力继续保持真实状态边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-192719/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`。

## 2026-09-02 第 29 复盘统计可比性审计

`confirmed`：第 29“复盘统计大全”新增同日/时间可比性 Presenter 结果与紧凑 UI 摘要。它只比较四路已有证据的真实交易日和观测时间；同日且时间可解析才标记“可按同日比较”，错日、缺日期、缺时间、非法时间、stale、missing、unavailable 分别保留明确边界，不宣称原子快照或盘后冻结。

`confirmed`：定向 Vitest 9 项、TypeScript、Node 合同通过；未新增网络、IPC、计时器、数据库或依赖。参考工程只读，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/review-statistics-types.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/review-statistics-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ReviewStatisticsPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/review-statistics-contract.test.mjs`。

## 2026-09-02 新闻来源降噪与交易日历重启恢复

`confirmed`：新闻来源页面首屏改为聚合摘要，来源网格和矩阵放入默认折叠的来源详情，查询前不再堆叠空占位卡；合同与相关 Vitest 测试通过，既有数据请求和五态状态语义未改变。

`confirmed`：交易日历跨进程恢复允许使用未过期或过期不超过 7 天、且 JSON、SHA-256 与身份校验均通过的持久快照；超过 7 天或非法过期值拒绝恢复。定向 Rust 测试 18 项通过。

`observed`：恢复窗口只为重启后的短期连续性，不能替代远程刷新；完整来源覆盖、未发布年度和 macOS 实机验证仍保留真实 `partial/stale/missing/unavailable` 边界。参考项目只读，未执行 Git 写操作，未生成安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/news/NewsPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/news-source-status-matrix-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_trading_calendar.rs`。

## 2026-09-02 交易日历年度覆盖状态修复

`confirmed`：SSE/SZSE 年度日历的状态判定改为按请求窗口和涉及自然年度计算。快照覆盖请求起止日期且覆盖每个涉及年份全年时为 `ready`；跨年缺少任一年时为 `partial` 并保留 `calendar_year_coverage`。新增 3 项回归测试，交易日历定向测试 16 项通过。

`observed`：未发布年度、临时公告修订和 macOS 实机验证仍保持真实缺口；本轮未修改参考工程、用户数据或数据库，未执行 Git 写操作。

`confirmed`：交易日历年度覆盖修复后的最新 Windows x64 EXE-only 预览位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-192719`。主程序 32,891,904 bytes，PE machine `0x8664`，SHA-256 `5A2F7DFECF12F7F849FF7E93F0C520A86D3994A1FA26207A12BAFE97807DF3F3`；独立路径启动 3 秒窗口有效，清理后无残留进程。未生成安装包或 ZIP。

## 2026-09-01 数据大屏标签化与异动雷达迭代（16:30）

`confirmed`：行业板块由方格列表改为标签式卡片，显示板块名称、涨跌幅、领涨股和涨跌家数，并加入错峰入场、呼吸辉光和扫光效果；原“条件命中个股”替换为固定“盘中异动雷达”，优先展示真实异动事件，缺少异动时回退到实时快讯，关联股票代码可点击打开。

`confirmed`：定向 DataScreen/Layout 测试 26 项通过，TypeScript 和 Vite 生产构建通过；便携 EXE 重新生成并完成冷启动烟测，窗口 94ms 可见、API 2884ms 就绪、14/14 菜单性能通过、总验证 8283ms，退出后无残留 `xiaoqibao.exe`。最终 EXE SHA-256 为 `F9664B5BA34D44AC446A3FF36F1DC818194BA55B5A07C698CDDAF56B26294CCA`，路径为 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

`observed`：数据源缺失时仍按真实 `partial/unavailable` 状态展示，不使用模拟异动或伪造市场数字。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-01 数据大屏滚动与图表完整性修复（16:50）

`confirmed`：中央“指数与市场图表”改为摘要条固定、三段 ECharts 按父容器剩余高度 flex 分配，修复底部图表被 `height: 100%` 叠加和父级溢出隐藏裁切的问题；图表段增加独立呼吸辉光，不改变真实数据。

`confirmed`：尾盘候选和今日涨停由固定 4 条改为每页 8 条，数据超过 8 条时按真实候选池轮换并显示当前窗口范围；盘中异动雷达统一使用真实异动/快讯池，每页 4 条轮换并显示总量与窗口范围，不再静态截断。

`confirmed`：底部新闻改为复制轨道的垂直无缝向上循环；鼠标 hover 暂停，条目保留新到高亮和淡入位移动效。页面新增不遮挡业务内容的四角几何全息装饰，保留暗色网格、扫描线、粒子与卡片呼吸效果。

`confirmed`：数据大屏定向测试 5 项通过；前端全量 139 个测试文件、816 项通过；TypeScript、Vite 生产构建、UTF-8/乱码扫描和 `git diff --check` 通过。便携 EXE 已重建并通过冷启动烟测：窗口约 95ms 可见、API 约 2980ms 就绪、14/14 菜单性能门禁通过、退出后无残留 `xiaoqibao.exe`。

`observed`：烟测隔离环境中的来源健康、量化策略、北向资金和通达信专业模块仍按真实 `partial/unavailable` 显示；公司研究返回 `partial`，未伪造行情或数据完整性。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`、本轮前端测试、生产构建和便携烟测输出。

## 2026-09-01 板块标签与行业资金流向增强（17:00）

`confirmed`：板块强弱标签动效改为高对比度扫光、底部能量条和呼吸辉光，投影环境下可见；行业资金流向按板块代码去重，不再把历史采样重复显示为“非金融”等重复行。

`confirmed`：行业资金流向现在展示主力净额、大单净额、超大单净额、相对上次采样变化、采样次数、更新时间、来源和动态强度条；超过 6 个板块时局部轮换，底部大单卡片补充股票代码、方向和净额。

`confirmed`：新增 Presenter 去重与最新拆分回归测试；定向测试 9 项通过，TypeScript、Vite 生产构建和 `git diff --check` 通过。便携 EXE 已重建并完成冷启动烟测：窗口约 90ms 可见、API 约 2856ms 就绪、14/14 菜单性能门禁通过，退出后无残留 `xiaoqibao.exe`；最新 EXE SHA-256 为 `F76A408D7ABDED570BF777FFFAEA1A7053BF903165ACE1BF9A2F4E751E2C25B7`。

`observed`：烟测隔离环境仍将来源健康、量化策略、北向资金和通达信专业模块如实标记为 `partial/unavailable`，不使用模拟数字替代；Vault 校验脚本对历史乱码、依赖 README 和旧文档存在既有告警，本轮新增记忆文本未发现乱码。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/presenter.ts`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/types.ts`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/presenter.test.ts`。

## 2026-09-01 数据大屏顶部框架加高复验（16:20）

`confirmed`：针对投影截图中的顶部框架过窄问题，标题导航区加高至 88px，顶部行情指标区加高至 100px，指数摘要卡增加内边距；左侧板块强弱、尾盘候选、今日涨停重新分配间距，避免上松下挤。右侧保持固定展示型资金与行业流向面板，不恢复设置表单。

`confirmed`：定向布局测试 26 项通过，TypeScript 与生产构建通过；便携 EXE 已重建。冷启动烟测通过：窗口 119ms 可见、API 2999ms 就绪、14/14 菜单性能通过、验证总耗时 9491ms，退出后无残留进程。最终 EXE SHA-256 为 `81996032046BADA429B0DCEB8D1072100729FC86C1184933BCE4493E1EBB5313`，路径为 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

`observed`：真实环境中的通达信专业模块、北向资金或板块流向若未提供，界面继续显示真实不可用状态，不以模拟数值替代。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-01 问财选股偏好持久化与 Windows x64 阶段性 EXE（15:55）

`confirmed`：第38问财选股工作区新增规则、排序和方向偏好持久化。前端启动时读取现有用户设置，应用规则、重置条件及排序/方向变化通过串行保存队列写回；TS 与 Rust 均对白名单字段、有限数值、规则数量和枚举做归一化，缺失字段兼容旧配置并回退默认值。未新增网络请求、轮询、数据库表或假数据。

`confirmed`：定向 Vitest 15 项、Node 问财选股合同、Rust 设置 4 项通过；全量前端 204 个文件/793 项通过；Rust workspace 881 项通过、1 项按设计忽略；前端生产构建 3982 个模块通过；文件登记 1823 条、编码扫描 3254 个文本文件、架构验证、rustfmt 与 `git diff --check` 通过。Windows x64 三可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-155542`：主程序 `yishu-desktop.exe` SHA-256 `A7AE8916315D6B209E914A92CD58DBB14D00925181178FC5DFFB465E7B41B7B4`，更新助手 `9D26F668C981299FF4814B95F0ADE2DBF67FCE5A39A301F1CCBE5ABE217EE2EF`，后台快讯采集器 `FAA9487C01CC120386AB37648D8F0DA33D7835A9BC4E0F5D141B1422D0903BD4`。主程序独立启动 8 秒保持存活并正常退出，未残留进程。

`observed`：本次仅生成阶段性 EXE，不生成安装包或 ZIP；参考工程及用户数据目录未触碰，未执行 Git commit/stage/push。远程来源和未完成能力继续保留真实 `partial/stale/missing/unavailable` 边界，阶段性 EXE 不代表整个项目最终完成。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/query-selection-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/QuerySelectionPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/shared/settings/user-settings-types.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/settings.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-155542/yishu-desktop.exe`。

## 2026-09-01 Windows x64 阶段性 EXE（16:16）

`confirmed`：当前源码重新完成前端生产构建（3982 个模块）和 Rust Windows x64 release 构建。三个可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-161612`：主程序 `yishu-desktop.exe` SHA-256 `0B12012C9B7E5D41828E4E803CC250795911E2AD9F66276B881D9C04EF17326B`，更新助手 `yishu-updater.exe` `A877756632AB25B8DD93834839C34FE475B1B5420074ADD2550B5EC38D6745D1`，后台快讯采集器 `yishu-news-collector.exe` `AEE69D3F6BCB9736773827C782A2EA11082CA630DB6A5CAAACB8F392B5766B04`。主程序独立启动 8 秒保持存活并正常结束，未残留进程。

`observed`：本次只生成阶段性 EXE 验收目录，未生成安装包或 ZIP；参考工程及用户数据目录未触碰，未执行 Git commit/stage/push。远程来源和未完成能力继续保持真实 `partial/stale/missing/unavailable` 状态。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-161612/yishu-desktop.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-161612/yishu-updater.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-161612/yishu-news-collector.exe`。

## 2026-09-01 Windows x64 阶段性 EXE 独立复核（16:46）

`confirmed`：验收目录 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-164651` 包含 `yishu-desktop.exe`、`yishu-updater.exe`、`yishu-news-collector.exe` 和 `BUILD-INFO.txt`。主程序 SHA-256 为 `170B28D661ACDBE17212A83A7C874FBE47F0AA03D933C971399A388554637E17`，与构建信息一致；更新助手 SHA-256 为 `86BEADB93928389A00AF0FC85D0666EFF4F91A789DBAA26ABEB6ACFEE153B439`，后台快讯采集器 SHA-256 为 `7833BD9AE50D91A24277C4D328006F834F27450093D473D436A463A9051565C5`。

`confirmed`：主程序独立启动 8 秒保持运行，烟测结束后无残留 `yishu-desktop` 进程；编码扫描 4521 个文本文件、文件登记 1823 条、架构验证、`cargo fmt --all -- --check` 与 `git diff --check` 均通过。未生成安装包或 ZIP，未修改参考工程或用户数据目录，未执行 Git commit/stage/push。

`observed`：该 EXE 为当前源码阶段性 Windows x64 验收产物，不代表尚未完成的远程数据、交易所级逐笔、完整 AI 供应商接入和历史回填能力已全部达到 `ready`；应用继续按真实 `partial/stale/missing/unavailable` 状态展示。

## 2026-09-01 AI 回放汇总与 Windows x64 阶段性 EXE（17:16）

`confirmed`：AI+选股跨日回放面板新增纯派生效果汇总，基于已有冻结候选的真实 1/5/20 日结果统计有效样本、上涨数、下跌数和平均收益；排除 `null`/非有限值，零收益保持中性，不生成预测或交易建议，不新增网络、IPC、数据库、计时器或依赖。

`confirmed`：最新 Windows x64 阶段性验收产物位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-171618`，包含主程序、更新助手和后台快讯采集器。主程序独立启动 8 秒保持运行并正常退出，无残留进程。主程序 SHA-256 `33495602C4C569A262F257C62D857A9A10F1C240D9EE6B877465E808B8C5EA90`，更新助手 `E95E0B38C8465A436808F6330DEB76BCB72CD66B85CC90A392346D7F419B9D62`，后台快讯采集器 `8FD6608EB70F809170CA4B67E9269518EF087C075DC829A9481C3CC329893C8B`。前端 204 文件/797 项、Rust 885 项（1 项按设计忽略）通过；编码、登记、架构、格式和差异检查通过。

`observed`：本次仅生成阶段性 EXE，不生成安装包或 ZIP；参考工程及用户数据目录未触碰，未执行 Git commit/stage/push。远程来源、交易所级逐笔、完整 AI 供应商接入和历史回填仍保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ai-selection-replay-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/AiSelectionReplayPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-171618/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-164651/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-164651/yishu-desktop.exe`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

## 2026-09-01 数据大屏排版与实时资金流优化（本轮）

`confirmed`：修复数据大屏左侧行业板块区域的内容高度溢出和内部滚动条错位，取消强制 `max-content` 高度，量化命中、板块强弱、尾盘候选和涨停预览在有限空间内按比例排布。底部实时新闻补齐深色卡片、中文分类颜色和 hover 辉光，避免按钮回退为浏览器默认灰色。

`confirmed`：行业资金流向改为双轨连续垂直滚动，数据复制形成无缝循环轨道，鼠标悬停暂停，行级 hover 增强辉光；保留主力/大单/超大单/采样次数/时间等真实字段，不再通过整块替换制造机械刷新观感。

`confirmed`：定向测试、前端全量测试、TypeScript 检查和生产构建通过；全量前端测试为 139 个文件/819 项。便携 EXE 冷启动烟测通过：窗口可见 97ms、API 就绪 2780ms、验证完成 9700ms，无残留 `xiaoqibao.exe`。最新 EXE SHA-256 为 `B818D94D7C4B1D1A985BCCD7A08C2BAFEDF5C91F46D5F622D1F8081C7D5E47E6`。

`observed`：本轮未删除数据、缓存、日志或配置；实时接口无有效数据时继续显示真实的等待/不可用状态。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-01 数据大屏中部图表与新闻重新排版（本轮追加）

`confirmed`：中部图表调整为“指数趋势整行、板块涨幅与涨跌分布/北向资金待接入左右并排、实时新闻占用原涨跌分布下方空间”；板块涨幅与涨跌分布各占半宽，新闻改为紧凑的关联标的列表，保留时间、标题和股票代码。

`confirmed`：修复行业板块区域被 `max-content` 撑高导致的滚动条与内容裁切；新闻条目明确设置深色卡片、分类颜色、文字和股票代码颜色，避免浏览器默认灰色按钮。中部新闻与底部快讯均继续支持滚动/悬停暂停。

`confirmed`：前端全量测试 139 个文件/820 项通过，TypeScript 检查、生产构建和便携 EXE 冷启动烟测通过。最新 EXE 窗口可见 107ms、API 就绪 2922ms、验证完成 9917ms，无残留 `xiaoqibao.exe`；SHA-256 为 `9344782CCCE1E183A1C2C71D2AADE6F6F0551D491EA19FF66BFC54ACB6CF1F6F`。

`observed`：未删除数据、缓存、日志或配置；真实接口缺失时仍显示明确不可用状态。

## 2026-09-01 数据大屏量化命中板块（本轮）

`confirmed`：数据大屏左侧行业板块区域新增“量化命中”板块，复用量化分析真实候选接口 `loadQuantStrategy(24)`，展示股票名称/代码、策略模型、评分、命中状态、证据覆盖率和触发确认；候选为零时明确显示“量化策略暂无已验证命中”，不伪造行情。新候选通过差异识别触发全局提示，并以弹出、闪烁、流光扫描和发光边框提醒；鼠标悬停行会放大并增强辉光；离开候选池的旧行保留 900ms 后淡出移除。量化候选轮询与市场辅助请求并行，每 5 秒刷新。

`confirmed`：新增量化候选快照 ref 与高亮计时器清理，避免闭包导致辅助轮询 effect 频繁重启，并在组件卸载时释放所有定时器。量化命中列表使用紧凑可滚动容器，最多首屏展示 8 条真实候选，避免左侧板块溢出。

`confirmed`：前端 TypeScript、生产构建、定向测试和全量测试通过；全量前端测试为 139 个文件/818 项。便携 EXE 重新构建并通过冷启动烟测：窗口可见 198ms、API 就绪 3035ms、验证完成 9618ms，无残留 `xiaoqibao.exe`。最新 EXE SHA-256 为 `D88774B3E9D56F120695B969D2CD1A0019C3D5F0510C3E95FF27371697EDB419`。

`observed`：本轮只修改数据大屏量化命中展示、相关测试和便携构建产物；未删除持久化数据、缓存、日志或配置，量化引擎在无真实候选时继续按 `unavailable/partial` 边界展示。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-01 AI 回放样本覆盖审计增强

`confirmed`：AI+选股跨日回放效果汇总新增每个 1/5/20 日 horizon 的预期候选数、有效样本数、缺失样本数和覆盖率，并在面板显示 `有效/预期样本`。统计只读取已有冻结回放快照的 `candidates[].outcomes`；`null`/非有限收益不计入样本，零收益不计入涨跌，不新增网络、IPC、数据库、计时器或依赖。

`confirmed`：Presenter 类型、面板和双份文件登记完成 TDD；Vitest 4 项、TypeScript、回放 Node 合同、文件登记、编码扫描和 `git diff --check` 通过。参考工程只读，未生成 EXE，未执行 Git commit/stage/push。

`observed`：长期效果归因、第二行情来源、交易所原子快照、完整历史回填和自动捕获全部候选的跨日结果仍未完成，工作区继续保持 `partial`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ai-selection-replay-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ai-selection-replay-types.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/AiSelectionReplayPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/ai-replay-next-report.md`。

## 2026-09-01 重要事件雷达字段增强

`confirmed`：首屏 `ImportantEventRadar` 新增独立 Presenter/类型层，基于共享快讯直接事实投影紧急度、单/多源核验态、直接/市场关联类型、来源数量和完整去重受影响代码集合；方向与置信度因现有来源无原始字段保持 `--`/`null`，不做推断。页面继续复用 `marketAttention` 唯一刷新生命周期，不新增网络、IPC、轮询或依赖。

`confirmed`：Vitest Presenter 3 项、Node 跨层合同、TypeScript、文件登记与编码扫描通过；参考工程只读，未执行 Git 写操作，未生成安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/important-event-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ImportantEventRadar.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/important-event-radar-report.md`。

## 2026-09-01 18:10 重要事件雷达增强与 Windows x64 阶段性 EXE

`confirmed`：重要事件雷达继续复用 `marketAttention` 唯一刷新生命周期，新增来源分组、去重市场信号、摘要和完整受影响股票代码展示，首屏最多 5 条；无原始方向/置信度字段时保持 `null`/`--`，不推断，不增加网络、IPC、轮询或第三方依赖。前端全量 206 文件/803 项通过，Vite 生产构建 3986 modules。

`confirmed`：最新 Windows x64 三可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-181023`。主程序 `yishu-desktop.exe` SHA-256 为 `33587E9AA3E22513109B3EAF3C10AC7C4AC89B7E94245DE5F7D71C5E438179B0`，更新助手 `yishu-updater.exe` 为 `87A2703CD45C7EF9DF20A3AAD146F67B4DB800E7E44C9DB97B9704235A88EB56`，后台快讯采集器 `yishu-news-collector.exe` 为 `42037BF2ED955B2D408D0440E3006E2FD0786296A01254E0BD913040983594C4`。主程序独立启动 8 秒保持运行，烟测结束后无残留进程。

`observed`：本次仅生成阶段性 EXE 验收目录和 `BUILD-INFO.txt`，未生成安装包或 ZIP；参考工程、用户配置、缓存和业务数据目录未触碰，未执行 Git commit/stage/push。远程来源、交易所级逐笔、完整 AI 供应商接入、跨日历史回填和 macOS 实机验证仍保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-181023/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/important-event-presenter.ts`。

## 2026-09-01 18:25 AI+选股跨重启恢复与阶段性 EXE

`confirmed`：第 31 项新增版本化最近冻结索引，最多 30 条、30 天 TTL，按真实 `asOf`/交易日排序；启动时一次性加载最近仍通过完整身份校验的冻结快照，损坏/过期项跳过并回退旧记录。前端以 `origin=restored` 与当前候选 `origin=current` 区分，不自动重算、不调用 AI、不新增网络、轮询或永久业务表。Rust 9 项、前端 5 项、Node 合同 4 项通过。

`confirmed`：全量前端 206 文件/803 项、Rust workspace 885 项通过（1 项按设计忽略）；编码扫描 4536 文件、文件登记 1831 条、架构、TypeScript、rustfmt 和 `git diff --check` 通过。最新 Windows x64 三可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-182538`：主程序 SHA-256 `B918CDE224C4787F6DFF5E393ECB48F5C68EDDEB626E91F58F8BFBE63BCCCDF0`，更新助手 `FAD61D5A8C77C8FE52CB3F0A03D162EFAEA8EF3678E19F218679A10F79DB2C31`，后台快讯采集器 `2F69A1A39667553C2F082206EE2338DE934503C6993A2B56190ACE2BE0BD9261`。主程序独立启动 8 秒保持运行且无残留进程。

`observed`：本次仅生成阶段性 EXE 验收目录和 `BUILD-INFO.txt`，未生成安装包或 ZIP；参考工程、用户配置、缓存和业务数据目录未触碰，未执行 Git commit/stage/push。交易所级逐笔、完整 AI 供应商接入、长期效果归因、完整历史回填和 macOS 实机验证仍保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/ai-selection-restore-report.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-182538/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

## 2026-09-01 18:41 Windows x64 阶段性 EXE

`confirmed`：当前源码完成 Vite 生产构建（3986 modules）和 Rust Windows x64 release 构建。三个可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-184133`：主程序 `yishu-desktop.exe` SHA-256 `D7615D404D4182A59E52BDF82BAE09D6D17C19EE01ECFCFEC6D29D0A3B9C603F`，更新助手 `yishu-updater.exe` `B69D717A49E8E88063BD4F3DC13F6187AC5072B8D5D2F1CC196752474D2EDF53`，后台快讯采集器 `yishu-news-collector.exe` `73924A838C87428CBAE4C0CF1AE89375CBD0163CEBCE4C7B748C5271DAF596C0`。

`confirmed`：主程序从验收目录独立启动后保持运行 8 秒，随后由烟测结束，未残留 `yishu-desktop` 进程。验收目录只包含三个 EXE 和 `BUILD-INFO.txt`，未生成安装包或 ZIP。

`observed`：参考项目、用户配置、缓存和业务数据目录未触碰；未执行 Git commit/stage/push。远程数据、交易所级逐笔、完整 AI 供应商接入、历史回填和 macOS 实机验证仍保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-184133/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`。

## 2026-09-01 19:18 七大人气榜归档与 Windows x64 阶段性 EXE

`confirmed`：第20七大人气榜跨重启当前榜快照归档完成。归档按真实交易日保存与恢复，最多 7 条、7 天 TTL，固定校验七个榜单身份、顺序、交易日和 RFC3339 观测时间；损坏、错日、非七榜 payload 保持 `missing`，IPC/写入异常保持 `unavailable`。恢复来源与当前来源独立标识，不新增网络请求或永久业务表。

`confirmed`：定向 Rust 3 项、前端 2 项、Node 合同、TypeScript、Vite 生产构建（3988 modules）、Rust workspace 888 项通过（1 项按设计忽略），文件登记 1847 条、编码扫描和 `git diff --check` 通过。Windows x64 阶段性便携验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-191759`；主程序 SHA-256 `F3BF185948DD79923B4622050A3AE5B1CB0357F06A70FA09EC6628D9A04E4F2C`，更新助手 `D1DD1690ABD6C74A833C6EB3D578C3764F43C2FA515DA839366AF6F18D0775D2`，后台快讯采集器 `34DDBB6E1CFA405164FFDE78375E7F7653071A21DC500B409ED09ECEA331B2FA`。主程序独立启动 8 秒保持运行并完成烟测清理。

`observed`：本次只生成 EXE 验收目录和 `BUILD-INFO.txt`，未生成安装包或 ZIP；参考项目、用户配置、缓存和业务数据目录未触碰，未执行 Git commit/stage/push。远程数据、交易所级逐笔、完整 AI 供应商接入、历史回填和 macOS 实机验证仍保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-191759/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/.superpowers/sdd/progress.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/seven_popularity_rankings_archive.rs`。

## 2026-09-01 19:31 七大人气榜恢复展示边界修复与最新 EXE

`confirmed`：修复七大人气榜归档恢复的展示边界。实时榜有有效样本时始终优先；仅当实时榜无有效样本时，合法恢复快照才投影到页面。自动保存和按交易日恢复均只读取 `liveView`，恢复快照不会再次被写入当前归档，也不会污染当前来源标识。新增 Node 跨层合同回归测试，受影响 Presenter/Store 共 12 项通过。

`confirmed`：修复后前端生产构建 3989 modules，Windows x64 release 构建成功。最新阶段性验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-193142`；主程序 SHA-256 `749060C8151CA54822FC174CC4C0836A1D546C2DDB789236024981742A18FC40`，更新助手 `4C50681DDAF5AE273C098B095CC1FBFC3138EE5717D4097A09861DA7C0D8F969`，后台快讯采集器 `0E3325CAC37CB527ACAE2A5ED19D901A07CE18794CA54744C93C01C6B3BC190C`。主程序独立启动 8 秒保持运行，清理后无残留进程。

`observed`：本次仅生成便携 EXE 验收目录，未生成安装包或 ZIP；参考项目、用户数据和 Git 均未触碰。远程数据、交易所逐笔、完整 AI 供应商、历史回填和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-193142/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/SevenPopularityRankingsPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/seven-popularity-rankings-archive-contract.test.mjs`。

## 2026-09-01 18:39 Windows x64 阶段性 EXE（三件套）

`confirmed`：当前源码完成前端生产构建（Vite 3986 modules）和 Rust Windows x64 release 构建，三件可执行文件复制到 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-183956`。主程序 `yishu-desktop.exe` SHA-256 `B918CDE224C4787F6DFF5E393ECB48F5C68EDDEB626E91F58F8BFBE63BCCCDF0`；更新助手 `yishu-updater.exe` SHA-256 `9176AB1B7CC4452BF899ED8C79BCB522473200CC74D212CB07D1D73498991257`；后台快讯采集器 `yishu-news-collector.exe` SHA-256 `22C90F119FB22DCDCAA31B88F52220D5441EF966E9ED446DFEFA7C723DA06157`。

`confirmed`：主程序独立启动 8 秒保持运行，烟测后无残留 `yishu-desktop` 进程；编码扫描 4536 个文本文件、文件登记 1831 条、`git diff --check` 均通过。只生成 EXE 验收目录，未生成安装包或 ZIP；参考项目及用户配置、缓存、业务数据目录未触碰，未执行 Git commit/stage/push。

`observed`：release 编译仍有既有 unused/deprecated 警告，不影响本次 exit 0 构建；远程来源、交易所级逐笔、完整 AI 供应商接入、跨日历史回填和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-183956/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/Cargo.toml`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows.ps1`。

## 2026-09-01 数据大屏重复新闻与板块强弱布局修复

`confirmed`：数据大屏底部重复新闻区域已移除，中部“实时新闻 · 关联标的”继续作为唯一新闻展示区；底部保留数据源、观测时间、覆盖率和实时通道状态，并压缩为 30px 状态栏，避免重复内容和无意义留白。

`confirmed`：左侧“板块强弱”区域增加最终布局约束，父容器使用 `min-height: 0` 与 `overflow: hidden`，四个子区按可用高度分配，板块标签和量化命中列表改为内部纵向滚动，限制横向溢出，避免 `max-content` 撑高造成裁切和滚动条错位。

`confirmed`：新增底部新闻移除与板块高度约束回归测试；前端全量测试 139 个文件/821 项通过，TypeScript、Vite 生产构建、`git diff --check` 和数据大屏乱码扫描通过。便携 EXE 已重建，冷启动烟测通过：窗口可见 368ms、API 就绪 6148ms、14/14 菜单性能通过、验证完成 21536ms，无残留 `xiaoqibao.exe`。最新 EXE SHA-256 为 `37C74A16AF8748672B8383E305021B29FB37D473597541B30F5483429F1DEC8B`，路径为 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

`observed`：本轮未删除持久化数据、缓存、日志或配置；真实新闻和行情接口仍按实际覆盖状态展示。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。
## 2026-09-01 七大人气榜恢复快照可见性

`confirmed`：当实时七榜没有有效样本且归档 Store 返回 `origin=restored` 时，前端新增纯投影将恢复快照用于榜单、重复矩阵、审计和摘要展示；实时样本一旦存在则保持实时优先。恢复视图追加明确的跨重启限制说明，不改变来源状态，不新增网络、IPC、数据库或定时器。

`confirmed`：新增 `apps/desktop/src/feature/market-overview/seven-popularity-rankings-archive-projection.ts` 及测试，接线 `SevenPopularityRankingsPanel.svelte`；Vitest 4 项、Node 合同 2 项、TypeScript、Vite 3989 modules、文件登记 1849 条、编码扫描 4548 个文本文件和 `git diff --check` 通过。

`observed`：恢复快照仍只代表本机最近一次真实观测，不代表实时官方人气榜；参考工程只读，未执行 Git 写操作，未生成安装包或 ZIP。
## 2026-09-01 七大人气榜恢复快照可见性

`confirmed`：实时七榜无有效样本且归档 Store 返回 `origin=restored` 时，前端纯投影将恢复快照用于榜单、矩阵、审计和摘要展示；实时样本形成后保持实时优先。恢复状态与限制说明保留，不新增网络、IPC、数据库或定时器。

`confirmed`：新增归档投影模块及测试，接线七大人气榜面板；Vitest 4 项、Node 合同 2 项、TypeScript、Vite 3989 modules、文件登记 1849 条、编码扫描 4548 个文本文件和差异检查通过。Windows x64 三件 EXE 复用本次 release 产物，独立启动 8 秒无残留进程。

`observed`：恢复快照仍只代表本机最近真实观测，不代表实时官方人气榜；参考工程只读，未执行 Git 写操作，未生成安装包或 ZIP。

## 2026-09-01 19:49 七大人气榜归档覆盖率语义修复与 Windows x64 阶段性 EXE

`confirmed`：七大人气榜归档记录新增可选 `coverage` 字段，保存时只接受有限且位于 0 到 1 的真实覆盖率；恢复时透传归档覆盖率，旧版无该字段的 JSON 记录保守恢复为 0.0，避免把不完整归档升级为满覆盖或 `ready`。归档交易日、七榜身份、TTL、数量上限和恢复展示边界保持不变。

`confirmed`：Rust workspace 测试 890 项通过、1 项按设计忽略；前端 208 个测试文件/807 项通过；前端生产构建 3989 modules；架构登记、编码扫描、`cargo fmt --check` 和 `git diff --check` 通过。Windows x64 三件便携验收产物位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-194911`：主程序 SHA-256 `709AECC8D30496CB22599705A595F1FEB61595E2680A23DC2F36B12F8A224A7A`，更新助手 `B6A6CC1193CF43338FA0F32AA8378C9CCBC84ABCB1266469243FDA2BB35EEBA2`，后台快讯采集器 `ACBDC664233B16C7D7C341650C0AFFD5B84F6F1C464E004BA5C2C86172CD365E`。主程序独立启动 8 秒保持运行并由烟测清理，无残留进程。

`observed`：本轮只生成阶段性便携 EXE 验收目录和 `BUILD-INFO.txt`，未生成安装包或 ZIP；参考项目、用户配置、缓存和业务数据目录未触碰，未执行 Git commit/stage/push。远程来源、交易所级逐笔、完整 AI 供应商接入、历史回填和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/seven_popularity_rankings_archive.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/seven_popularity_rankings_archive.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/seven-popularity-rankings-archive-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-194911/BUILD-INFO.txt`。
## 2026-09-01 Windows x64 阶段性 EXE 验收（20:15）

`confirmed`：当前源码重新完成前端生产构建与 Rust Windows x64 release 构建，三个独立可执行文件已输出到 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-201523`。主程序独立目录启动 2 秒可创建窗口并正常清理；前端 3989 modules；启动采样 86.75-114.47ms，空闲 CPU 0.049%，工作集峰值约 33.9MiB。

`confirmed`：产物 SHA-256：主程序 `D4CA4082630C1980F4B087C0B4A62158FAE99836C8A6DA02823EB134C26D33C2`，更新助手 `C80A5E4E319F3070537BD1158D11592DC17F6CFBAA46D3A83F6A8A4EA010CD86`，后台快讯采集器 `231D7C61D09C6F6E759BBC66AB4AAE8F3AFC501572E35AB3EDC90146252F897F`。编码扫描与 `git diff --check` 通过，未生成安装包或 ZIP，参考工程保持只读，未执行 Git 写操作。

`observed`：更新助手烟测脚本整体退出码为 0，但其测试启动命令输出了启动失败诊断；因此更新流程不宣称为完全 ready，后续需专项复核测试启动参数与健康检查边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-201523/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/verification/windows-performance-latest.json`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/run-windows-smoke.ps1`。

## 2026-09-01 20:47 数据大屏增强与 Windows x64 阶段性 EXE

`confirmed`：数据大屏新增板块强弱、行业资金流、主力大单、首次涨停候选、尾盘候选及数据源审计栏，所有列表限制为最多 10 条并复用既有 Store；量化命中无真实来源时保持 `missing`。盘中统一时间线修复为可信来源交易时间优先于本机检测时间，其他来源仍按实际观测时间排序。

`confirmed`：根级前端合同与 Vitest 209 文件/810 项通过；Rust workspace 890 项通过、1 项按设计忽略；Vite 生产构建 3998 modules；编码扫描、文件登记、架构验证、rustfmt 和 `git diff --check` 通过。最新 Windows x64 三可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-204719`：主程序 `yishu-desktop.exe` SHA-256 `EB61D8AD2FDBBCA989A12515542618DDCFE4148B6EDD11AB9364B13A3F7A8857`，更新助手 `yishu-updater.exe` 为 `EB7A9356603883FD07E08DAA84675D76DDB5E6A7076C83D42D792FFF98918CC0`，后台快讯采集器 `yishu-news-collector.exe` 为 `49C3A46580E3F268C9C9CC0F656F3FF723EA3A703D1C27452F7BBF9F8C433EE9`。主程序独立启动 8 秒并清理，无残留进程。

`observed`：本轮仅生成阶段性 EXE 验收目录；未生成 ZIP 交付包，NSIS 安装包仅作为构建副产物留在 `target/release/bundle/nsis`，未对用户数据、配置、缓存或参考项目做任何修改，未执行 Git commit/stage/push。远程完整覆盖、交易所级逐笔、完整 AI 供应商接入、跨日历史回填和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/data-screen-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/intraday-event-timeline.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-204719/BUILD-INFO.txt`。

## 2026-09-01 21:09 EXE-only 构建流程隔离

`confirmed`：新增 `scripts/build-windows-exe.ps1`，用 `tauri build --no-bundle` 构建 Windows x64 主程序，并先构建更新助手与后台快讯采集器；新增 `tests/release/windows-exe-only-contract.test.mjs` 和双文件登记，锁定阶段验收不调用 NSIS、不生成 ZIP。

`confirmed`：最新三件 EXE 位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-210922`。主程序 `yishu-desktop.exe` SHA-256 `DEEF0F2F5FF9F7A318B1EA0F8CC9500ED45BB860CE9259AACF65DC3096E466BB`，更新助手 `yishu-updater.exe` 为 `5D4D493FE3FF891D775862E00A811988E68F78B3F88FF5205B14F73A3CF02538`，后台快讯采集器 `yishu-news-collector.exe` 为 `113BCA8DFC2F82001C30CEC52649505167E3396994E33954D10D7C807B6434A4`；构建后 `target/release/bundle/nsis` 无 EXE 安装器。

`observed`：参考项目、用户配置、缓存和业务数据目录未触碰，未执行 Git commit/stage/push；产品总体仍保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-210922/BUILD-INFO.txt`。

## 2026-09-01 21:24 Windows x64 阶段性 EXE 验收

`confirmed`：基于当前源码重新完成前端生产构建（Vite 3998 modules）与 Rust Windows x64 release 构建，三件 EXE 已复制到独立验收目录 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-212448`。主程序 `yishu-desktop.exe` SHA-256 `02A5D5247DC830E010414BBA9FB48A65328AB736056979E13011CA3186C5A589`，更新助手 `yishu-updater.exe` `12B9A01FCC8E374B11B3F999511B06C501BDBDD61A46D62113B6B7605CAD004F`，后台快讯采集器 `yishu-news-collector.exe` `073BD1C181B738FEFE5352DEE3ACFF9FE27CDF8C23186DC1D2E43EDFE1771FB7`。

`confirmed`：主程序从验收目录独立启动后 2 秒仍存活，烟测清理后无残留 `yishu-desktop` 进程；`windows-exe-only-contract` 通过，编码扫描 4562 个文本文件通过，`git diff --check` 通过。本轮仅生成 EXE 和 `BUILD-INFO.txt`，未生成安装包或 ZIP。

`observed`：构建输出仍有既有 unused/deprecated Rust 警告，不影响 release 构建退出码 0；更新助手的真实远程更新服务配置、远程数据完整覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。参考项目、用户配置、缓存和业务数据目录未触碰，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-212448/BUILD-INFO.txt`。

## 2026-09-01 21:31 Windows x64 阶段性 EXE 验收

`confirmed`：基于当前源码重新完成 Windows x64 EXE-only 构建，前端 Vite 生产构建处理 3998 个模块，Rust release 构建退出码为 0。三件 EXE 已复制到独立验收目录 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-213121`：主程序 `yishu-desktop.exe` SHA-256 `ECC766A1E8900F2364EC0F77908C046E910CCB023586A297486247FF67B653B4`，更新助手 `38204B074453F8B9F1D7AA6844C6348008941CBBE59843B08A82A36D191810E0`，后台快讯采集器 `BDEA7C98C4B7268B5ECBF763B505ED5EAB7CC15391C36356C314DDA0CD4B4EB8`。

`confirmed`：主程序从验收目录独立启动 2 秒后保持运行，清理后无残留进程；`windows-exe-only-contract` 通过；验收目录仅含三个 EXE 和 `BUILD-INFO.txt`，无 ZIP 或安装包。元数据文件换行已修正为正常 UTF-8 文本。

`observed`：构建仍有既有 Rust unused/deprecated 警告；更新服务真实远程配置、远程数据完整覆盖、交易所级逐笔、完整 AI 供应商和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。参考项目、用户配置、缓存和业务数据目录未触碰，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-213121/BUILD-INFO.txt`。

## 2026-09-01 重要事件雷达字段真实性边界修复

`confirmed`：首屏重要事件雷达继续只消费共享 `marketAttention.breakingNews`。Presenter 现在按来源文本实际分组计数；当证据标记为多源但来源文本不完整时仅保留至少两路的真实下限，不凭空扩展来源。受影响股票集合仅保留原文明示且符合六位 A 股代码规则的代码并去重；没有合法代码的快讯不会被提升为关联事件。雷达头部持续显示快讯信封的 `ready/partial/stale/missing/unavailable` 状态，方向与置信度无原始字段时仍为 `null/--`。

`observed`：新增回归测试覆盖三来源计数、非法代码过滤和无合法代码不入雷达；定向 Vitest 7 项、Node 合同和 Vite 3998 modules 构建通过。未新增网络、IPC、轮询、数据库或第三方依赖，未修改参考项目和用户数据。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/important-event-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ImportantEventRadar.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/important-event-presenter.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/important-event-radar-contract.test.mjs`。

## 2026-09-02 13:47 信息总览全息动效、无内滚动与 EXE 验收

`confirmed`：信息总览 50 个工作区改为 8 个家族标签与当前家族贴纸导航；长列表、排名、日历、资金、板块、筛选和详情工作区统一改用共享分页或互斥标签，业务组件内部纵向 `overflow auto/scroll` 与 `max-height` 扫描为 0，必要宽表只保留横向滚动。状态来源与运行细节默认折叠，真实 `ready/partial/stale/missing/unavailable` 状态保持不变。

`confirmed`：桌面壳加入粒子、科技网格、全屏扫描线、四角装饰、玻璃拟态、旋转霓虹描边、呼吸辉光、数字与列表刷新反馈及 SVG 图表流光；上涨使用亮红、下跌使用亮青，并为 `prefers-reduced-motion` 提供停用兜底。开发模拟轨道仅在 `import.meta.env.DEV` 与 URL `previewSimulation=1` 双闸门后动态加载，显式标注“模拟预览 / 非真实行情”，不接正式 Store、IPC、缓存、数据库、归档或 AI 证据；生产构建相关标识扫描为 0。

`confirmed`：前端全量 213 个测试文件、839 项通过；Rust workspace 890 项通过、1 项按设计忽略，更新核心另有 13 项、采集器 1 项通过；Vite 生产构建处理 4012 个模块。文件登记 1873 条、编码扫描 4603 个文本文件、架构检查、rustfmt 与 `git diff --check` 通过。浏览器在 1280×720、1440×900、800×900 下无页面横向溢出、无业务卡片内部纵向滚动、无窄窗口文本裁切。

`confirmed`：最新 Windows x64 桌面 EXE 位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-134712/yishu-desktop.exe`，33,129,984 bytes，PE machine `0x8664`，SHA-256 `B7F644F5C27D3953E3AF6DB976FAD33F53CCD974CB5728B316D88014D3695B0D`。独立目录启动 2500ms 后进程和主窗口有效，清理后同路径残留进程为 0；本轮未生成安装包或 ZIP，未修改参考工程，未执行 Git commit/stage/push。

`observed`：Rust release 仍有既有 unused/deprecated 警告，但构建退出码为 0。完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证继续保留真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-02-overview-holographic-motion-and-scrollbar-removal.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/HolographicBackdrop.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/shared/motion/market-motion.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/shared/pagination/CompactPager.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/dev-preview/preview-market-simulator.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-134712/yishu-desktop.exe`。

## 2026-09-02 数据大屏实时新闻 2 列 5 行

`confirmed`：数据大屏“实时新闻 · 关联标的”宽屏展示调整为 2 列 5 行，共渲染 10 条新闻；窄屏保留 10 条内容并启用纵向滚动，避免新闻被截断。新闻条目继续保留时间、标题、关联标的及核验/跟踪/影响标签。

`confirmed`：新增回归覆盖 10 条新闻渲染和 2 列 5 行 CSS 布局；前端全量测试 139 个文件、825 项通过，TypeScript/Vite 生产构建通过。便携版 EXE 已重建并通过冷启动冒烟测试：窗口可见约 367ms，API 就绪约 7.3s，14 个菜单性能检查通过。最新主程序位于工作树 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `C5CAEAED52FE63007EF3E691292C72785E06025D6678DEC1A5E9BBFF39EF0D9B`。

`observed`：构建日志仍有既有大 chunk 提示及真实数据覆盖不足告警；未修改业务接口、数据目录或用户持久化目录，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenCharts.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/scripts/run-portable-smoke.ps1`。

## 2026-09-02 数据大屏候选滚动与量化命中视觉优化

`confirmed`：数据大屏左侧“量化命中”改为亮紫色（`#c084fc`）边框、侧标和新命中发光提示；行业板块、量化命中及候选区重新分配高度，避免内容拥挤。尾盘候选与今日涨停改为左右双栏，每栏最多同时显示 5 行，超过 5 条时以复制轨道实现连续向上循环滚动，悬停或聚焦会暂停滚动。

`confirmed`：新增 `ContinuousRail` 组件及回归测试，锁定连续滚动轨道、双栏候选布局、五行视口和亮紫色量化命中样式。定向测试 15 项通过，TypeScript/Vite 生产构建通过；最新便携版 EXE 已重建并通过冷启动冒烟测试，窗口约 363ms 可见、API 约 7.4s 就绪、14 个菜单性能检查通过。主程序 SHA-256 `CF951B56A357B249BB5043018D68AC54634056E20302E879AC03F0A1EE7CA721`。

`observed`：构建仍有既有大 chunk 和真实数据覆盖不足告警；未修改数据接口、业务逻辑或用户持久化目录，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/scripts/run-portable-smoke.ps1`。

## 2026-09-01 22:37 Windows x64 EXE-only 阶段性验收

`confirmed`：基于当前源码执行 `scripts/build-windows-exe.ps1` 成功，前端生产构建 3999 modules，Rust release 构建退出码 0。最新验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-223721`，包含主程序、更新助手和后台快讯采集器三个 EXE 及 `BUILD-INFO.txt`。主程序 SHA-256 `2E4FD4E23D59FBB937976278D533FBF3115542F1402E97F318A0E3795C282608`；更新助手 `9F0D8C64CAEFA401FE5EB1DF3976A5ECC839C71A2D8C8EFC2641D05FC8C1B357`；后台快讯采集器 `EC6D0A334F6AB4802FFE64D3F8A24037F9CBC2E59125A5F82FF7FA72BEB7A4A5`。

`confirmed`：主程序从独立验收目录启动 2000ms 后保持运行，随后清理成功且无残留进程；本轮未生成安装包或 ZIP，未修改参考项目、用户数据、缓存或业务数据库，未执行 Git commit/stage/push。

`observed`：Rust 构建仍有既有 unused/deprecated warnings；远程更新服务完整配置、完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-223721/BUILD-INFO.txt`。

## 2026-09-01 23:16 数据大屏资讯/热点增量后的 Windows x64 EXE

`confirmed`：数据大屏实时资讯与热点双栏增量通过全量前端测试（210 个文件、822 项）和 Vite 4001 modules 构建后，重新生成 Windows x64 EXE-only 验收目录 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-231609`。主程序 SHA-256 `BF0143A37157F167F41C5B3D278EFDE8B019419968F33CB81A00CF58107BC7C2`；更新助手 `AEA10A7F83538EC5442C65E02BB9E4DA702FC87C1CC4EFA6452EF77155FD6AD1`；后台快讯采集器 `9CA59C9ED9B70E8D84FD4518CCB5EF2C5D8BFADC50A74E005A3DB26BA7196C77`。

`confirmed`：主程序 PE machine 为 `0x8664`，从独立目录启动 2000ms 后保持运行，清理成功且无残留进程；目录仅含三个 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP，未修改参考项目或用户数据，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-231609/BUILD-INFO.txt`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`。

## 2026-09-01 22:27 事件雷达共享异动回退与异动题材排行

`confirmed`：重要事件雷达现在资讯优先；资讯没有可展示事件时回退共享 `marketMovements.movements.data.eventStream.events`。回退事件按 `eventId` 去重，时间优先使用真实 `exchangeTimestamp`，缺失时使用 `detectedAt`，并标记时间来源；`confidence` 始终保持空值，不从涨跌幅、标题或市场信号推断。该接线复用已有 `marketAttention` 与 `marketMovements` 单例，不新增网络、IPC、轮询、数据库或依赖。

`confirmed`：第 30“异动统计大全”新增独立“异动题材排行”区块，复用异动事件、快讯明示代码和热点原始 `themes`，仅在同一上海交易日、同一六位股票代码严格匹配时计数；重复 `eventId` 去重，多题材拆分，最多展示 24 条，来源失败和无匹配保持真实 `missing/stale/unavailable`。

`confirmed`：事件雷达定向 Presenter 10 项、异动题材排行 Presenter 4 项、前端全量 210 个测试文件/820 项、Rust workspace 890 项通过；Vite 生产构建处理 3999 modules；EXE-only 构建退出码 0。最新 Windows x64 三件 EXE 位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-222723`：主程序 SHA-256 `49AA02E0250E00967C1BC6750DBC088DF28D10798859F574F0D07E65419B2E53`，更新助手 `A65E58A72AF8665C3BA95D088AFCF30C3EFA9ECA1139BA087E86331317264CFB`，后台快讯采集器 `CC3EA1DC5B8A7FD1485CF44F4AF3F18D08DC2361191197141D9077EDEA132B8C`。主程序独立启动 2 秒并清理无残留，验收目录仅含三个 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP。

`observed`：远程完整覆盖、交易所级逐笔、完整 AI 供应商、历史回填和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界；参考项目、用户配置、缓存、业务数据目录未触碰，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/important-event-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ImportantEventRadar.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/movement-statistics-theme-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/MovementStatisticsPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-222723/BUILD-INFO.txt`。

## 2026-09-01 21:57 Windows x64 EXE-only 阶段性验收

`confirmed`：基于当前源码重新完成 Windows x64 EXE-only 构建，三件可执行文件位于 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-215716`。主程序 `yishu-desktop.exe` SHA-256 `10BD84B865DE85268D7F3EA2F6365DC357DEA7DA446B5A5DF6B9C890E9704054`；更新助手 `yishu-updater.exe` SHA-256 `2B6F739550771523E04BA4A8D3379E7AB582216AD3692213B8A30E23CDCD9E22`；后台快讯采集器 `yishu-news-collector.exe` SHA-256 `D88A717F34255F454160D1F9AE249AD59135FF44719DA3A1F6F181A41BCE9835`。

`confirmed`：EXE-only 合同通过，重要事件 Presenter 定向 7 项测试通过；主程序从独立验收目录按完整路径启动 2 秒保持运行，清理后无残留同路径进程；验收目录仅含三个 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP。

`observed`：构建仍有既有 Rust unused/deprecated 警告，不影响 release 构建退出码 0；更新服务真实远程配置、远程数据完整覆盖、交易所级逐笔、完整 AI 供应商接入、历史回填和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。参考项目、用户配置、缓存、业务数据目录未触碰，未执行 Git commit/stage/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/important-event-presenter.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-20260901-215716/BUILD-INFO.txt`。

## 2026-09-01 重要事件雷达共享异动回退

`confirmed`：重要事件雷达新增纯组合 Presenter，优先展示已有全球快讯；仅当快讯没有可展示事件时，才回退共享 `marketMovements.movements.data.eventStream.events`。异动回退保留原始事件种类、方向、合法六位代码、来源和时间来源类型（优先交易所时间，缺失时使用本地检测时间），重复事件按事件 ID 去重并最多展示 5 条；置信度继续保持 `null/--`，不从涨跌幅或标题推断。组件只订阅已有 `marketAttention` 和 `marketMovements` 单例，不增加网络、IPC、轮询、数据库或依赖。

`observed`：新增资讯优先、异动回退、时间来源、去重和有界展示回归测试；定向 Vitest 10 项、Node 合同、TypeScript/Vite 3998 modules 构建通过。参考工程和用户数据未修改，未执行 Git 写操作。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/important-event-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ImportantEventRadar.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/important-event-presenter.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/important-event-radar-contract.test.mjs`。

## 2026-09-02 14:34 信息总览终审修复与 Windows x64 EXE

`obsolete`：13:47 验收目录 `dist/yishu-a-share-observation-preview-20260902-134712` 不包含后续分页上下文、卡片资源和图表路径插值修复，不再作为本阶段最新验收产物；文件保留供历史追溯。

`confirmed`：搜索、筛选、查询、清空和题材切换会重置对应分页；详情与目录分页在实时重排后仍同步当前选中项。普通卡片不再常驻高成本双动画和 10px 模糊，霓虹描边与呼吸辉光改由伪元素承载，普通子卡只在 hover/focus 时触发。`missing` 与 `unavailable` 文案已分离，行情数字使用精确标记，不误把股票代码或时间作为涨跌数值。

`confirmed`：四个 SVG 图表统一接入共享 RAF 路径插值，支持不同点数弧长重采样、180–320ms 有界动画、快速更新和销毁取消旧 RAF；隐藏页面、减少动效和空数据直接提交终值。正式页面仍只消费真实数据五态；开发模拟器继续受 `DEV + previewSimulation=1` 双闸门隔离。

`confirmed`：前端全量 214 个测试文件、847 项通过；Rust 桌面库 890 项通过、1 项按设计忽略，更新核心 13 项和采集器 1 项通过；Vite 生产构建处理 4013 个模块，Windows EXE-only 构建与合同通过。最新主程序为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-143430/yishu-desktop.exe`，33,129,984 bytes，PE machine `0x8664`，SHA-256 `3E33906764D197B91C43AD57460E207055F1B1919C109911D2A8A46B06B46C5D`。独立路径启动 2500ms 后进程存活且主窗口句柄有效，清理后同路径残留进程为 0。

`observed`：本轮只复制桌面主 EXE，未生成安装包或 ZIP；未修改参考工程、用户配置、缓存或业务数据，未执行 Git commit/stage/push。Rust release 仍有既有 unused/deprecated 警告，但构建退出码为 0；完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/docs/superpowers/plans/2026-09-02-overview-holographic-motion-and-scrollbar-removal.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/shared/chart/chart-path-motion.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/shared/chart/chart-path-motion.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-143430/yishu-desktop.exe`。
## 2026-09-02 数据大屏、启动刷新、更新失败与涨停复盘归因阶段

`confirmed`：数据大屏总体状态现覆盖页面实际展示的全部来源并保留五态；候选机会与主力大单支持合法六位股票钻取，板块、候选和审计区域不再截获纵向滚轮，长审计默认折叠。数据大屏路由去除了应用壳重复页头和重复全局行情带，DOM 实测业务区无内部纵向滚动，可见操作标签使用 12px 可读下限。

`confirmed`：应用启动只读取一次设置并在全局市场脉冲挂载前应用用户刷新频率，同一份设置用于交易日历首次配置；读取失败使用安全默认并放行。更新前端现在保留后端激活结果，`started:false` 显示真实错误并解除忙碌，`started:true` 才等待更新助手接管。

`confirmed`：第 28“涨停复盘啦”改为复用唯一板块生态 Store；板块行情只在来源上海交易日与严格涨停交易日一致时参与归因，行业名称仅做 trim 后完全匹配，重复与非法股票剔除并记录，错日或板块不可用时保留行业原值分组而不拼接旧行情。

`confirmed`：前端全量 216 个测试文件、862 项测试通过，Vite 生产构建处理 4017 个模块；架构登记 1883 条、UTF-8 扫描 4621 个文本文件、浏览器视觉/DOM 验收和 `git diff --check` 通过。参考工程未修改，未执行 Git stage/commit/push，未生成 EXE、安装包或 ZIP。

`observed`：普通网页预览没有 Tauri IPC，因而远程行情显示真实 `unavailable/missing`；交易所逐笔、完整板块成员、多源原子快照、完整 AI 提供商、macOS 实机与部分历史回填仍是明确缺口，项目总体继续保持 `active/partial`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/settings-bootstrap.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/update-client.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/limit-up-review-sector-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/verification/feature-completion-audit.md`。

## 2026-09-02 信息总览控件与长列表收口

`confirmed`：信息总览剩余 12 个原生下拉控件全部改用共享 `SegmentedChoice`，日期归档页同时保留标签快捷筛选与 `type=date` 精确输入；7 个长列表及对应 presenter 统一使用共享 `paginate` 与 `CompactPager`，默认每页 10 行。

`confirmed`：前端全量 218 个测试文件、868 项通过；信息总览运行时/分页合同通过；Vite 生产构建 4017 模块通过；架构登记 1890 条、UTF-8 编码扫描 4633 个文本文件和 `git diff --check` 通过。浏览器 1280×720 实测页面宽度无溢出，原生 `select` 数量为 0。

`observed`：构建仅剩少量历史无效 CSS 选择器提示，不影响产物；正式页面继续保持真实 `ready/partial/stale/missing/unavailable` 状态边界。未修改参考工程、未执行 Git stage/commit/push、未生成 EXE/安装包/ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-workspace-runtime-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-long-list-pagination-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/shared/controls/SegmentedChoice.svelte`。

## 2026-09-02 16:51 Windows x64 EXE 阶段验收

`confirmed`：按用户明确要求，基于当前源码执行 `scripts/build-windows-exe.ps1` 的 EXE-only release 构建，前端 Vite 生产构建与 Rust/Tauri release 构建均退出码为 0。三件可执行文件复制到 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-165107`：主程序 `yishu-desktop.exe` 33,138,176 bytes，更新助手 `yishu-updater.exe` 675,840 bytes，后台快讯采集器 `yishu-news-collector.exe` 7,127,552 bytes；主程序 PE machine 为 `0x8664`。SHA-256 分别为 `762B636A9F61E957CE3EA06371F65A6D3AA6548A0DDA4079A3207AECD0CC9878`、`9B7D62F3E0E8782FF58C4687D9437FDDED3878453073EDEFFE364F420848DE0A`、`46839B671C035995249B38971C26E3EE531ADCF252559B83AF974C7AD7155706`。

`confirmed`：主程序从独立验收目录启动 3 秒后进程存活且主窗口句柄有效，随后清理；同路径残留进程为 0。Windows EXE-only 合同通过，UTF-8 编码扫描 4633 个文本文件通过，`git diff --check` 通过。验收目录只包含三个 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP；未修改参考项目、用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：release 编译保留既有 unused/deprecated/linker warnings，不影响本次构建退出码；完整远程数据覆盖、完整 AI 供应商接入、交易所级逐笔、macOS 实机验证仍保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-165107/BUILD-INFO.txt`。
## 2026-09-02 17:42 有界日志存储与最新 Windows x64 验收

`confirmed`：通知与监控审计 JSONL 已接入有界追加/尾部读取实现，默认最大 2 MiB、最多 500 条，尾部坏行容错并通过临时文件替换降低中断半写风险；新增生产文件已登记到 `docs/architecture/file-registry.yaml`。

`confirmed`：前端全量 218 个测试文件/868 项通过；Rust workspace 896 项通过、1 项按设计忽略；Vite 生产构建通过；文件登记 1894 条、UTF-8 编码扫描 4637 个文本文件、`git diff --check` 通过。最新 Windows x64 EXE-only 验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-174235`，主程序 SHA-256 `CF3052A4C466C14EF5CED960DDE0AAD4144C918FDAE49D927899E3A8F7DE375C`，更新助手 `F7055AF6A442AF122B2E5B7A6DCF205ED9A630EE209A8893C2AB91A6E980B09A`，后台采集器 `7BA07BAA70DF3DC934E9A19C976F8B4B5783156CECDEB3C104EBAF899CA6ACFB`；主程序 PE machine `0x8664`，独立启动 3 秒窗口有效，清理后无残留进程。

`observed`：release 构建仍有既有 unused/deprecated/linker warnings；完整远程数据覆盖、完整 AI 供应商接入、交易所级逐笔和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。未修改参考工程、用户数据、缓存或业务数据库，未执行 Git stage/commit/push，未生成安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/storage/bounded_jsonl.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/file-registry.yaml`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-174235/BUILD-INFO.txt`。

## 2026-09-02 17:55 最新 Windows x64 EXE 阶段验收

`confirmed`：基于后台采集跨进程租约改造后的最新源码重新执行 `scripts/build-windows-exe.ps1`，Rust/Tauri release 与 Vite 生产构建均退出码为 0。最新验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-175534`，包含 `yishu-desktop.exe`（33,272,832 bytes，SHA-256 `317AA1B5163B7EB733F7E322AF1E89A598D01592A8E5BB27B451C83D2CCABABC`）、`yishu-updater.exe`（675,840 bytes）和 `yishu-news-collector.exe`（7,136,256 bytes），仅保留 EXE 与 `BUILD-INFO.txt`，未生成安装包或 ZIP。

`confirmed`：主程序 PE machine 为 `0x8664`；从独立验收目录启动 3000ms 后进程仍存活且 `MainWindowHandle` 有效，随后已终止并确认无残留同名进程。Windows EXE-only 合同、文件登记（1894 条）、UTF-8 编码扫描（4637 个文本文件）和 `git diff --check` 通过。参考项目、用户配置、缓存、业务数据未修改，未执行 Git stage/commit/push。

`observed`：构建保留既有 Rust unused/deprecated/linker warnings；`run-windows-smoke.ps1` 的更新助手子步骤因脚本要求 `target/debug/yishu-updater.exe` 而未执行成功，不影响本次 release EXE 产物和主程序启动验收；更新助手完整 debug smoke、远程数据覆盖、完整 AI 供应商、交易所级逐笔和 macOS 实机验证仍待后续环境验证。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/build-windows-exe.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/release/windows-exe-only-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-175534/BUILD-INFO.txt`。

`obsolete`：上段关于更新助手 smoke 因 debug 路径缺失而失败的描述已由 2026-09-02 更新烟测修复记录替代；当前脚本会优先使用 release helper，`run-windows-smoke.ps1` 与成功/回滚 smoke 均已通过。

## 2026-09-02 公司研究 AI 行为测试与更新烟测修复

`confirmed`：公司研究 AI 用例新增本地回环 HTTP 行为测试，验证合法配置只发出一次请求、请求体只包含冻结证据白名单字段、API key 不进入请求体或返回包；非 HTTPS 外部端点、HTTP 500、超时、非法 JSON 和超过 1 MiB 响应均保持 `unavailable` 并保留限制信息。Rust 定向测试 4 项、公司研究 live contract、格式检查、文件登记 1895 条、UTF-8 扫描 4637 个文本文件和 `git diff --check` 均通过。

`confirmed`：更新助手 smoke 脚本现在优先解析 `target/release/yishu-updater.exe`，release 不存在时回退 `target/debug`；成功激活路径保持用户配置并记录 `committed`，健康超时路径恢复旧版本并记录 `rolled_back`。`run-windows-smoke.ps1`、更新 smoke、文件登记、编码扫描和差异检查均通过。

`observed`：公司研究 AI 仍依赖用户配置的 OpenAI-compatible HTTPS 服务和系统凭据；本地 mock 只证明协议、边界和安全行为，不等同外部供应商可用性。完整远程数据覆盖、交易所级逐笔/原子快照和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。参考项目只读，未执行 Git stage/commit/push。

## 2026-09-02 18:32 信息总览滚动与证据状态一致性修复

`confirmed`：盘中异动统一时间线容器补充 `overflow-x: auto`，并显式保持 `overflow-y: visible`，满足宽时间线横向查看且不恢复内部纵向滚动；页面新增折叠式证据状态面板，覆盖盘中异动、个股详情、复盘统计、情绪周期、七大人气榜和涨停复盘，复用公共 `DataStatusPanel`，没有新增数据请求或重复状态逻辑。

`confirmed`：前端全量测试 218 个文件/868 项通过；Rust workspace 899 项通过、1 项按设计忽略；Vite 生产构建处理 4024 个模块；文件登记 1895 条、UTF-8 编码扫描 4638 个文本文件、`cargo fmt --check` 与 `git diff --check` 通过。

`confirmed`：最新 Windows x64 阶段 EXE 验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-183228`。主程序 `yishu-desktop.exe` 33,272,832 bytes，PE machine `0x8664`，SHA-256 `5AEBB129DF49D8FC4330833F448B35FA079B59A69F957EA0376961F29F271B1E`；更新助手 SHA-256 `E4C50C6090125A1C31C3A8001325A22813B527A852BC68FB03554C43E614F86F`；后台采集器 SHA-256 `000A51CF4F3A949C10C63FD1CEA5359193D997ED0CD061F76376962518B6ED0D`。主程序从独立目录启动 3 秒后进程与窗口句柄有效，清理后无残留进程；未生成安装包或 ZIP。

`observed`：构建仍有既有 Rust unused/deprecated/linker warnings；完整远程数据覆盖、交易所级逐笔、完整 AI 供应商接入和 macOS 实机验证保持真实 `partial/stale/missing/unavailable` 边界。参考项目、用户配置、缓存和业务数据未修改，未执行 Git stage/commit/push。

## 2026-09-02 18:43 当前源码 Windows x64 阶段 EXE

`confirmed`：基于公司研究 AI HTTP 安全边界与更新助手 smoke 路径修复后的当前源码完成 EXE-only release 构建。验收目录为 `D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-184331`，包含 `yishu-desktop.exe`、`yishu-updater.exe`、`yishu-news-collector.exe` 与 `BUILD-INFO.txt`。主程序 33,272,832 bytes，PE machine `0x8664`，SHA-256 `661191D101B3C9CE574E942AE863C0E6DB38A3D9E5B24A0AC538F81C5CE52185`；更新助手 SHA-256 `282C92E24A6169FD8CBE5BB7EBAD248E37267F125F8264FD69692608118988E2`；后台采集器 SHA-256 `6DBD8A98F2B7BB607D290F04F30B71C825C9554863EF9FC59DB8FEC79D3D08A4`。

`confirmed`：主程序从独立验收目录启动 3000ms 后进程与主窗口句柄有效，终止后同路径残留进程为 0。前端根合同与 Vitest、Rust workspace 899 项通过/1 项按设计忽略、文件登记 1895 条、UTF-8 扫描 4638 个文本文件、`cargo fmt --all -- --check` 与 `git diff --check` 均通过。未生成安装包或 ZIP，未修改参考项目、用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：生产构建保留既有 Rust unused/deprecated/linker warnings；完整远程数据覆盖、交易所级逐笔、完整 AI 供应商可用性和 macOS 实机验证继续保持真实 `partial/stale/missing/unavailable` 边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/OverviewIntradayWorkspace.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/StockDetailsPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ReviewStatisticsPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/SentimentCyclePanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/SevenPopularityRankingsPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/LimitUpReviewPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/dist/yishu-a-share-observation-preview-20260902-183228/BUILD-INFO.txt`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/generate_company_research_ai.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/scripts/smoke-updater.ps1`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/company-ai-contracts-next-report.md`。

## 2026-09-02 数据大屏涨跌停滚动修复

`confirmed`：当前涨停、当前跌停使用独立连续垂直轨道，少量数据固定复制多组以保证可见位移；量化命中和尾盘选股超过 2 条即循环滚动；行业资金流向和底部资讯使用独立横向无缝轨道。修复了全局减少动效规则误停信息轨道、全局极短动画时长覆盖滚动、少量数据轨道过短以及新闻只有淡入没有滚动的问题；悬停仍可暂停可读信息轨道。

`confirmed`：数据大屏 Vitest 139 个文件/840 项通过；Vite 生产构建通过；便携版 `dist/XiaoQiBao-Portable` 已重建。冷启动烟测窗口 88ms 可见、API 2743ms 就绪、完整验证 8907ms 完成，退出后无 `xiaoqibao.exe` 残留。当前便携主程序 SHA-256 为 `898D024590989B1E978C147095E8C48B7042E98CBF4E487E0C995786A2C84531`。

`observed`：烟测中的部分真实数据源仍可能返回 `unavailable/partial`，这属于数据源边界，不影响滚动轨道本身；未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

## 2026-09-02 信息总览视觉密度与动态反馈优化

`confirmed`：信息总览工具栏的刷新、自动刷新、排序、折叠保留为主操作，交易间隔与偏好收纳到默认折叠状态面板；数据大屏限制说明默认折叠；通用表格容器仅允许横向滚动，避免嵌套纵向滚轮。主题层新增玻璃霓虹卡片呼吸、旋转边框、数字更新跳动和列表行闪烁，并沿用页面可见性与 reduced-motion 降级。

`confirmed`：定向视觉合同、前端 Vitest、Vite 生产构建、UTF-8 编码扫描和 `git diff --check` 通过。50 个信息总览工作区继续使用家族标签与贴纸导航；参考项目保持只读，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-02 21:56 时间一致性状态传播修复

`confirmed`：客户端 `buildMarketPulseView` 现在将后端 `temporalConsistency.status` 纳入顶层市场脉搏状态；四路子来源均 ready 但来源时间差超过 10 秒时，顶层降为 `partial`，时间一致性 stale 且存在可用事实时顶层为 `stale`，原有无数据 `missing/unavailable` 语义保持不变。时间差警告和明细仍由同一投影返回，未新增请求、计时器或数据源。

`confirmed`：新增两条 Vitest 回归用例，先验证旧实现红灯，再完成修复并通过；桌面端全量 218 个测试文件、878 项测试通过，Vite 生产构建通过，架构登记 1896 条，UTF-8 扫描 4644 个文本文件，`cargo fmt --all -- --check` 与 `git diff --check` 通过。

`observed`：数据源审计仍确认微观行情约 5 秒刷新、交易所级逐笔/竞价队列、多源原子快照、完整板块成员、完整 AI 外部可用性和 macOS 实机验证属于未完成边界；功能状态继续保持真实 `partial/stale/missing/unavailable`，不以静态或模拟数据冒充实时事实。参考项目只读，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/market-pulse.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/market-pulse.test.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/runtime-refresh-audit-report.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/work/agents/data-source-gap-audit-report.md`。

## 2026-09-02 信息大屏视觉层级与滚动收口

`confirmed`：主题层新增显示专用字号层级变量，统一数据大屏标题、面板标题和核心数字的视觉比例；保留既有可读性下限与契约要求的基础字号。全息背景增加低亮度径向环境光，不增加业务层逻辑或高耗时轮询。

`confirmed`：数据大屏资讯与热点默认只展示首屏有限条目，其余内容通过折叠详情查看；盘中异动、涨停、活跃行情、候选机会、资金流、大单和板块行均采用固定条数或有限样本，并接入 `data-market-row` 以复用真实 DOM 更新闪烁反馈。未引入 mock 数据、额外计时器或内部纵向滚动容器。

`confirmed`：定向全息/字号/信息大屏契约、桌面端 Vitest 218 个文件 878 项、Vite 生产构建、UTF-8 编码扫描、源码清单、文件登记和 `git diff --check` 均通过；浏览器预览确认大屏仅保留页面级滚动，控制台无错误。

`observed`：本轮为视觉与交互密度优化，真实行情刷新仍受数据源刷新周期和状态边界约束；视觉动效不等同于毫秒级实时数据。参考项目保持只读，未执行 Git stage/commit/push，未生成安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/theme.css`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/DataScreenPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/DataScreenAttentionPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/DataScreenFlowPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/DataScreenOpportunityRail.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/data-screen/DataScreenSectorsPanel.svelte`。

## 2026-09-03 数据大屏底部资讯移除与涨跌停双列节奏修复

`confirmed`：数据大屏移除底部资讯滚动条及其 footer DOM；当前涨停与当前跌停固定保持同一行左右两列。连续轨道改为按每条约 4.2 秒的固定可读节奏计算循环总时长，条目增加时只延长完整循环，不再导致滚动加速；补充线性节奏显式声明。

`confirmed`：数据大屏定向回归 28 项、前端全量 Vitest 139 个文件/840 项通过；Vite 生产构建通过。最新便携 EXE 已重建至 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `1CBA495E41CD4B4D51A2E258BD3B7A80C959F6487A09195F68B8557CFFD0D71B`。冷启动烟测通过，窗口 94ms 可见、API 4490ms 就绪、完整验证 9815ms 完成，退出后无残留进程。

`observed`：烟测中的部分真实数据源仍可能为 `unavailable/partial`，这是数据源状态边界，不是滚动实现错误；未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-02 信息总览首屏工作区可达性收口

`confirmed`：市场摘要维持紧凑状态，指数、宽度与双源核验保留在默认关闭的“行情详情”中；空的重要事件雷达收敛为单行状态。开发预览的非真实行情轨道改为紧凑单行信号带，保留明确“模拟预览/非真实行情”标识、独立内存数据边界、命中入场动效和图标化启停控制，但不再挤占总览首屏。

`confirmed`：浏览器在 `1280x720` 实测：动态预览信号带高度从约 147px 收敛至约 64px；工作区家族贴纸导航位于 `y=427-568`，工具栏位于 `y=568-610`，均进入首屏；主内容宽度与滚动宽度均为 1047px，无横向溢出。纵向滚动仅由页面主内容承担，侧栏独立纵向导航滚动保留。

`confirmed`：开发预览模拟器合同、信息总览视觉合同、架构清单（1896 条）、UTF-8 编码扫描（4645 个文本文件）、`git diff --check` 与桌面端 Vite 生产构建（4025 个模块）均通过。未修改参考工程、用户配置、缓存或业务数据，未执行 Git stage/commit/push，未生成安装包或 ZIP。

`observed`：预览轨道仅在开发模式且 URL 显式传入 `previewSimulation=1` 时启用，不能作为真实行情或实时性证据；正式行情继续保留真实 `ready/partial/stale/missing/unavailable` 状态边界。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/dev-preview/PreviewSimulationRail.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/preview-market-simulator-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/reference-overview-visual-contract.test.mjs`。
---
type: project-memory
status: confirmed
updated: 2026-09-03
project_path: "D:/Users/90090/Documents/ChatGPT/A股平台"
sources: ["task:01a03785-a8a0-7a42-88d4-836458a08fb1", "project:金融财经-read-only-reference"]
tags: [project-memory, finance, a-share, desktop, tauri]
---

## 2026-09-03 信息总览空事件状态降噪

`confirmed`：信息总览的重要事件雷达在无真实命中时继续保持 36px 单行收口，并隐藏与顶部全局状态重复的状态徽章，只保留“重要事件雷达 / 暂无命中”可扫描信息；存在真实事件时不改变状态徽章、事件列表或共享 Store 生命周期。新增视觉合同覆盖该行为，文件登记 YAML/Markdown 已同步。

`observed`：该改动只降低空态视觉噪声，不改变 `ready/partial/stale/missing/unavailable` 数据状态，也不补造事件；真实数据服务未启动时仍由顶部状态入口承载详细诊断。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/market-overview/ImportantEventRadar.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-visual-hierarchy-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/file-registry.yaml`。

## 2026-09-03 数据大屏顶部指标与涨停梯队

`confirmed`：数据大屏顶部 KPI 移除独立“炸板数量”和“北向资金”卡片，并将涨停/跌停卡片副文案收敛为封板率，顶部栅格调整为九列，避免移除后出现空位。图表区原有“北向资金待接入”状态说明保持不变，仅顶部展示取消。

`confirmed`：板块情绪面板新增“连板梯队”和“首板梯队”双栏。优先使用共享 `MarketOverviewResponse.review` 的真实日线复盘数据；复盘缺失时首板梯队回退到已加载的首次涨停数据，并明确中文空状态。每栏超过 5 条使用共享连续轨道，以每条约 4.2 秒的固定可读节奏循环滚动，支持点击钻取个股。

`confirmed`：定向数据大屏测试 34 项通过，前端全量 139 个测试文件/847 项通过，Vite 生产构建通过；便携 EXE 已重建至 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。冷启动烟测通过，窗口 331ms 可见、API 5896ms 就绪、14 菜单检查通过，退出后无残留进程。未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：梯队内容依赖本地日线复盘覆盖；复盘接口没有有效样本时，界面会显示“暂无数据”，不伪造连板或首板名单。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-03 板块广度与主线变化高亮

`confirmed`：数据大屏左侧“板块广度与主线”对实时市场快照的前十板块建立内容签名，比较名称、领涨股、涨跌幅、涨跌家数和成交额等字段；首次载入只建立基线，不触发全量高亮。后续仅发生变化或新出现的板块逐项进入高亮状态，独立持续 10 秒后自动恢复普通样式；同一板块在 10 秒内再次变化会重置计时，组件卸载会清理计时器。高亮使用金色边框与轻微内发光，避免长期挂屏刺眼闪烁。

`confirmed`：前端 Vitest 139 个文件/845 项通过；Vite 生产构建通过；便携 EXE 已重建至 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`；冷启动烟测通过，窗口 109ms 可见、API 2758ms 就绪、14 菜单检查通过，退出后无 `xiaoqibao.exe` 残留。`git diff --check` 通过；本轮修改文件 UTF-8/乱码扫描通过。未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：烟测中的部分真实数据源仍可能返回 `unavailable/partial`，这是数据源状态边界，不等同于高亮逻辑异常；视觉高亮不伪造实时行情。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/sectorHighlights.ts`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。
---
type: project-memory
status: confirmed
updated: 2026-09-03
project_path: "D:/Users/90090/Documents/ChatGPT/A股平台"
sources: ["task:01a03785-a8a0-7a42-88d4-836458a08fb1", "project:金融财经-read-only-reference"]
tags: [project-memory, finance, a-share, desktop, tauri]
---

## 2026-09-03 板块情绪封板生态统计

`confirmed`：数据大屏“板块情绪”新增封板生态统计区，展示封板数量、封板率、炸板数量、炸板率、晋级数量和晋级率。封板数量与封板率直接采用市场快照；炸板率按炸板/(封板+炸板)计算；晋级数量采用真实复盘中的连板股票数量，晋级率按今日连板数/昨日涨停数计算。数据不足时显示“--”，不伪造比例。

`confirmed`：指标采用三列紧凑卡片并与左侧板块情绪布局共同约束高度；前端 139 个测试文件/847 项通过，Vite 构建通过，便携 EXE 已重建并完成冷启动烟测，窗口 395ms 可见、API 5889ms 就绪、14 菜单检查通过，退出后无残留进程。

`observed`：晋级率依赖复盘快照同时提供昨日涨停与今日连板样本；若复盘未完成，晋级率保持不可用状态。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.test.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。

## 2026-09-03 板块广度与主线变化高亮

`confirmed`：数据大屏左侧“板块广度与主线”对实时市场快照的前十板块建立内容签名，比较名称、领涨股、涨跌幅、涨跌家数和成交额等字段；首次载入只建立基线，不触发全量高亮。后续仅发生变化或新出现的板块逐项进入高亮状态，独立持续 10 秒后自动恢复普通样式；同一板块在 10 秒内再次变化会重置计时，组件卸载会清理计时器。高亮使用金色边框与轻微内发光，避免长期挂屏刺眼闪烁。

`confirmed`：前端 Vitest 139 个文件/845 项通过；Vite 生产构建通过；便携 EXE 已重建至 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`；冷启动烟测通过，窗口 109ms 可见、API 2758ms 就绪、14 菜单检查通过，退出后无 `xiaoqibao.exe` 残留。`git diff --check` 通过；本轮修改文件 UTF-8/乱码扫描通过。未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：烟测中的部分真实数据源仍可能返回 `unavailable/partial`，这是数据源状态边界，不等同于高亮逻辑异常；视觉高亮不伪造实时行情。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/sectorHighlights.ts`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。
---
type: project-memory
status: confirmed
updated: 2026-09-03
project_path: "D:/Users/90090/Documents/ChatGPT/A股平台"
sources: ["task:01a03785-a8a0-7a42-88d4-836458a08fb1", "project:金融财经-read-only-reference"]
tags: [project-memory, finance, a-share, desktop, tauri]
---

## 2026-09-03 板块广度与主线变化高亮

`confirmed`：数据大屏左侧“板块广度与主线”对实时市场快照的前十板块建立内容签名，比较名称、领涨股、涨跌幅、涨跌家数和成交额等字段；首次载入只建立基线，不触发全量高亮。后续仅发生变化或新出现的板块逐项进入高亮状态，独立持续 10 秒后自动恢复普通样式；同一板块在 10 秒内再次变化会重置计时，组件卸载会清理计时器。高亮使用金色边框与轻微内发光，避免长期挂屏刺眼闪烁。

`confirmed`：前端 Vitest 139 个文件/845 项通过；Vite 生产构建通过；便携 EXE 已重建至 `D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`；冷启动烟测通过，窗口 109ms 可见、API 2758ms 就绪、14 菜单检查通过，退出后无 `xiaoqibao.exe` 残留。`git diff --check` 通过；本轮修改文件 UTF-8/乱码扫描通过。未修改用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：烟测中的部分真实数据源仍可能返回 `unavailable/partial`，这是数据源状态边界，不等同于高亮逻辑异常；视觉高亮不伪造实时行情。

来源：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/DataScreenView.tsx`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/dataScreen.css`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/apps/web/src/features/data-screen/sectorHighlights.ts`、`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。
## 2026-09-03 核心指数双来源核验折叠与目录选择器文档同步

`confirmed`：信息总览的“行情详情”默认关闭；其中“核心指数双来源核验”使用原生 details 二级折叠，外层重新打开时强制重置为关闭。首屏只显示一致数量摘要与自动对比说明，腾讯/东方财富明细仅在用户主动展开后显示；数据源缺失时不生成假明细。浏览器实测首次加载和外层展开均保持二级明细关闭。

`confirmed`：设置页目录选择已接入跨平台原生目录选择器 IPC，Windows 使用系统文件夹对话框，macOS 保留 osascript 适配层，取消、绝对路径和目录存在性由共享客户端统一校验，手动路径输入继续作为后备方式。`docs/architecture/feature-map.yaml` 已同步标记为 `cross_platform_native_directory_picker_with_manual_fallback`。

`confirmed`：定向双来源折叠合同、目录选择器合同与客户端测试、Rust 目录选择器测试、量化 Walk-forward Store 测试、前端行情测试、UTF-8 编码扫描、Vite 生产构建、架构登记和 `git diff --check` 已通过。未修改参考工程、用户配置、缓存或业务数据，未执行 Git stage/commit/push，未生成安装包或 ZIP。

`observed`：当前浏览器环境未启动桌面 Tauri 数据服务时，页面会如实显示 `unavailable/missing`；双来源明细只有在真实后端返回确认事实时才出现。量化 Walk-forward 的最终跨层接线仍需智能体回报后进行一次全量回归。

## 2026-09-03 核心指数双来源核验截图明细默认折叠复核

`confirmed`：用户提供的截图对应“核心指数双来源核验”明细展开态。当前重实现已保持该明细默认关闭：首屏及“行情详情”首次打开只显示一致数量摘要，腾讯/东方财富逐项明细仅在用户主动展开核验标题后显示；关闭外层“行情详情”再重新打开时，内层核验状态会重置为关闭。真实双来源对比、五态状态和缺失字段保真逻辑不变，不使用截图或假数据替代真实来源。

`confirmed`：修正 `tests/features/overview-compact-pulse-contract.test.mjs` 的静态匹配，使其允许 `market-detail-drawer` 携带 `bind:open` 与 `on:toggle` 状态属性，同时继续禁止 `open` 默认属性。双来源折叠合同、紧凑总览合同、全局行情合同、行情 Store 定向测试、TypeScript 编译、文件登记、UTF-8 扫描与 `git diff --check` 均通过。

`observed`：当前浏览器连接不可用，未进行本轮实页截图；折叠行为由 Svelte 初始状态、toggle 重置逻辑和静态合同共同约束。未修改参考工程、用户配置、缓存或业务数据，未执行 Git stage/commit/push。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-index-confirmation-fold-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-compact-pulse-contract.test.mjs`。

## 2026-09-03 量化策略目录与研究快照独立空态链路

`confirmed`：量化分析页新增独立策略目录和量化研究快照模块，分别由跨层 contracts、Rust application use case、Tauri command、TypeScript client/store 与 Svelte panel 组成；不把策略或研究逻辑塞入回测/Walk-forward 文件。当前无真实策略目录来源时返回 `missing`，无研究快照仓储时返回 `unavailable`，不生成假策略、假因子或研究结论。

`confirmed`：量化页移除原先硬编码的“20日均线突破 + 2%动量”策略卡片，改为显示真实目录状态和研究状态；两个 Store 均支持按需加载、同请求 Promise 去重、失败时保留 last-good 并标记 stale。页面挂载时各执行一次读取，不增加轮询。

`confirmed`：新增策略/研究合同测试；TypeScript 编译、Vite 生产构建、Rust `cargo check -p yishu-desktop --offline`、cargo fmt、文件登记和 `git diff --check` 通过。文件登记现为 1963 条。未修改参考工程、用户配置、缓存或业务数据，未执行 Git stage/commit/push。

`observed`：策略候选扫描、因子健康、风险闸门和机会池仍依赖后续真实数据源/研究仓储接入；当前界面仅展示可验证的不可用边界。

## 2026-09-04 核心指数双来源核验默认收起确认

`confirmed`：用户提供的截图是“核心指数双来源核验”明细展开态。本项目继续采用默认收起策略：首次进入总览、打开外层“行情详情”以及路由复用时，只展示一致数量和“自动对比腾讯与东方财富真实数据”摘要；五个指数的逐项来源、差异和缺失字段明细只有用户主动展开二级折叠后才渲染。关闭外层详情后重新打开，二级明细再次收起。

`confirmed`：本轮重新通过双来源折叠合同、总览紧凑合同、文件注册表、架构命令合同、UTF-8 编码扫描、桌面端 TypeScript/Vite 生产构建和 `git diff --check`。真实数据状态和双源比较链路未改变，不使用截图或假数据替代数据源；未修改参考项目、用户配置、缓存或业务数据，未执行 Git stage/commit/push，未生成安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-index-confirmation-fold-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/overview-compact-pulse-contract.test.mjs`、用户截图 `C:/Users/90090/AppData/Local/Temp/codex-clipboard-8fe21b12-8502-4c1f-abaf-38c7955a1c20.png`。

## 2026-09-04 今日研判按交易日冻结账本接入

`confirmed`：今日研判页面新增独立 `decision-ledger-client.ts` 与 `decision-ledger-store.ts`。Store 按交易日读取 `load_decision_ledger`，对同日期请求去重，最多保留有限 LRU 日期快照；空账本返回真实 `missing`，无旧值读取失败返回 `unavailable`，同日期强制刷新失败保留 last-good 并标记 `stale`，晚到旧日期响应不会覆盖当前日期。

`confirmed`：三阶段轨道已改为可点击选择，当前阶段不再被系统时钟强制覆盖；工作台优先展示所选阶段该交易日最新冻结记录，并显示冻结序号、时间和快照编号。冻结成功后仅强制刷新对应交易日账本；实时行情证据和永久冻结证据保持独立。

`confirmed`：新增账本 client/store 测试、阶段冻结记录 presenter 回归和架构合同；定向测试 14 项、全量前端 Vitest 222 文件/893 项、TypeScript 编译、Vite 生产构建、文件登记、UTF-8 扫描与 `git diff --check` 通过。未修改参考项目、用户数据或运行时缓存，未执行 Git stage/commit/push，未生成安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/today-decision/decision-ledger-client.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/today-decision/decision-ledger-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/today-decision/TodayDecisionPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/today-decision/today-decision-workbench-presenter.ts`。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/quant_strategy.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/crates/contracts/src/quant_research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_quant_strategy.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_quant_research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/quant-analysis/QuantStrategyPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/quant-analysis/QuantResearchPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/quant-strategy-research-contract.test.mjs`。

## 2026-09-04 公司研究后台任务

`confirmed`：公司研究主快照新增独立后台任务命令 `start_company_research_task`。任务按股票代码绑定 `company-research:{symbol}`，复用统一 `TaskRegistry` 的进行中/最近成功任务；后台执行现有真实公司研究聚合逻辑，不增加来源、轮询或假数据。任务支持进度、取消和结果序列化，取消/失败不会生成结果。

`confirmed`：前端新增任务 client、Store 和默认折叠 `ResearchTaskPanel.svelte`。Store 负责同标的请求去重、任务等待、取消、结果股票身份校验、last-good/stale 回退和晚到响应隔离；公司研究页面使用任务结果作为主研究快照，其余财务、研报、资本、事项和估值模块仍由各自 Store 并行加载，避免重复请求主研究接口。

`confirmed`：定向后台任务合同、Store 测试、Rust 任务测试、全量前端 Vitest（224 文件/898 项）、Rust 库测试（921 项通过/1 项忽略）、TypeScript/Vite 构建、架构登记、UTF-8 扫描、cargo fmt 和 `git diff --check` 均通过。未修改参考项目、用户数据或运行时缓存，未执行 Git stage/commit/push，未生成安装包、ZIP 或 EXE。

`observed`：任务状态等待沿用共享的有界任务读取器；真实外部来源仍可能返回 `partial/stale/missing/unavailable`，后台任务不会把这些状态升级为 `ready`。公司研究 AI 任务仍保持按需调用边界，未与研究证据任务混合。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/company_research_tasks.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/company-research/company-research-task-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/company-research/ResearchTaskPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/company-research-background-task-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/feature-map.yaml`。

## 2026-09-04 公司研究 AI 后台解释任务

`confirmed`：公司研究 AI 解释新增独立 `start_company_ai_task` 后台命令。命令只接受六位股票代码、非空冻结证据版本和证据文本，任务键由股票、证据版本、证据文本和模型名的 SHA-256 组成，不把原始证据直接放入任务 ID；任务复用统一 `TaskRegistry`，支持进度、取消、30 秒内最近结果复用和结果序列化，取消或失败不发布结果。

`confirmed`：前端新增 AI 任务 client/store，`ResearchAiPanel.svelte` 仅在用户点击“请求解释”时提交任务，不在挂载或行情刷新时自动调用。Store 负责同请求 Promise 去重、共享任务等待器、取消、股票身份校验、last-good/stale 回退和晚到响应隔离；结果继续使用真实 `EvidenceEnvelope` 五态，不把不可用状态伪装为可用解释。

`confirmed`：功能地图已将 `start_company_ai_task` 列为公司研究真实实现，YAML 与 Markdown 文件注册表同步登记新增命令、客户端、Store、测试；定向 AI 合同、Store 测试、前端全量 Vitest（225 文件/901 项）、Rust 库测试（922 项通过/1 项忽略）、TypeScript/Vite 构建、架构检查、注册表检查、UTF-8 编码扫描、cargo fmt 和 `git diff --check` 均通过。未修改参考工程、用户配置、缓存或业务数据，未执行 Git stage/commit/push，未生成安装包、ZIP 或 EXE。

`observed`：AI 供应商配置、网络状态和模型能力仍由既有 AI 用例决定；后台任务只改变执行生命周期，不扩大证据范围、不生成虚假研究事实，也不替代主研究快照任务。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/company_research_ai_tasks.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/ai.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/company-research/company-research-ai-task-store.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/company-research/ResearchAiPanel.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/company-research-ai-background-task-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/feature-map.yaml`。

## 2026-09-04 量化策略目录绑定真实回测规则

`confirmed`：量化分析策略目录不再返回“尚未接入真实来源”的空缺状态，而是登记当前回测引擎已经实现且可核验的唯一规则：`ma20-momentum-2pct`，名称为“20日均线突破 + 2%动量”，公式版本 `backtest-v1`。规则要求 `trade_date`、`open`、`close` 字段，描述为收盘站上前20日均线且较前一交易日上涨超过2%，次日开盘入场并按持有期退出。

`confirmed`：策略目录通过独立 `load_quant_strategy` use case、IPC、Store 与面板返回 `ready`，目录版本为 `builtin-2026-09-04`，来源为 `quant-strategy-catalog:builtin`；目录只登记已经实现的回测规则，不生成未实现候选。量化研究快照仍保持真实 `unavailable` 边界，回测的交易日历、停牌、涨跌停、复权和真实预测模型缺口未被掩盖。

`confirmed`：策略目录合同测试和 Rust 定向单测均通过；同步更新功能地图、功能对照矩阵、复刻账本及文件注册表。未修改参考工程、用户配置、缓存或业务数据，未执行 Git stage/commit/push，未生成安装包、ZIP 或 EXE。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_quant_strategy.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/quant/backtest.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/tests/features/quant-strategy-research-contract.test.mjs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/feature-map.yaml`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/verification/feature-parity-matrix.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/reference-parity-ledger.md`。

## 2026-09-04 配置级数据源能力路由

`confirmed`：新增 `select_configured_source` 配置级路由。路由仅考虑启用的数据源、配置中声明了目标 `DataCapability` 的数据源，并要求整体 `SourceProbeReport` 与目标能力探针均为 `ready/partial/stale`；按数值优先级升序选择，返回能力级真实状态并保留 `stale`。禁用来源、未声明能力和 `missing/unavailable` 探针均被排除。

`confirmed`：旧版 `select_source(priority, probes, capability)` 保持不变，避免破坏现有适配器；新增三项 Rust 回归测试覆盖禁用来源、能力声明/可用性门禁及优先级与 stale 保留。`cargo test -p yishu-desktop source_router --offline` 5 项通过，`cargo check -p yishu-desktop --offline`、`cargo fmt --all -- --check`、数据源设置合同、文件登记（1988 条）、UTF-8 扫描和 `git diff --check` 均通过。未修改参考工程、用户数据或运行时缓存，未执行 Git stage/commit/push，未生成安装包、ZIP 或 EXE。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/data/source_router.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/file-registry.yaml`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/file-registry.md`。

## 2026-09-04 TickFlow/TuShare 连接探测收口

`confirmed`：数据设置中的 `test_data_source_connection` 已改为异步短探测。TickFlow 使用单标的报价请求并发送系统凭据中的认证头；TuShare 使用低成本 `trade_cal` 官方 POST 请求。网络请求独立于 UI 线程，连接超时约 3 秒、请求超时约 5 秒、无重试、并发上限 1。

`confirmed`：探测结果保留真实五态：未配置凭据为 `missing`，网络或服务不可达为 `unavailable`，权限、业务错误或无法解析响应为 `partial`，合法响应为 `ready`；成功探测记录 UTC RFC3339 `observed_at`。错误文案不回显 API Key、Token 或供应商原始敏感内容。fuyao 协议尚未核验，继续固定 `unavailable` 且不发起网络请求。

`confirmed`：同步更新依赖登记、来源清单和功能地图，连接探测与凭据 IPC 已登记为独立能力。`cargo test -p yishu-desktop commands::settings --offline` 7 项通过；未修改参考工程、用户配置、缓存或运行时数据，未执行 Git stage/commit/push，未生成安装包、ZIP 或 EXE。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/settings.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/dependencies.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/source-inventory.md`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/feature-map.yaml`。

## 2026-09-04 TickFlow 实时行情业务路由

`confirmed`：新增独立实时行情应用路由。用户启用 TickFlow、声明实时行情能力且系统凭据库存在 API Key 时，信息总览、今日研判、个股驾驶舱和公司研究优先并发读取 TickFlow；任一标的失败、解析不完整、未配置或网络不可用时，整批回退腾讯，避免同一批行情混用来源。

`confirmed`：TickFlow 与腾讯使用独立缓存键；TickFlow 缓存 10 秒，腾讯缓存 30 秒，均复用现有内存/SQLite 两级缓存和请求去重。TickFlow 成交额不映射为换手率、缺失盘口不伪造，来源字段随实际命中源返回。设置保存后热更新内存中的非敏感数据源配置；API Key 仍只按需从系统凭据库读取，不进入状态结构、缓存、日志或 DTO。

`confirmed`：TuShare 尚未完成实时行情字段合同，不进入本轮实时路由；fuyao 协议未核验，仍不发起网络请求。本阶段未修改参考工程、未执行 Git 提交，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/data/realtime_quotes.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/core_menu.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/settings.rs`。

## 2026-09-04 TickFlow 日线可选来源接入

`confirmed`：个股驾驶舱远程日线链路新增 TickFlow 可选优先路径。仅当来源已启用、声明 `DailyKline` 能力且系统凭据库存在 API Key 时，按 `1d` 区间请求 TickFlow；响应经日期窗口、股票代码、字段和来源校验后投影为现有 `StockRemoteDailySnapshot`，使用独立缓存键，不与东方财富缓存混用。

`confirmed`：TickFlow 日线失败、配置无效或字段不足时自动回到既有东方财富日线链路；成交额映射到 `amount`，缺失 OHLC/成交量字段保留为空，非法日期行计入 `discarded_count`，不生成假值。设置、凭据、参考项目和 Git 状态边界不变。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_stock_remote_daily.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/core_menu.rs`。

## 2026-09-04 TickFlow 分时可选优先接入（obsolete）

`confirmed`：个股分时链路新增 `execute_with_sources`。当 TickFlow 已启用、声明 `Intraday` 能力且系统凭据库存在 API Key 时，先请求 `/v1/intraday`；响应通过独立投影函数校验股票代码、交易日、分钟顺序、连续竞价范围及累计量额，再转换为共享 `StockIntradaySnapshot`。TickFlow 使用独立 10 秒两级缓存和请求去重，失败、字段不足或身份不匹配时回退既有腾讯→东方财富链路，不合并两源分钟点。

`confirmed`：分时投影仅接受已知 JSON 字段组合（`items`、`timestamp/time/minute`、`price/last/close`、`volume/vol`、`amount/turnover`），非法日期、倒序时间、累计量额倒退和盘外异常点不会被伪造为有效数据；缺失价格、成交量或成交额的行计入 `discarded_count`，不以零值冒充来源事实，状态继续由证据层判定为 `partial` 或 `unavailable`。TickFlow API Key 仍只从系统凭据库按需读取，不进入配置状态、缓存或日志。

`confirmed`：`stock_intraday` IPC 已传递数据源配置和 TickFlow 凭据句柄；新增 3 项投影回归测试，`cargo test -p yishu-desktop load_stock_intraday --offline` 7 项通过，`cargo check -p yishu-desktop --offline` 与格式检查通过。未修改参考工程、用户数据或运行时缓存，未执行 Git stage/commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_stock_intraday.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/stock_intraday.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/docs/architecture/file-registry.yaml`。

## 2026-09-04 TickFlow 官方分时协议修复与历史研判隔离

`confirmed`：前一条 TickFlow 分时结论已被标记为 obsolete。真实官方协议为 `GET /v1/klines/intraday`，参数为标准交易所代码、`period=1m` 和 `count`；响应使用 `data` 下的列式 `timestamp/open/high/low/close/volume/amount`。重实现现在先校验列长度、有限值、OHLC 关系、时间递增、单交易日和容量上限，再把 epoch 毫秒按 UTC+8 转换为分钟。`close` 作为分钟价格，`volume/amount` 按单根分钟值累加为共享 DTO 的累计量额；未对官方未明确的股/手单位做臆测。

`confirmed`：分时链路的 TickFlow 快照已加入三源 stale-if-error 最新观测时间选择，失败信封按实际来源记录；独立缓存和请求去重保持 10 秒，API Key 仍只从系统凭据库按需读取。定向 `load_stock_intraday` 测试 8/8 通过，覆盖官方列式投影、上海时区、量额累加、坏值/倒序/跨日/容量拒绝和三源旧快照选择。

`confirmed`：今日研判页面新增历史交易日选择。实时模式继续使用共享行情；历史模式只读取永久冻结账本，隐藏实时情绪与冻结动作，若无记录或账本读取失败则显示 `missing/unavailable/stale` 真实空态，不混入当前行情事实。前端合同与相关 Presenter 测试通过，全量前端 Vitest 为 228 文件/909 项。

`confirmed`：TuShare 日线新增官方 POST `daily` 备用来源，按启用状态、能力声明、优先级和凭据门禁参与；独立缓存键与响应校验保留缺失字段。`core_menu` 已读取系统凭据并调用双凭据入口。连接探测仍使用 `trade_cal`，fuyao 协议未核验不发起请求。

`confirmed`：今日研判后端 `load_today_decision` 已并发复用指数、市场宽度、成交和本地九因子情绪用例，真实填充 phase、sentiment_score、evidence_count、risk_gate 与摘要，并聚合子来源状态、时间、交易日、缺失字段和警告；当前前端页面仍以共享 pulse Store 做实时投影，历史模式只读取冻结账本，不把后端缺失字段升级为完整研判。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/tickflow.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_stock_intraday.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/today-decision/TodayDecisionPage.svelte`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/today-decision/today-decision-history-presenter.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/infrastructure/sources/tushare.rs`。

## 2026-09-04 量化研究与组合风险真实计算增量

`confirmed`：量化研究快照现在只从本地业务库日线计算累计收益、20 日均线距离、5 日量比、年化波动率、最大回撤及 RankIC/ICIR；样本不足或字段非法返回 `missing/partial`，并公开因子、健康和机会模块状态，不生成随机值。相关 Rust/前端合同、Store、面板和文件注册表已同步。

`confirmed`：单标的时间序列不再被误称为横截面 RankIC/ICIR；当前机会信号保持 `missing`，直到接入按交易日对齐的多标的横截面样本。风险输入失败不再静默压成空数据；观察篮子无报价和历史日线时返回 `unavailable`。部分持仓缺价时组合总市值、总盈亏、权重和压力盈亏保持缺失，压力冲击比例仍显示真实 -5/-10/-20%。重复交易日会使历史风险和相关性证据缺失。

`confirmed`：信息总览的问财选股与个股详情复用同一份全市场横截面共享缓存。服务端支持多条件筛选、搜索、排序和最多 100 行分页；缺失字段进入 `pending`，详情按股票身份隔离并保留真实 stale/unavailable。异动排名仍独立保持最多 200 行语义，不与全市场筛选混用。新增前端 Store、Tauri 命令、跨层 DTO、合同测试和文件注册表已同步。

`confirmed`：风险工作台新增共同交易日收益 Pearson 相关性、权重 HHI 集中度和 -5%/-10%/-20% 机械压力情景。相关性共同样本不足时保留空值；行业与事件风险仍保持真实缺口，不以零值填充。组合面板默认折叠相关性与压力明细，避免增加滚动负担。

`confirmed`：量化定向测试 4 项、风险定向测试 4 项、`cargo check -p yishu-desktop --offline`、`cargo fmt --all`、文件注册表、来源清单、UTF-8 扫描和 `git diff --check` 均通过。未修改参考工程、用户数据或运行时缓存，未执行 Git stage/commit/push，未生成 EXE、安装包或 ZIP。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/quant/research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/load_quant_research.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/domain/risk/portfolio_risk.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/application/use_cases/evaluate_risk.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/feature/risk/PortfolioRiskPanel.svelte`。

## 2026-09-04 来源时间与接收时间最终收口

`confirmed`：全局 `market_pulse` 合同新增独立 `received_at`。聚合 `observed_at` 仅从核心指数、市场宽度、历史成交、九因子和实时成交子证据中筛选合法 RFC3339 来源时间，并按解析后的绝对时刻排序；没有有效来源时间时保持空值。前端事件门禁改用聚合 `received_at` 判断新旧，允许来源时间缺失时仍接收真实新快照，同一接收时刻只有内容变化才接受。

`confirmed`：本地日线成交额、东方财富市场宽度和本地九因子计算不再把本机执行时钟写入 `observed_at`。九因子仅在实际采用且具备来源时间的板块资金流或横截面辅助证据时贡献观测时间；本地接收/归档时刻与来源时间保持独立。总览状态栏在折叠详情中分别显示来源观测和本地接收时间。

`confirmed`：新增来源时间缺失、非法时间、跨时区绝对排序、缓存 stale 保留、同刻内容变化和本地成交/宽度/九因子空来源时间回归测试。定向前端 18 项、市场脉冲 Rust 4 项、成交 Rust 3 项、九因子 Rust 6 项及相关合同测试通过；Vite 生产构建处理 4058 个模块通过。全量门禁仍待本轮结束后执行。

来源：`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_pulse.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_overview.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_sentiment.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src-tauri/src/commands/market_turnover.rs`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/market-pulse-events.ts`、`D:/Users/90090/Documents/ChatGPT/A股平台/apps/desktop/src/app/GlobalMarketPulse.svelte`。
