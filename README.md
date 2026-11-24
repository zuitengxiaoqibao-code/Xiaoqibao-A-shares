# 易数智算 · A 股观测台

面向个人投资研究的本地工作台，将市场行情、历史日线、新闻事件、个股研究、策略筛选、回测与风险提示集中在一个 Windows 桌面程序中。

**可以直接下载便携版使用，也可以下载源码自行部署、修改和构建。个人非商业部署使用免费；未经书面许可，禁止商用。** 本项目采用[个人非商业许可](LICENSE)，属于公开源码项目，不采用允许自由商用的 OSI 开源许可证。

本项目不连接券商、不下单、不提供自动交易；页面信息、策略结果和 AI 解释均不构成投资建议。

## 选择你的使用方式

| 方式 | 适合人群 | 入口 |
| --- | --- | --- |
| 下载成品，解压运行 | 想直接使用的 Windows 用户，无需安装 Python 或 Node.js | [下载 Windows x64 便携包](https://github.com/zuitengxiaoqibao-code/Xiaoqibao-A-shares/raw/refs/heads/main/release/XiaoQiBao-Portable-Windows-x64.zip) |
| 下载完整仓库 | 想同时保留源码与可运行程序 | [下载仓库 ZIP](https://github.com/zuitengxiaoqibao-code/Xiaoqibao-A-shares/archive/refs/heads/main.zip)，程序位于 `release/XiaoQiBao-Portable/` |
| 源码部署 | 希望研究、修改或自己打包 | 按下方“源码部署”操作 |

便携包是**纯程序包**，不含作者的数据库、自选、API 密钥、个人配置、新闻缓存、日志或模型权重。首次使用需要联网获取数据；AI 为可选功能，需要用户自行配置。

## 能做什么

| 使用场景 | 主要功能 |
| --- | --- |
| 工作台 | 信息总览、数据大屏、今日研判；查看指数、市场广度、涨跌停、热点与情绪证据 |
| 个股研究 | 按代码或名称查找股票，查看行情、K 线、事件、财务与公司研究 |
| 策略筛选 | 首次涨停、尾盘选股、量化分析、历史回测与规则证据 |
| 资讯与风控 | 新闻热点、风险提醒、历史复盘、监控中心 |
| 数据维护 | 数据来源配置、覆盖检查、一键数据修复、任务进度、备份和诊断 |
| 特色工具 | 大盘云图、易数智算发现专区，在桌面程序右侧展示网页 |

系统展示来源、时间、覆盖率与缺口。数据不完整或来源失效时，会显示部分可用、过期、缺失或不可用状态；不会用随机数或假行情填补。后台刷新期间可先展示带时间标记的缓存。

AI 用于解释已有证据，不替代行情、财报或确定性规则。Kronos 情景预测属于可选研究能力，未启用或模型不可用时不会生成替代曲线。第三方网页与行情接口的可用性取决于网络、服务规则和上游状态。

## 下载成品：Windows 便携版

### 环境

- Windows 10/11，64 位。其他系统未提供桌面成品。
- Microsoft Edge WebView2 Runtime；如果系统没有安装，请使用 [Microsoft 官方安装包](https://developer.microsoft.com/microsoft-edge/webview2/)。
- 可写的本地目录、可访问数据源的网络，以及足够的磁盘空间；完整历史数据会持续占用空间。

### 安装与启动

1. 下载上方便携包，并**完整解压**到可写目录，例如 `D:\Apps\Yishu`。
2. 进入 `XiaoQiBao-Portable`，双击 `xiaoqibao.exe`。
3. 保留同级的 `_internal` 和 `web`，不要只复制 EXE，也不要在压缩包内直接运行。
4. 首次启动先创建本地运行目录、初始化数据仓储并加载页面。市场数据会在后台准备，首次数据补齐不等于程序启动耗时。

仓库也保留了解压后的同一份成品：[release/XiaoQiBao-Portable](release/XiaoQiBao-Portable)。使用“Code → Download ZIP”下载完整仓库后，可以直接进入这个目录启动程序，无需编译。

### 第一次使用

1. 打开“数据设置”，查看来源状态；有通达信本地日线的用户可配置自己的安装目录。
2. 若出现数据完整性提示，可执行一键修复；也可在“本地运维”手动启动全面修复。保持程序运行，按阶段、数量、百分比和预计剩余时间观察任务。预计时间会随网络与数据量变化。
3. 打开“信息总览”，先确认交易日、更新时间和覆盖状态，再查看各项指标。“开盘啦”等事件中的股票名称会结合本地证券目录展示；目录仍缺失时会保留待补齐提示。
4. 在“个股观察”或“公司研究”输入股票代码或名称；在“首次涨停”“尾盘选股”“量化分析”查看规则与证据。
5. 如需 AI，在“数据设置”填写自己的兼容接口地址、模型和密钥，并测试连接。没有 AI 也可以使用行情与规则功能。
6. 如需提醒，在“监控中心”配置规则并测试站内、语音等通道；飞书 Webhook 需要用户自行配置。

修复会尝试可用来源并报告失败原因；它无法保证外部服务始终可用。出现失败时，先检查具体来源、网络和授权状态，再针对缺口重试。不要为了修复而删除原数据库。

### 数据保存与升级

程序会在 EXE 同级创建 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。这些目录保存个人配置和运行数据，不随公开程序包分发。

升级前完全退出旧程序并备份上述目录。推荐将新版解压到新目录，确认旧进程已退出，再迁移自己的持久目录。不要覆盖仍在运行的 EXE，不要同时用两个程序实例打开同一数据目录。数据库与日志可能包含个人信息，反馈问题前请脱敏。

公开便携版的文件哈希见 [SHA256SUMS.txt](release/XiaoQiBao-Portable/SHA256SUMS.txt)，依赖和许可清单位于同目录的 `THIRD_PARTY_LICENSES`。

## 源码部署

前端使用 React、TypeScript、Vite；后端使用 FastAPI；桌面容器使用 pywebview 与 WebView2；数据存储使用 SQLite、DuckDB 和 Parquet。桌面构建与主要验证环境为 Windows。浏览器开发模式与桌面网页容器能力不同，第三方网站可能禁止 iframe 内嵌。

### 准备工具

- Git
- Python 3.12，64 位（推荐使用此版本以匹配便携构建环境）
- Node.js 22.12+，pnpm 10+
- Windows PowerShell 或 PowerShell 7

### 下载、安装和启动

在 PowerShell 中执行：

```powershell
git clone https://github.com/zuitengxiaoqibao-code/Xiaoqibao-A-shares.git
cd Xiaoqibao-A-shares

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".\apps\api[dev]"
pnpm.cmd install --frozen-lockfile

powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

安装依赖需要联网。若没有 pnpm，可先运行 `npm.cmd install --global pnpm@10`。如果下载的是源码 ZIP，解压后从创建 `.venv` 开始执行即可。

启动后在浏览器访问 `http://127.0.0.1:5173`；API 为 `http://127.0.0.1:8000`，API 文档为 `http://127.0.0.1:8000/docs`。关闭开发脚本会清理其启动的 API 进程。默认开发数据保存在项目根目录 `.runtime`，与便携版数据分离。

若需要分别启动，打开两个 PowerShell 窗口，在项目根目录执行：

```powershell
# 窗口一：API
.\.venv\Scripts\python.exe -m uvicorn qibao_api.main:app --host 127.0.0.1 --port 8000

# 窗口二：前端
pnpm.cmd --dir apps/web dev --host 127.0.0.1
```

此项目的本地 API 没有面向公网部署设计的完整登录和访问控制；请保留回环地址，勿直接暴露到公网。

### 可选配置

环境变量需要在启动 API 前设置，也可以在程序的数据设置页面配置 AI：

```powershell
# 可选：隔离源码部署的数据目录
$env:QIBAO_DATA_DIR = "D:\YishuData"

# 可选：AI，三项需要一起设置
$env:QIBAO_AI_BASE_URL = "https://your-provider.example/v1"
$env:QIBAO_AI_API_KEY = "replace-with-your-own-key"
$env:QIBAO_AI_MODEL = "your-model"
```

不要把真实密钥写入源码、Issue、截图或公开程序包。程序不会自动加载根目录 `.env`；如使用环境变量，请在启动进程的同一个终端设置。AI 请求会发送相关研究上下文至你选择的服务商，请自行决定使用范围。

Kronos 默认关闭。需要此能力时，另行获取 [Kronos 源码和模型](https://github.com/shiyu-coder/Kronos)，按其要求安装依赖，并设置 `QIBAO_KRONOS_ENABLED=true`、`QIBAO_KRONOS_REPO_PATH`、`QIBAO_KRONOS_MODEL` 和 `QIBAO_KRONOS_TOKENIZER`；设备可通过 `QIBAO_KRONOS_DEVICE` 设置。公开包不包含模型权重。

### 构建自己的便携版

完成源码依赖安装后：

```powershell
# 同步依赖、执行测试、构建前端并生成 Windows EXE
powershell -ExecutionPolicy Bypass -File .\scripts\build-portable.ps1 -SkipPersistentData
```

正常输出位于 `dist\XiaoQiBao-Portable`。如果已有 EXE 正在运行，脚本会输出到暂存目录并登记待更新；以终端显示的路径为准。构建只生成本机程序，不会自动上传 GitHub。

如需生成和本仓库一致的公开纯程序快照与 ZIP，可在构建完成后运行：

```powershell
.\.venv\Scripts\python.exe scripts/prepare-public-release.py --source dist/XiaoQiBao-Portable
```

该脚本只复制发布清单内通过哈希检查的程序文件，不复制持久数据；目标 `release/XiaoQiBao-Portable` 必须不存在，避免覆盖现有文件。它会附带本项目许可、使用说明和依赖许可。

常用开发检查：

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q
pnpm.cmd --filter @qibao/web test
pnpm.cmd --filter @qibao/web build
powershell -ExecutionPolicy Bypass -File .\scripts\run-portable-smoke.ps1
git diff --check
```

## 数据来源与边界

项目按功能使用腾讯行情、通达信本地日线与在线接口、东方财富、百度、巨潮等来源，并接入 eltdx、mootdx、AxData 等适配能力。相同上游的多个适配器不代表多个独立证据来源。

数据源可能限流、改版、延迟、缺失或要求额外授权；行业、板块、新闻关联与财务字段也可能尚未核验。请以页面实际来源、交易日、覆盖率和缺失说明为准。历史回测不保证未来收益，情景预测不代表确定结果。

本仓库的软件许可**不授予任何交易所、数据商、新闻、第三方网站或模型的使用与再分发权限**。这些内容及第三方依赖遵循各自规则，详见 [第三方说明](THIRD_PARTY_NOTICES.md)。

## 常见问题

**一直停在启动界面怎么办？**

先确认已完整解压并安装 WebView2。若刚升级，请等待旧程序正常退出，确认没有无窗口残留的 `xiaoqibao.exe` 占用旧文件，再启动新版。查看 `logs/xiaoqibao.log` 中的启动阶段或更新错误；不要反复双击启动，也不要删除数据库。

**为什么首轮补齐较慢，或者修复失败？**

扫描本地文件、下载、解压、入库与最终校验所需时间不同；网络速度、数据量、磁盘和来源限制都会影响耗时。查看当前阶段、处理数量、预计时间和具体失败原因。其他实例占库时先正常退出该实例，数据源失效时稍后重试或配置其他可用来源。

**没有 AI 密钥能使用吗？**

可以。行情、规则筛选与数据维护不要求配置 AI；需要模型参与的解释会显示未配置或降级状态。在线数据仍需网络与来源可用。

**为什么股票显示“名称待补齐”或行业待核验？**

通常是证券目录或分类数据尚未完整。先在数据设置检查证券目录与来源健康，再执行相关补齐。程序会保留未知状态，不会编造名称或板块。

**能放到 Linux 服务器或做在线服务吗？**

本仓库提供的是 Windows 桌面成品；后端和前端可作为开发组件研究，但没有提供已验证的 Linux 桌面包、Docker 一键部署或公网服务方案。经营性在线服务还需要事先取得商用许可。

## 目录

```text
apps/api/               API、桌面入口、数据源、策略与研究服务
apps/web/               React 前端与测试
scripts/                开发、构建、验证与发布脚本
packaging/              图标、PyInstaller 配置、便携版说明
docs/                   公共架构与运维参考
release/                新版 Windows 便携程序、ZIP 与校验信息
LICENSE                 个人非商业许可
THIRD_PARTY_NOTICES.md   第三方软件及数据使用边界
```

本机工作记录、个人配置、数据库、日志、模型、虚拟环境及构建缓存不作为本次公开交付内容。

## 许可、商用与贡献

- **允许**个人以非商业目的下载、部署、使用、学习和修改；按许可保留声明后可非商业分享修改版。
- **禁止未经许可商用**，包括销售软件、收费部署、付费数据/信号服务、SaaS、商业产品集成，以及为经营活动提供服务。
- 商用请先通过 [GitHub Issue](https://github.com/zuitengxiaoqibao-code/Xiaoqibao-A-shares/issues/new) 联系仓库维护者，说明用途并取得相关权利人的书面许可；提交申请不代表已获授权。不要在公开 Issue 提交密钥、合同或个人敏感信息。
- 本项目的授权仅涵盖有权授权的项目内容；eltdx 等第三方依赖、行情数据与模型可能需要另行授权。

完整条款以 [LICENSE](LICENSE) 为准。提交问题或代码前请阅读 [贡献说明](CONTRIBUTING.md)；安全问题见 [SECURITY.md](SECURITY.md)。

本软件按现状提供，不保证数据准确性、持续可用性、盈利能力或特定用途适用性。使用者应独立核验原始行情、公告与财报，并自行承担投资决策及使用后果。
