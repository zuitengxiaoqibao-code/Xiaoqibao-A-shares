# 一树-A股观测台

一树-A股观测台（软件全称：一树电子商务-A股观测台）是一套面向个人研究者和新手的本地 A 股研究、行情观察、量化筛选与风险提示工具。它把实时行情、历史日线、基本面、新闻事件、策略因子、回测和 AI 解释放在同一个 Windows 工作台中，帮助用户先把证据看清楚，再决定是否继续研究。

项目的正式用户入口是 Windows 便携版 EXE。React/Vite 前端和 FastAPI 服务被嵌入桌面程序中，浏览器和 localhost 只用于开发和内部诊断，不是最终交付入口。

> **重要边界**：本项目不连接券商、不下单、不提供自动交易、不创建模拟账户或模拟委托，也不构成投资建议。所有研判都应结合原始行情、公告、财报和个人风险承受能力独立复核。

## 目录

- [项目定位与原则](#项目定位与原则)
- [功能地图](#功能地图)
- [数据来源与真实性边界](#数据来源与真实性边界)
- [系统架构](#系统架构)
- [Windows 便携版部署](#windows-便携版部署)
- [开发环境部署](#开发环境部署)
- [数据补齐与通达信配置](#数据补齐与通达信配置)
- [AI 与 Kronos](#ai-与-kronos)
- [监控中心与盘后复盘](#监控中心与盘后复盘)
- [构建、打包与验证](#构建打包与验证)
- [故障排查](#故障排查)
- [仓库结构与安全](#仓库结构与安全)

## 项目定位与原则

### 先证据，再结论

系统将每个结果绑定到数据来源、观察时间、交易日和覆盖状态。AI 只能解释已经冻结的证据，不能补造价格、利润、概率或事件，也不能改写确定性规则的动作、置信度和风险门禁。

### 数据状态必须可见

页面使用统一状态表达数据质量：

| 状态 | 含义 |
| --- | --- |
| `ready` | 必要字段齐全，来源和时间可核验 |
| `partial` | 有部分真实数据，但存在缺口；页面会列出缺少的字段或来源 |
| `stale` | 使用上一次成功快照，已超过当前新鲜度阈值 |
| `missing` | 尚未形成可展示的真实记录 |
| `unavailable` | 来源、授权、网络、权限或本机环境暂时不可用 |

缺失数据不会被静默替换成 0、随机值或估算值。后台刷新时先展示上一次完整缓存，并明确标注更新时间；刷新失败会保留原因和重试建议。

### 本地优先、可追溯、可恢复

运行数据写入本地目录，来源健康、任务进度、补齐记录、快照和审计信息都可追踪。数据同步采用幂等写入和多源回退，不覆盖正在使用的便携目录，也不会主动删除用户历史数据。

### 股票视觉规则

A 股页面统一使用“红涨绿跌”：上涨、正收益和积极信号使用红色；下跌、回撤和风险信号使用绿色；黄色/蓝色/紫色用于数据状态、来源类别和中性信息，避免与涨跌含义混淆。

## 功能地图

| 菜单 | 主要用途 | 典型输出 |
| --- | --- | --- |
| **信息总览** | 全市场快速体检 | 指数、市场广度、涨跌停、成交热度、资金与热点总览 |
| **今日研判** | 识别当天市场环境 | 九因子情绪仪表盘、市场阶段、证据覆盖、行动建议 |
| **个股观察** | 研究单只 A 股 | 实时行情、K 线、事件、风险门禁、数据质量、观察结论 |
| **公司研究** | 做基本面与反方研究 | 商业模式、行业空间、营收利润、现金流、竞争壁垒、估值、催化和风险 |
| **首次涨停** | 识别阶段首次涨停并跟踪回撤 | 规则证据、估值/位置过滤、回撤窗口和后续观察池 |
| **尾盘选股** | 收盘前识别量价形态 | 六类尾盘形态、可调规则、14:30 后动态监控、AI 解释和无结果原因 |
| **量化分析** | 策略、因子和回测工作台 | Kronos 价格路径、Tick/分时、市场策略、候选池、信号、回测和风险收益 |
| **新闻热点** | 过滤并关联有效资讯 | 新闻时效、来源、股票代码/名称、板块归因和影响摘要 |
| **风险提醒** | 组合与标的风险检查 | 风险闸门、回撤窗口、涨停日禁买、风险明细和可点击筛选 |
| **历史复盘** | 复核过去的判断和策略 | 5/20 日均线回测、收益、回撤、波动、胜率、成本和阶段归因 |
| **监控中心** | 配置自动提醒 | 行情/成交/策略/新闻/风险规则，启停、删除、测试、语音和飞书通道 |
| **数据设置** | 管理来源和 AI | 通达信目录、来源授权、字段映射、AI 地址/模型/密钥和健康状态 |
| **本地运维** | 修复、同步、备份和诊断 | 一键全面修复、下载/解压/校验进度、覆盖率、任务脚本、备份恢复 |
| **可转债** | 独立的可转债研究域 | 行情、条款、估值、正股关联和数据源授权；不与 A 股状态混合 |

任意已核验的六位 A 股代码都可以进入个股观察和公司研究；候选池只是研究阶段的筛选结果，不会限制用户查看单只股票。量化分析支持按代码或名称搜索，并记住最近使用的分析标的。

## 数据来源与真实性边界

系统会在每个模块显示实际来源和观察时间。当前主要来源及用途如下：

- **腾讯行情**：批量实时行情、指数和盘中快照；缺失股票会定向重试一次。
- **通达信 `mootdx`**：优先读取本地沪深日线、趋势和部分财务快照；支持多个通达信目录评分和有序回退。
- **百度 K 线**：通达信节点不可用时的日线回退源；入库前校验日期唯一性、行宽和 OHLC 边界。
- **通达信财务/F10**：公司基本面字段；纯元数据或空响应不会被视为有效财务数据。
- **东方财富**：资金流、个股资讯和部分市场数据；分钟资金流失败时保留日报并标注为部分可用。
- **同花顺**：盘中热点和题材归因；只写入已解析的代码、名称、交易日和标签。
- **巨潮资讯**：公告、证券基础目录和部分官方回退数据。
- **本地事件仓储**：仅保存已采集、去重、带来源和时间的事件；无代码新闻必须完成标的关联后才进入确定性依据。

公开接口可能限流、改版、断网或要求授权。遇到这种情况，页面会显示 `partial` 或 `unavailable` 及可操作的修复建议；不会把旧日期冒充今天，也不会把旧缓存伪装成实时数据。K 线事件、新闻和 AI 解释均以实际证据时间为准。

## 系统架构

```text
Windows EXE / pywebview
        |
        +-- React + TypeScript + Vite（内嵌 web 资源）
        |
        +-- FastAPI 本地 API
              |
              +-- 统一行情/日线/新闻/财务数据访问层
              +-- 缓存、来源健康、任务进度与审计仓储
              +-- 研究、因子、策略、回测、风险和监控服务
              +-- 本地 AI/Kronos 适配器（可选、懒加载）
              +-- SQLite / DuckDB / Parquet 本地数据文件
```

前端不硬编码行情结果。菜单调用统一 API，API 再按数据域复用数据层、缓存和来源健康记录。长任务通过任务状态接口返回阶段、当前动作、计数、速度、预计剩余时间和中文失败原因，避免“1% 不动后突然 100%”。

## Windows 便携版部署

### 直接运行仓库中的便携版

Windows 10/11 用户无需安装 Python、Node.js 或开发服务器：

```text
release\XiaoQiBao-Portable\xiaoqibao.exe
```

请把整个 `XiaoQiBao-Portable` 目录复制到目标电脑，不要只复制 EXE。以下内容是运行必需的：

- `_internal`：PyInstaller 运行库和 Python 依赖。
- `web`：内嵌 React 生产资源。
- `xiaoqibao.exe`：桌面启动入口。
- `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`：程序运行时创建或维护的持久目录。

便携版不写注册表、不要求管理员权限。程序首次启动会创建缺失目录；运行时配置、行情数据库、新闻、缓存和日志都留在 EXE 同级目录。系统需要 Microsoft Edge WebView2 Runtime；Windows 10/11 通常已预装，若无法打开窗口，请先安装 WebView2 Evergreen Runtime。

### 给测试人员的纯程序包

测试包只包含程序和空的运行目录，不携带源码、行情数据库、新闻、缓存或日志。进入程序后打开 **本地运维 → 一键全面修复数据**，按页面进度下载、解压、校验并导入真实数据。

带默认 AI 配置的测试包只应交给获授权的测试人员，不应上传到公开 Git 仓库或转发到不受控渠道。公开仓库和普通程序包不包含 API 密钥。

## 开发环境部署

### 环境要求

- Windows 10/11
- Python 3.12 或更新版本
- Node.js 22 或更新版本
- pnpm 10 或更新版本
- Git

### 安装与启动

```powershell
git clone https://github.com/zuitengxiaoqibao-code/Xiaoqibao-A-shares.git
cd Xiaoqibao-A-shares

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\apps\api[dev]"
pnpm.cmd install

powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

开发脚本会启动本地 API 和 Vite 开发服务：

- API：`http://127.0.0.1:8000`
- Web：`http://127.0.0.1:5173`

开发阶段可以用浏览器访问 Web 地址进行诊断；交付用户和验收仍应使用便携版 EXE。默认运行数据写入项目根目录 `.runtime`，需要隔离数据时设置绝对路径：

```powershell
$env:QIBAO_DATA_DIR = "D:\qibao-runtime"
```

## 数据补齐与通达信配置

### 一键全面修复

在 **本地运维** 中执行“一键全面修复数据”后，任务按以下阶段运行：

1. 检查本机通达信目录和本地数据权限。
2. 扫描各目录中的沪深日线文件，实时显示已扫描/总文件、可读文件数、当前文件、速度和剩余时间。
3. 读取官方日线包元数据，自动兼容 UTF-8、UTF-8-SIG、GB18030 和 GBK。
4. 按缺口下载、解压、校验并导入官方数据或备用源。
5. 校验最新交易日、证券覆盖率、日期连续性和数据库可读性。
6. 生成来源健康、补齐结果和可追溯的任务记录。

如果数据库正被另一个任务占用，页面会显示“等待本地数据库释放并自动重试”，不会把已经完成的扫描误报成失败，也不会删除或覆盖原始数据。

### 多通达信版本

程序会发现常见安装目录，并按“最新交易日、可读取日线数、A 股覆盖率、文件活跃时间”评分，选择最高分目录作为主源，其余目录作为缺口回退源。用户也可以在 **数据设置** 中手动指定目录，例如：

```text
D:\new_tdx_mock
```

主源缺少某只股票或某个日期时，系统按评分顺序补读其他目录；同日冲突保留评分更高的来源，并记录实际来源，不静默覆盖。

## AI 与 Kronos

### 本地 AI 设置

在 **数据设置 → AI 配置** 中填写 OpenAI 兼容接口地址、模型和密钥，或通过环境变量提供：

```powershell
$env:QIBAO_AI_BASE_URL = "https://your-compatible-endpoint/v1"
$env:QIBAO_AI_API_KEY = "your-api-key"
$env:QIBAO_AI_MODEL = "your-model"
```

三项必须同时有效才会请求模型。AI 用于公司研究总结、新闻归纳、盘后复盘、候选解释和监控说明；确定性规则先运行，AI 只解释冻结证据。未配置、超时、限流、非法 JSON 或引用越界时，页面保留确定性结果并显示中文降级原因。

密钥只保存在本机运行目录的受保护配置中，接口仅返回“在线/离线/异常”等状态和脱敏信息，不返回完整密钥。请勿把 `.env`、`data/ai-settings.json` 或带密钥的测试包提交到 Git。

### Kronos 价格路径预测（可选）

“首次涨停 → 量化分析”可选接入 [Kronos](https://github.com/shiyu-coder/Kronos)，使用本地真实日线生成未来 5 至 20 个交易日的情景路径。页面展示中位路径、分位区间、下行概率和路径分歧度；结果只作为研究证据，不改变规则结论，也不生成交易指令。

Kronos 默认关闭，第一次预测请求才加载模型，不阻塞 API 启动。启用前按官方仓库安装 PyTorch 和依赖，并设置：

```powershell
$env:QIBAO_KRONOS_ENABLED = "true"
$env:QIBAO_KRONOS_REPO_PATH = "D:\path\to\Kronos"
$env:QIBAO_KRONOS_MODEL = "D:\path\to\Kronos-mini"
$env:QIBAO_KRONOS_TOKENIZER = "D:\path\to\Kronos-Tokenizer-2k"
$env:QIBAO_KRONOS_DEVICE = "cpu"
$env:QIBAO_KRONOS_LOOKBACK_BARS = "250"
$env:QIBAO_KRONOS_SAMPLE_COUNT = "20"
```

模型权重可使用本地路径或 Hugging Face 名称；首次加载需要网络可用。模型不可用时页面显示“模型未启用/暂不可用”，不会用随机曲线填补。

## 监控中心与盘后复盘

**监控中心**支持预置中文规则和自定义条件。每条规则都可以启用、暂停、恢复、停止、删除和测试；测试按钮可以验证站内消息、Edge TTS 语音和飞书投递是否真正可用。规则触发后保存快照、去重键、冷却时间、投递结果和失败原因。

监控主题覆盖价格、成交、量化策略、新闻热点、尾盘候选和风险分数。飞书 Webhook、语音和站内通知互相隔离，某一通道失败不会阻断其他通道。所有字段在界面上使用中文名称，底层字段路径仅保存在审计记录中。

收盘后，确定性程序先冻结市场阶段、候选、风险归因和次日观察事项，再由 AI 生成简洁摘要。配置了飞书后，可将盘后报告投递到指定群；未配置或投递失败时显示真实状态，不伪造“已发送”。

## 构建、打包与验证

### 构建便携 EXE

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1
```

脚本会同步 API 依赖、运行 API/Web 测试、构建 Vite 前端、使用 PyInstaller 生成 EXE，并保留已有 `config/data/news/cache/logs/models/exports/backups` 持久目录。若正式 EXE 正在运行，脚本会生成 `dist\XiaoQiBao-Portable-staged-*`，不会覆盖正在使用的目录；用户退出后由更新流程应用。

无数据环境构建可使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1 -SkipTests -SkipPersistentData
```

### 生成测试包

```powershell
# 仅程序，不带行情、新闻、缓存、日志和源码
powershell -ExecutionPolicy Bypass -File .\scripts\package-portable-test.ps1 -ProgramOnly

# 程序 + 默认 AI 配置（仅限授权测试人员）
powershell -ExecutionPolicy Bypass -File .\scripts\package-portable-test.ps1 -ProgramOnly -IncludeDefaultAIKey

# 无历史数据但保留公开测试配置
powershell -ExecutionPolicy Bypass -File .\scripts\package-portable-test.ps1 -DataFree
```

脚本会把压缩包写入 `dist`，并排除发布清单、数据库、缓存和日志（具体以参数为准）。带密钥包必须通过私下渠道分发。

### 验证实际 EXE

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-portable-smoke.ps1 `
  -PortableRoot .\dist\XiaoQiBao-Portable

powershell -ExecutionPolicy Bypass -File .\scripts\verify-release-quality.ps1 `
  -ReleaseRoot .\dist\XiaoQiBao-Portable
```

验收重点包括：窗口是否出现、API 是否就绪、菜单请求是否可用、数据状态是否诚实、关闭后是否有残留 `xiaoqibao.exe`、发布文件 SHA-256 是否一致，以及备份恢复演练是否通过。

常用开发检查：

```powershell
\.venv\Scripts\python.exe -m pytest apps\api\tests -q
\.venv\Scripts\python.exe -m ruff check apps\api\src apps\api\tests scripts\restore_backup.py
pnpm.cmd --filter @qibao/web test
pnpm.cmd --filter @qibao/web build
git diff --check
```

## 故障排查

### EXE 无法启动或重复弹窗

1. 确认运行的是完整 `XiaoQiBao-Portable` 目录，而不是单独复制的 EXE。
2. 检查 `_internal`、`web` 和 WebView2 Runtime 是否存在。
3. 查看同级 `logs\xiaoqibao.log` 和启动状态提示。
4. 若上次更新被中断，关闭当前程序后重新启动；更新助手会把失败更新改为暂缓，不会无限重试。

### 数据修复停在扫描或 5%

查看当前阶段是否为“扫描本机日线”或“等待本地数据库释放”。扫描总量未知时进度条会显示实时计数而不是伪造百分比。确认没有其他一树程序占用 `data\market.duckdb`，等待任务结束后再重试；不要删除数据库文件。

### 页面提示请求超时

超时只表示某个数据源或任务阶段暂时没有返回，不代表整个程序退出。先查看页面的来源状态和最近成功时间，再在 **数据设置/本地运维** 执行对应数据域的重试。旧缓存会标记为 `stale`，新数据成功后自动替换。

### AI 显示异常

确认地址、模型和密钥三项配置完整，并在数据设置中使用测试按钮验证。未配置显示“离线”；已配置但接口连接失败、超时、限流或模型不存在显示“异常”。AI 异常不会阻断行情、规则和回测结果。

### 数据库被占用

同一便携目录只运行一个 EXE 实例。构建或恢复请使用新目录，不要覆盖正在运行的目录；恢复脚本也要求输出到新路径：

```powershell
\.venv\Scripts\python.exe .\scripts\restore_backup.py `
  backup-20260714T133107Z-e1148658 `
  .\.runtime-restored
```

## 仓库结构与安全

```text
apps/api/                 FastAPI、本地数据层、研究/策略/风险/监控服务
apps/web/                 React + TypeScript 前端
scripts/                  开发、构建、打包、烟测、备份恢复脚本
packaging/                PyInstaller 配置、图标和便携版说明
docs/                     架构、路线图、验证记录和 API 参考
release/XiaoQiBao-Portable/  可运行的 Windows 便携版快照
```

以下目录被 Git 忽略，不能作为公开源码的一部分：`config/`、`data/`、`news/`、`cache/`、`logs/`、`models/`、`exports/`、`backups/`、`.runtime/`、`.venv/` 和 `dist/`（仓库内的 `release/` 是经过筛选的程序快照）。API 密钥、Webhook、Cookie、数据库和个人行情文件都必须留在本机。

发布前请保留 EXE、发布清单和压缩包的 SHA-256，便于测试人员确认拿到的是同一版本。所有新数据源都应记录来源、观察时间、授权状态、失败原因和字段校验结果。

## 路线与贡献

当前交付重点是：真实数据边界、快速启动、缓存优先、来源健康、可追溯补齐、受控策略和可验证提醒。后续工作包括扩大已核验事件覆盖、增加策略的样本外验证、完善可转债专属数据域、扩展监控规则和持续优化启动/菜单性能。详细状态见 [docs/roadmap.md](docs/roadmap.md)。

提交改动前请运行 API/Web 测试、生产构建、`git diff --check` 和便携版烟测。不要提交运行数据、密钥或个人配置。

## 免责声明

本项目仅用于信息整理、量化研究和风险提示。数据可能因来源限制、网络、授权、交易时段或本机配置而不完整或延迟；任何页面结论都不能替代公告、财报、专业投顾意见或个人独立判断。使用本项目产生的投资决策和损益由使用者自行承担。
