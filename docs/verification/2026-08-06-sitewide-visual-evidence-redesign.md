# 全站视觉与证据持续优化验收记录

日期：2026-08-06

## 2026-08-07 量化刷新可观测性、索引优化与最终烟测

- 量化策略契约新增候选扫描和触发证据两层的采集时间、数据年龄、缓存复用标记；状态栏明确展示“刚刚采集/复用缓存”，不再把 5 秒策略刷新误解为每次都重新扫描全市场。
- 盘中快照仓库新增 `(symbol, observed_at, sequence)` 索引；已有发布数据库启动时自动创建，查询计划回归确认按股票索引读取。
- 便携烟测新增独立请求耗时：`home / overview / quant / professional`，用于区分窗口/API/业务数据瓶颈。
- 真实发布目录烟测：窗口 `96ms`，API `/health` `2050ms`，完整验证 `11370ms`；请求耗时 `home=101ms`、`overview=1105ms`、`quant=6318ms`、`professional=1776ms`；信息总览 `ready`，量化策略 `partial`（7 只候选、85.00% 覆盖），通达信专业 `unavailable`。
- 隔离目录烟测：窗口 `126ms`，API `/health` `2460ms`，完整验证 `4379ms`；量化在隔离数据不足时诚实返回 `unavailable`。
- 结论：窗口首帧和 API 就绪继续满足 3 秒目标；真实发布完整验证主要耗时集中在首次全市场日线候选扫描，后续 30 秒候选缓存和 5 秒触发证据缓存保留实时刷新与真实性边界。
- API 量化/路由/快照索引/打包回归通过；前端量化与全站回归在本轮字段变更后保持通过；生产构建和便携 EXE 构建通过。
- 最新便携 EXE SHA-256：`787C004202E1DCCDF2E98662E6B0A4ED19FA3557889D3CFEE4EFF751438AC315`。
- smoke 后确认无应用或通达信探测进程残留，`127.0.0.1:17709` 未监听；`config/data/news/cache/logs/models/exports/backups` 全部保留。

## 2026-08-07 通达信桥接根因与量化刷新预算增量

- 直接只读调用 `D:\new_tdx64\PYPlugins\TPythClient.dll`，使用官方 `tqcenter.py` 同样的 DLL 路径、连接脚本和 Python 3.12 版本号，返回 `ErrorId=11`；解码后的原因是“初始化错误：请确认是否打开通达信客户端”。
- 进程层检查显示 `TdxW.exe` 可以启动并响应，但进程模块列表没有 `TPythClient.dll`，本次 `T0001\tdxsys3.log` 只记录版本启动，没有“后台数据服务启动”记录；因此专业字段不可用属于通达信 TdxQuant/只读服务尚未初始化，不是本程序把 DBF 或普通行情误当成专业数据。
- 设置页与 API 的 JSON-RPC 状态改为使用实际配置端口；自定义 `http://127.0.0.1:19001/` 时显示 `19001 未监听`，不再固定显示 17709。
- 量化策略服务增加两级真实数据刷新预算：候选池日线扫描缓存 30 秒，触发证据缓存 5 秒；这不会生成新数据，只减少同一刷新窗口内重复扫描，且候选池和触发证据均保留原来源与时间戳。
- 新增后端 2 项缓存回归和设置端口回归；相关 API/前端聚焦测试通过，ruff 通过。
- 本轮回归：API `1139 passed, 1 skipped`（5 个警告均为依赖弃用提示）；前端 `72` 个测试文件、`473 passed`；Vite/TypeScript 生产构建通过。
- 便携 EXE 已重建，SHA-256：`01C9B70BE8EF3F98FB6B83C7DC5997AE9B76B00482033AAFE2A8D959ED2F918`。
- 隔离 smoke 首次受 Windows 冷盘静态资源请求超时影响，保留目录复测通过：窗口 `117ms`、API `2439ms`、完整验证 `4383ms`；真实发布目录 smoke 通过：窗口 `60ms`、API `2005ms`、完整验证 `11532ms`；真实发布量化 `partial`（7 只候选、85.00% 覆盖），专业字段保持 `unavailable`。
- smoke 后确认无应用或通达信残留进程，`127.0.0.1:17709` 未被本程序监听；便携持久目录均保留。

### 本轮仍保留的外部条件目标

- 通达信客户端完成登录并在客户端内启动 TdxQuant/只读服务后，再逐项实测 `Fn/GP/BK/SC/GO`；在此之前继续显示 `detected_only/unavailable`。
- 继续积累至少三次真正冷盘与三次热启动 EXE 证据，并拆分 Windows 安全扫描、PyInstaller 读取和业务接口查询耗时。

## 2026-08-07 区间统计真实日期选择与 EXE 交付增量

- 信息总览的“区间统计”已从通用复盘占位切换为真实区间工作区：支持起始日/结束日选择，默认使用最近交易日及其前 28 天窗口。
- 后端新增 `GET /api/v1/a-shares/market-overview/interval?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`；只读取本地通达信日线，要求实际起止交易日同时具备收盘价后才纳入逐股结果。
- 逐股公式固定为：区间收益 = 结束收盘 / 起始收盘 - 1；区间振幅 = 区间最高价 / 区间最低价 - 1；区间成交额 = 区间日线成交额之和 / 1e8。结果按区间收益降序，红色表示上涨、绿色表示下跌。
- 前端增加动态加载状态、失败原因、证据警告、有效样本、平均收益、上涨/下跌数量、最大振幅、收益分布、强弱榜和逐股表格；整行可打开个股观察，小屏自动单列/双列，不产生页面级横向溢出。
- 前端全量回归：72 个测试文件、467 项通过；API 全量回归：1126 项通过、1 项按环境跳过；Vite/TypeScript 生产构建通过。
- 便携 EXE 已按本轮源码重建并通过真实 smoke：窗口首帧 `124ms`、API `/health` 就绪 `2667ms`、完整验证 `3549ms`；信息总览 `ready`，量化策略在无真实样本时保持 `unavailable`。
- 最新 EXE SHA-256：`3D389D40040E29EC1027C545EDF2091CB09F0E2EAED203768554D385EF758EA4`。
- smoke 结束后确认 `xiaoqibao_process=False`、`bridge_17709=False`；`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 全部保留。

### 本轮仍保留的计划目标

- 本机通达信只读桥和专业数据包恢复后，逐字段实测 direct Python/RPC 返回并绑定到业务菜单；当前 `detected_only/unavailable` 是严格真实状态。
- 继续用冷盘/热启动双组 EXE 证据剖析 Windows 安全扫描和 PyInstaller 重型模块加载成本；窗口首帧已满足 3 秒目标，API 就绪时间仍受冷盘环境波动影响。

## 2026-08-07 启动并行化与候选选择竞态修复

- 启动路径将本地终端目录扫描与 SQLite schema 建立改为并行任务；两者均为启动期独立的只读/初始化工作，未改变行情、财务、新闻或专业字段的来源口径。
- 修复 `StockSelector` 的异步竞态：候选池尚未返回时用户点击波段候选，自动选择首个短线候选不会覆盖显式选择；测试同时覆盖了 URL 状态和重新渲染后的空候选池。
- API 全量回归：`1119 passed, 1 skipped`；前端全量回归：`71` 个测试文件、`454 passed`；Vite 生产构建通过；乱码扫描和 `git diff --check` 通过。
- 便携 EXE 已重建并连续三次 smoke：窗口首帧 `111/98/118ms`，API `/health` 就绪 `2806/2421/2346ms`，完整验证 `3619/3238/3191ms`；信息总览均为 `ready`，量化策略均按真实样本状态返回 `unavailable`。
- 最新便携 EXE SHA-256：`8E535EE69D29242C2C0354841BE2F0A7BF40412C321CCBE25EE4B408312A69C6`。
- 便携目录中的 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 均保留；测试结束无 `xiaoqibao.exe`、`TdxW.exe`、`TdxSP.exe` 或 `TdxNonSP.exe` 残留。
- 本机 `127.0.0.1:17709` 仍不可达，通达信进程未运行；专业数据继续严格显示 `detected_only/unavailable`，未把缓存文件或其他行情字段代理成专业财务/交易数据。

### 当前剩余目标

- 等通达信只读桥和专业数据包真实返回有效行后，逐字段建立 `Fn/GP/BK/SC/GO` 到业务菜单的映射并回归。
- 继续用冷盘与热启动双组实测审计 PyInstaller/Windows 安全扫描成本；不以单次热启动替代冷盘证据，也不为压缩体积牺牲数据功能。

### 打包实验边界

- 曾尝试排除 pandas 的可选模块以减少冷盘文件扫描；EXE smoke 证明 `exchange_calendars -> pandas.core -> pandas.plotting` 是实际运行依赖，排除后量化策略接口出现 `ModuleNotFoundError`。
- 已回退该排除实验，恢复完整 pandas 依赖；当前便携包恢复为 `1845` 个文件、`114.2MB` `_internal`，连续 smoke 重新通过。
- smoke 脚本同时增强了非 JSON 错误体的诊断，避免验证器自身的 `ConvertFrom-Json` 异常掩盖真实服务错误。

## 2026-08-07 专业回退诊断与交付重建增量

- 设置页新增官方 TdxQuant Python 回退状态：本机目录和配套 DLL 存在时显示 `detected_only`，明确说明仍需通达信进程返回可验证字段；未导入模块、未初始化连接，不会把文件发现误报为 ready。
- 专业 RPC 调用失败、错误包、空包或解析失败时会释放 RPC 客户端并尝试 direct Python 回退；无回退或回退也失败时统一为 `unavailable`。
- 专业适配器回归：`8 passed`；API 全量：`1118 passed, 1 skipped`；前端全量：`71` 个测试文件、`454 passed`；生产构建通过。
- 便携 EXE 已重建并完成 smoke：窗口首帧 `276ms`、API `/health` 就绪 `5717ms`、完整验证 `11520ms`；信息总览 `ready`，量化策略 `unavailable`。
- 最新 EXE SHA-256：`6D15348C31D0DE6F76368B2ABDEC6C21A6CAFA52059661CFB105322E215C3072`。
- 持久目录继续保留：`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。

## 2026-08-07 官方 TdxQuant Python 只读回退与最终验收增量

- `TdxQuantPythonSource` 现在按官方本地 Python 模块惰性加载，仅允许专业只读方法：`get_financial_data`、`get_financial_data_by_date`、`get_gpjy_value`、`get_gpjy_value_by_date`、`get_bkjy_value`、`get_bkjy_value_by_date`、`get_scjy_value`、`get_scjy_value_by_date`、`get_gp_one_data`。内部参数按官方 Python 接口使用 `field_list`，外部 JSON-RPC 契约仍严格使用实际可用的 `table_list`。
- 设置页现在单独展示官方 TdxQuant Python 回退的文件发现状态；`detected_only` 仅代表模块与 DLL 已发现，不代表通达信进程或专业字段已验证。
- 当 JSON-RPC 桥接可达但专业方法不支持、返回空包、错误包或解析失败时，适配器会关闭桥接并尝试 direct Python 回退；两条链路都失败才返回 `unavailable`。
- `TdxLocalProfessionalSource` 在 RPC 不可达时惰性调用 direct Python 回退；模块不存在、DLL 不可用、通达信进程未运行、空响应、异常响应或缺少验证字段均统一返回 `unavailable`，不会冒泡为 500，也不把专业缓存文件名当作字段证据。
- 能力探测继续要求 JSON-RPC 专业响应带明确 `ErrorId=0` 契约；未包装的列表响应不会被标记为 ready。direct Python 返回的 pandas DataFrame、字典列或按代码嵌套行仍由专用适配器解析。
- 应用生命周期已把自动发现的真实 TDX 安装目录注入 direct fallback；疑似 `mock/fixture/sample/demo/fake` 目录不会自动进入生产源。
- API 全量回归：`1116 passed, 1 skipped`；前端全量：`71` 个测试文件、`454 passed`；Vite/TypeScript 生产构建通过。
- 便携 EXE smoke 通过：窗口首帧 `338ms`、API `/health` 就绪 `5728ms`、完整验证 `11666ms`；信息总览为 `ready`，量化策略在无真实样本时保持 `unavailable`。
- 最新便携 EXE SHA-256：`DD7BFD29067E59972B470E6C6D848F0399B0489137D437EB8E2E6248C96E53BA`。
- 持久目录已保留：`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。本机 `127.0.0.1:17709` 当前仍不可达，因此尚未将专业字段绑定为已验证业务数据。

### 持续计划

- 等本机通达信只读桥和专业数据包真实可读后，逐项验证字段并绑定到财务、交易、板块和市场菜单；缺失时继续显示 `unavailable`。
- 继续测量 Windows 冷盘加载与安全扫描波动，优化必须以 EXE 冷盘/热启动两组数据共同验收。

## 2026-08-07 专业数据只读契约增量

- `TdxLocalProfessionalSource` 已接入官方 TdxQuant 专业接口定义：`get_financial_data`、`get_financial_data_by_date`、`get_gpjy_value`、`get_gpjy_value_by_date`、`get_bkjy_value`、`get_bkjy_value_by_date`、`get_scjy_value`、`get_scjy_value_by_date`、`get_gp_one_data`。
- 字段模式按接口严格限制为 `Fn`、`GP`、`BK`、`SC`、`GO` 前缀；请求参数统一发送 `table_list`，不再误用官方 HTTP 桥实际不接受的 `field_list`。缺失字段、空响应、错误响应和桥接不可达均返回 `unavailable`，不把专业缓存文件存在当作有效行。
- 新增只读接口：`/api/v1/tdx/local/professional`。它只返回经过结构校验的表格行和明确来源，不连接券商、不读取账户、不调用交易方法。
- 回归覆盖字段校验、嵌套行解析、`table_list` 参数和错误脱敏；API 全量：1114 passed、1 skipped；前端全量：71 个文件、454 项通过；生产构建通过。
- 便携 EXE 已重建并通过真实 smoke：窗口首帧 322ms、API `/health` 就绪 5746ms、完整验证 11577ms；信息总览 `ready`，量化策略 `unavailable`（无真实样本时保持诚实降级）。
- 最新 EXE SHA-256：`BDCF178116CD8D0D587DDD6214FCB24D67035B648DA1E29AFA3427EF8690023A`。
- 持久目录已保留：`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。
- 本机 `127.0.0.1:17709` 仍不可达，专业数据包目前只能显示 `detected_only/unavailable`；待只读桥恢复并返回有效行后，才继续接入真实财务/交易字段。

## 2026-08-07 持续目标增量（自动发现与专题证据口径）

- 自动发现本机数据目录时，目录名包含 `mock`、`fixture`、`sample`、`demo` 或 `fake` 的 ready 目录仍会展示为已发现，但标记为 `selection_eligible=false`，不会被自动选作生产数据源；手工明确指定目录仍尊重用户选择。本机当前自动 active 为 `D:\\new_tdx64\\vipdoc`，`D:\\new_tdx_mock` 被排除为疑似测试/示例目录。
- 专题仪表卡片新增证据口径标签：原始字段、确定性派生、观察性合成、部分证据、禁止代理。市场情绪采用 `a-share-sentiment-v2` 九因子加权（15/15/10/10/15/15/10/5/5），缺失因子按有效覆盖归一化；板块广度、板块综合强度、观察热度、高开/低开、竞价规则和日线覆盖均在卡片中给出明确计算口径。板块成交额仅表示活跃度，不等于资金净流入。
- 第二次重建便携版后 smoke 通过：窗口 131ms、API `/health` 2688ms、完整验证 3643ms；信息总览 `ready`，量化策略 `unavailable`（真实样本不足，不虚构）。
- 本轮全量 API 测试：1104 passed、1 skipped；前端测试：71 个文件、454 项通过；前端生产构建通过；`git diff --check` 通过，源码乱码扫描未发现异常匹配。
- 本轮 EXE SHA-256：`F31D6A22E5B162255E17C1A43112BA8C6A92DB7A1D8EF87B1C26663F7B429CD0`。
- 本轮新增本地专业缓存发现状态：当前 `D:\\new_tdx64` 的 `T0002\\hq_cache` 检测到 `base.dbf`、`shs.tnf`、`szs.tnf`、`sh.th2`、`sz.th2`、`gbbq` 六项文件，设置页显示“已发现，等待只读桥接读取”；由于 `127.0.0.1:17709` 当前不可达，未把这些文件当作已验证财务字段。
- 新增回归覆盖本地专业缓存的 `detected_only` 状态；API 全量测试更新为 1106 passed、1 skipped，前端仍为 71 个测试文件、454 项通过。
- 移除 PyInstaller 对整个 `qibao_api`/`qibao_desktop` 包的递归隐藏导入，改为显式 `qibao_api.main` 动态根；构建文件数与 `_internal` 体积未明显变化，说明当前依赖图本身仍需要这些业务模块，未强行排除以免 EXE 缺功能。
- 重建后的 EXE smoke：冷盘一次窗口 299ms、API 5678ms、完整验证 11438ms；热启动连续三次窗口 113/114/116ms、API 2365/2441/2444ms、完整验证 3221/3263/3237ms，信息总览均为 `ready`，量化策略均为 `unavailable`。
- 最新 EXE SHA-256：`A09C79DC1D0165F134B16F372DAF315AF91876A3F3DA3E0A46BF08C0A55ABFD6`。

## 2026-08-06 指标证据边界增量

- 信息总览专题的情绪分、市场风格、风险分和热度分在分数缺失或规则未匹配时统一进入 `unavailable`，不再把 `--` 或“待确认”标成已就绪。
- 复盘质量与交易日没有复盘快照时显示不可用；上涨/下跌家数要求 `valid_count > 0`；两市成交要求存在明确成交额；没有题材标签的股票不再被选为“题材叠加最多”。
- 龙虎榜只有至少一条真实上榜记录时才算证据可用，空列表（包括无警告的空列表）不再生成席位统计。
- 新增 5 个边界回归场景，前端本轮全量测试为 71 个文件、453 项通过；API 1099 项通过、1 项按环境跳过；生产构建通过；乱码扫描和 `git diff --check` 通过。
- 本批源码改动后已重建便携 EXE 并完成两次实际 smoke。首次冷盘窗口 302ms、API 5588ms、完整验证 11344ms；紧接着复测窗口 118ms、API 2456ms、完整验证 3304ms。复测阶段日志显示业务 `lifespan-ready` 为 578ms，因此第一次较慢主要来自 Windows 冷盘加载/安全扫描波动，不是本批业务初始化回退。两次信息总览均为 `ready`，量化策略均为 `unavailable`（真实样本不足，不虚构）。
- 本批 EXE SHA-256：`ADDE66B11C2DBA238FC693C02F526D7D6C9B8AA31EF6FECC1CF8F373EB494610`。
- 通达信本地 overview 后台刷新日志已限频：首次失败、错误类型变化和每 20 次失败记录一次完整诊断，恢复时记录一次；新增回归测试覆盖 21 次连续失败只产生 2 条警告。
- 日志限频改动后重新构建并 smoke：窗口 133ms、API 2809ms、完整验证 3773ms；信息总览 `ready`，量化策略 `unavailable`。最终 EXE SHA-256：`3BE9E00822D43D2C7BF451FAFDD79BD8D957202A5F14C3C209ACD56C9EE41C55`。

## 本轮完成

### 2026-08-07 专题语义第二轮审计

- 开盘啦的市场检查单已改为真实缺口派生：开盘样本、高开 >= 2%、低开 <= -2%、高开延续、高开回落和开盘题材；不再重复市场风格仪表。
- 人气榜的“人气构成分布”改为 0-20、20-40、40-60、60-80、80-100 分带；板块赛道的“赛道强弱分层”改为板块强度分带；均只覆盖真实接口代表样本。
- 热点解读的原始资讯与完整证据链仅接收已核验、具备题材和 A 股代码关联的新闻；待核验或未关联传闻不再混入解释链。
- AI+选股与问财选股分别显示行情字段、题材可追溯、风险排除、AI 解释边界和“本地规则/不调用问财官方接口”等专属闸门。
- 百日新高、昨涨停和区间统计当前后端尚未返回逐股历史结果时，页面明确显示接口缺口与证据边界，不再显示“严格筛选后没有记录”的通用空状态。
- 行情主源不可用时，市场风格仪表所有依赖市场快照的卡片显示“未接入”，不再显示上涨/下跌、涨停/跌停等 0 值。
- 新增 6 项专题行为回归；本轮前端全量测试为 71 个文件、462 项通过，API 全量为 1119 项通过、1 项按环境跳过，Vite 生产构建通过。
- 概念叠加的风险区改为多题材关联股票的拥挤样本，不再复用炸板/跌停风险清单；新高趋势缺少逐股结果时保持明确不可用。
- 最新便携 EXE 已按本轮源码重建并完成 smoke：窗口 112ms 可见、API 2639ms 就绪、完整验证 3645ms；信息总览 `ready`，量化策略 `unavailable`。
- 最新 EXE SHA-256：`5C90D9BEBFF2EFBB11D7549EAE21C0B67781C8774949133E0ED7F9C2DCF2E1E8`。

- 继续收紧复盘与龙虎榜的缺失值边界：席位买卖额、净额、连板高度、量能倍数、成交额和涨跌幅为空或非法时显示 `--` / 不可用，不再生成 `+0.00亿`、`0板`、`NaN%` 或默认仪表值。
- 市场风格评分、短线策略评分、公司研究维度条、资本结构圆环和量化回测统计新增 `data-state="unavailable"` 视觉状态；空条使用中性样式，不再暗示真实 0 分。
- 竞价缺口图只绘制有可验证缺口的股票，龙虎榜方向分组只使用有明确净额的记录。

- 修复专题工作区派生数据的真实性边界：缺失行情、成交额、价格区间和板块字段保持 `null`，不再被 `numberValue` 转成 0；缺少必要输入的竞价筛选、成交额排行、关注度、板块强度和四象限不生成结果。
- 复盘摘要的平均涨幅、最大量能、历史覆盖在无有效样本时显示 `--`，不再用 0 值或默认仪表填充。
- 新增 `workspaceSelectors.test.ts`，覆盖缺失值、筛选排除和板块强度不可用边界。

- 全局正文基线提升为 14px，普通辅助文字提升为 13px；保留代码、时间戳等紧凑信息层级。
- 信息总览专题工作区按 50 个菜单独立定义，已有菜单语义和组合回归测试。
- 专题页根据 `ready / partial / stale / unavailable` 显示真实工作区状态。
- 无行情样本时覆盖率显示 `--`，不再将缺失数据展示为 `0.0%`。
- 不可用行情不再显示“实时证据已连接”。
- 通达信本地只读能力探测已接入数据设置页，覆盖证券目录、实时行情、板块目录、扩展行情与估值、基础财务与行业、新股与新债日历、可转债条款、通达信公式计算；空响应、错误响应和接口异常不会被标记为可用，也不会回显异常原文。
- 新增通达信新股/新债日历只读接口 `/api/v1/tdx/local/ipo-calendar`：仅接受明确代码、名称、类型和申购日期；上市日/中签日缺失保持为空。
- 新增通达信公式批量只读接口 `/api/v1/tdx/local/formula`，仅允许 `formula_process_mul_*` 方法；量化分析仪表盘新增“通达信公式证据”面板，缺失字段不转成 0。
- 首页实时刷新失败但存在当日缓存时，启动层提供“继续使用缓存”，不再让错误遮罩持续阻塞已展示的缓存数据。
- 专题仪表在行情主源不可用时保持“未接入”，不把空样本显示为涨停、板块、竞价或风险指标的 0；历史覆盖为零时不显示虚假的 0.0%。
- 个股观察增加 30 秒可见页面刷新；页面恢复可见时立即刷新，刷新期间继续展示上一次完整快照，失败时保留缓存并标记陈旧。
- 公司研究增加 5 分钟活动标的刷新；只刷新当前活动公司，比较池其余股票不被无意义地重复请求，页面隐藏时暂停，恢复可见时立即更新。
- 量化 TICK 图表增加 inside/slider 双层缩放，成交量柱按已验证涨跌方向红涨绿跌，长时间盘中归档可以在同一面板内定位观察窗口。
- 日缓存日期改为显式使用 `Asia/Shanghai`，补充交易日午夜边界回归，避免运行环境时区不同导致跨日缓存误读。
- 通达信实时快照解析新增严格的 `MarketCapYi` 只读字段链路；不识别单位不明的 `MarketValue`，市值缺失时继续显示不可用。
- 数据设置页对已启用但暂不可用的通达信桥增加自动重探测：页面可见时每 60 秒检测一次，隐藏时暂停，恢复可见立即检测；手动检测和保存期间不会并发触发自动检测。
- 启动性能修复：可转债远程全量同步改为可取消后台任务，`lifespan-ready` 不再等待网络；烟测健康探测改为 1 秒轮询，避免测量超时偏差。
- 交易日历依赖改为首次查询懒加载：API 模块导入时不再立即构造 `exchange_calendars` 的上交所日历；首次交易日判断仍使用官方日历并保留原有节假日结果。
- Edge TTS 依赖改为首次真正请求语音时懒加载；仅导入语音服务不会加载 `edge_tts`，减少桌面 API 冷启动导入成本，同时保留原有播报行为。
- 桌面 API 启动就绪改为等待 Uvicorn `started` 状态；该状态发生在 lifespan 完成、预绑定 loopback socket 已进入服务阶段之后，不再重复发起 HTTP `/health` 自探测。
- 便携运行时的本地通达信 fallback 全市场扫描增加 2 秒启动缓冲；当日缓存优先展示，随后再启动真实全市场刷新，避免首屏阶段与 5,000 余只股票扫描争用资源。5 秒候选经烟测反向验证后未采用，恢复为 2 秒。

## 后续启动性能增量

- 桌面 GUI 路径现在先准备便携运行目录、迁移旧数据并启动 API 线程，再创建 WebView；窗口显示与 Python 导入/lifespan 初始化并行，服务器仍在窗口失败或退出时统一释放。
- `noarchive=True` 冷启动实验已回退：独立 `.pyc` 文件把便携目录从 1,845 个文件增加到 4,558 个，热启动改善不稳定，首次冷盘 API 约 10.76 秒；最终保留 `noarchive=False`，减少冷盘扫描文件数量。
- DuckDB、mootdx、pandas、numpy 不再从 `qibao_api.main` 顶层导入；BarRepository 首次真实日线操作时初始化 DuckDB，备份与通达信客户端提供兼容的懒加载入口。便携版历史符号校准改为 15 秒后可取消的后台任务，避免冷库导入抢占首个健康检查。
- smoke 脚本在 HTTP `/health` 前先等待 `desktop startup stage=lifespan-ready` 日志，避免 Windows 预绑定 loopback socket 在 Python 导入期间接收超时连接后触发 `WinError 64`。

## 验证结果

- 前端测试：71 个测试文件，453 项通过。
- API 测试：1100 项通过，1 项按环境跳过。
- 前端生产构建：通过。
- 便携 EXE 构建：通过（保留 `config/data/news/cache/logs/models/exports/backups`）。
- EXE 烟测：通过。
  - 本轮串行三次窗口显示：102ms、118ms、111ms
  - 本轮串行三次 API `/health` 就绪：2664ms、2387ms、2414ms
  - 本轮串行三次完整验证：3371ms、3201ms、3212ms
  - 信息总览：`ready`
  - 量化策略：`unavailable`（真实样本不足，保持诚实降级）
- EXE SHA-256：`3BE9E00822D43D2C7BF451FAFDD79BD8D957202A5F14C3C209ACD56C9EE41C55`

## 交付文件

- [一树电子商务-A股观测台 EXE](../../dist/XiaoQiBao-Portable/xiaoqibao.exe)

便携目录中的 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 已保留。

## 2026-08-07 真实发布数据烟测与发布脚本增量

- 新增 `scripts/run-portable-smoke.ps1 -UseReleaseData`：直接使用 `dist/XiaoQiBao-Portable` 的真实持久目录，不复制或清理发布数据；默认 smoke 模式仍使用隔离临时目录。
- smoke 新增 `/api/v1/tdx/local/professional` 只读探针，输出通达信专业字段的真实状态与原因，防止发布验收只验证首页而遗漏专业数据链路。
- 默认隔离 smoke：窗口首帧 `124ms`、API `/health` 就绪 `2620ms`、完整验证 `3500ms`；信息总览 `ready`；量化策略 `unavailable`；通达信专业字段 `unavailable`，原因是本机没有可用的专业数据响应。
- 真实发布数据 smoke：窗口首帧 `61ms`、API `/health` 就绪 `2018ms`、完整验证 `9430ms`；信息总览 `ready`；量化策略 `partial`，真实候选 `7` 只、市场风格覆盖 `85.00%`；通达信专业字段 `unavailable`（真实桥接/专业调用仍不可用）。
- 本轮 API 全量 `1130 passed, 1 skipped`；前端全量 `72` 个测试文件、`469 passed`；生产构建通过。
- 便携 EXE 已重建，SHA-256：`2AB32C12962D25FE9839FFA8169C7D12AACC230F0207BB3E6DA3660FC0B3425A`。
- smoke 结束后确认桌面进程已释放、`127.0.0.1:17709` 未被本程序占用；`config/data/news/cache/logs/models/exports/backups` 均保留。

## 2026-08-07 首屏 ECharts 按需加载增量

- `QuantChart` 改为运行时按需加载 ECharts；容器先显示 `图表引擎载入中` 的动态状态，成功后切换 `ready`，异常时显示 `图表引擎暂不可用`。
- Vite 入口从单块约 `1.52MB` 拆为约 `483KB` 首屏块和约 `1.04MB` ECharts 块；量化、分时、事件 K 线、回测和公司研究继续共用同一图表组件。
- 前端全量回归：72 个测试文件、`469 passed`；生产构建通过。
- EXE smoke：窗口 `115ms`、API `/health` `2676ms`、完整验证 `3529ms`；真实发布数据 smoke 为窗口 `60ms`、API `/health` `2002ms`、完整验证 `9545ms`；两种模式均未出现启动回归，真实发布数据仍为信息总览 `ready`、量化策略 `partial`（7 只候选、85.00% 覆盖）。

### 评估结论

- 保留 ECharts 按需加载：它降低首屏脚本阻塞并提供明确加载状态，但没有显著改变 Python API 冷启动；后端冷盘波动继续单独追踪。

## 未完成目标

本轮新增并验证：`get_more_info`/`get_stock_info` 可选接入个股基本面契约，明确提供 PE/PB/总市值/行业等字段时才进入诊断估值；`get_kzz_info` 进入可转债条款诊断的只读优先链，条款字段不完整时回退公开条款源。桥接不可达、空响应或字段不足时保留真实不可用状态。其余 TdxQuant 新股/新债、公式批量业务字段、全站逐菜单字段审计和长期实时数据覆盖仍在持续计划中；接口不可用或专业数据包缺失时，软件继续显示明确的不可用原因，不生成模拟值。

本增量验证：Edge TTS 懒加载、桌面 API 就绪路径、便携 fallback 启动缓冲、复盘/龙虎榜金额与连板高度、市场风格/短线策略/公司研究/量化回测的不可用视觉状态、个股观察与公司研究后台刷新、量化 TICK 缩放与红涨绿跌成交量、上海时区跨日缓存、市值单位边界、通达信桥自动重探测、远程转债同步不阻塞 lifespan、交易日历首次查询懒加载、API 预启动并行、重型数据依赖冷导入和 smoke 早期连接防护均有回归测试；本轮前端 449 项、API 1099 项通过（1 项按环境跳过），生产构建和便携 EXE 连续串行烟测通过。当前仍保留的长期计划是继续降低首次冷盘加载和剩余 PyInstaller/Windows 扫描开销，并在本机专业数据包实际可用后扩展真实字段和逐菜单数据源切换回归；任何接口不足继续显示不可用而不填充模拟值。

## 2026-08-07 日线回填逐股结果增量

- 后端市场复盘公式升级为 `a-share-market-review-v2`，新增真实日线派生结果：`new_high_100`（当前收盘不低于此前 100 个交易日最高收盘）和 `previous_limit_up`（前一交易日严格收盘涨停，当前交易日作为次日反馈）。每条记录保留交易日、收盘、涨跌、成交额、前一日收盘/涨跌、参考高点和窗口长度；没有完整日线窗口时不入选。
- 百日新高菜单的“已验证新高清单”现在展示逐股代码/名称、当前收盘、当前涨跌、100 日参考高点、突破幅度、成交额与窗口；整行支持打开个股观察。
- 昨涨停菜单的“可验证反馈明细”现在展示逐股代码/名称、当前收盘、当前涨跌、前一日收盘、前一日涨跌、成交额与反馈窗口；“今日反馈分组”按回撤 <= -3%、回撤 -3%~0、横盘 0%~3%、反弹 >= 3% 分组，全部来自前一日收盘与当前收盘的确定性计算。
- 新高趋势的“距离高点分布”按突破 0%~3%、3%~8%、>= 8% 展示；历史样本缺失时继续保留证据审计提示，不用当前代表快照冒充历史结果。
- 前端全量回归：71 个测试文件、463 项通过；API 全量回归：1121 项通过、1 项按环境跳过；Vite/TypeScript 生产构建通过；UTF-8 与 `git diff --check` 通过。
- 便携 EXE 已按本轮源代码重建并完成真实 smoke：窗口首帧 `310ms`、API `/health` 就绪 `5690ms`、完整验证 `11384ms`；信息总览 `ready`，量化策略在当前真实样本不足时保持 `unavailable`。
- 最新 EXE SHA-256：`A3EFBEBB5CF9ED8D17D66526C05A2FCE0D5D5885DFA8F88B29C8A1FF1282D87`。
- smoke 结束后已确认 `xiaoqibao` 进程释放，`127.0.0.1:17709` 未被本程序占用；便携持久目录 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 均保留。

### 当前仍未完成的长期目标

- 本机通达信只读桥与专业数据包恢复后，继续逐字段实测并绑定到对应菜单；当前 `detected_only/unavailable` 继续作为真实状态。
- 区间统计需要明确起止日期选择和后端历史窗口计算接口，当前不生成无口径的区间收益。
- 继续使用冷盘/热启动双组 EXE 证据剖析 Windows 安全扫描和 PyInstaller 重型模块加载成本；窗口首帧已快速出现，但冷盘 API 就绪仍受环境波动影响。

## 2026-08-07 设置页运行状态诊断与交付验收

- 设置页新增真实运行状态分栏：分别显示“通达信客户端”进程（`TdxW.exe`/`tdx.exe`）和 JSON-RPC 桥监听状态；客户端进程存在不再被当作 `127.0.0.1:17709` 桥接可用。
- 后端新增只读进程发现契约 `running_tdx_process_paths()`，并为 `TdxRpcStatus` 增加客户端状态、可执行文件路径和解释性详情；进程、桥接、专业缓存、专业字段仍保持独立证据层级。
- 回归覆盖客户端运行/未运行与桥接不可用的组合；API 全量 `1128 passed, 1 skipped`，前端全量 `72` 个测试文件、`468 passed`；生产构建通过；`git diff --check` 和 UTF-8 乱码扫描通过。
- 便携 EXE 已重建并完成真实 smoke：首轮窗口首帧 `120ms`、API `/health` 就绪 `2660ms`、完整验证 `3485ms`；随后连续三次为窗口 `112/111/111ms`、API `2448/2432/2431ms`、完整验证 `3312/3238/3246ms`。信息总览均为 `ready`，量化策略均为 `unavailable`（真实样本不足，不虚构）。
- 最新 EXE SHA-256：`E8516463D82C1DBD8639175588080D1A0AAECE0C402E8BD5C4F7A7E6E3018A6C`。
- smoke 后已释放桌面进程，`127.0.0.1:17709` 未被本程序占用；便携目录 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 均保留。

### 本轮仍未完成的长期目标

- 本机当前仍未检测到通达信客户端进程，`127.0.0.1:17709` 未监听；专业缓存文件只表示 `detected_only`，必须等待真实只读桥返回有效行后再绑定专业财务/交易字段。
- 继续用冷盘/热启动两组 EXE 数据剖析 Windows 安全扫描与 PyInstaller 冷磁盘读取成本；保持功能完整、缓存优先和真实数据边界，不用一次热启动结果替代冷盘证据。

## 2026-08-07 冷导入与便携交付复验

- API 全量 pytest：`1128 passed, 1 skipped`，5 个 exchange-calendars 弃用警告，不影响结果。
- 前端全量测试：72 个测试文件、468 项通过；Vite/TypeScript 生产构建通过（2238 modules transformed）。
- `qibao_api.main` 冷导入回归：未加载 `duckdb/pandas/numpy/mootdx/sqlalchemy`；累计导入时间约从 817ms 降至 626ms。
- 便携 EXE 已重建，持久目录 `config/data/news/cache/logs/models/exports/backups` 均保留；EXE SHA-256：`F6E29E181F01E5D385975F26CC0313C53D20C7154C2610DDE6E156A9A2097AD4`。
- 连续三次真实 smoke：窗口首帧 `114/117/110ms`，API `/health` 就绪 `2680/2476/2442ms`，完整验证 `3537/3278/3241ms`；三次信息总览均 `ready`，量化策略均 `unavailable`（当前真实样本不足，保持诚实降级）。
- smoke 结束后已确认无 `xiaoqibao/qibao_desktop` 残留进程，`127.0.0.1:17709` 未被本程序占用。
- 官方 TdxQuant Python 适配器新增按安装路径的模块缓存；专项与路由回归 `13 passed`，重复读取只调用一次模块加载器，仍保留每次查询的 `tq.close()`。
- 本轮改动后便携 EXE 连续三次 smoke：冷盘一次窗口 `308ms`、API `5520ms`、完整验证 `11302ms`；随后热启动窗口 `108/115ms`、API `2452/2372ms`、完整验证 `3295/3195ms`；三次信息总览均 `ready`，量化策略均 `unavailable`。
- 本轮 EXE SHA-256：`4EF707390AD5B6C8DAB658764AA8C2299838F489BE6BEB3206BA4BA71C050ACF`。

### 本轮仍未完成的长期目标

- 本机通达信客户端/只读桥恢复后，逐字段实测 `Fn/GP/BK/SC/GO` 并绑定到对应菜单；当前专业缓存仍只能标记 `detected_only/unavailable`。
- 继续用冷盘与热启动两组 EXE 证据剖析 Windows 安全扫描和 PyInstaller 内读取成本；不能用热启动结果替代冷盘结论。
- 在真实专业字段可用后，继续做财务、交易、板块、市场专题的逐菜单数据源切换回归，并保持缺失数据显式标注。

## 2026-08-07 首屏资源拆分复验

- Dashboard 的非首屏工作区改为 `React.lazy + Suspense`，新增“正在加载工作区”状态，避免切换到重型页面时出现空白等待。
- Vite 构建产生独立资源：量化分析约 `39.6KB`、公司研究约 `27.8KB`、今日研判约 `26.9KB`、设置约 `18.4KB`、可转债/首次涨停/新闻/复盘均独立成块；首屏入口从约 `1.69MB` 降至约 `1.52MB`。
- 前端全量回归：72 个测试文件、`469 passed`；构建通过。入口仍有大于 500KB 的警告，主要来自首屏行情与图表依赖，后续继续按首屏实际使用链路拆分。
- 便携 EXE 已重建并连续三次 smoke：冷盘窗口 `320ms`、API `5596ms`、完整验证 `11377ms`；热启动窗口 `104/126ms`、API `2325/2433ms`、完整验证 `3237/3260ms`；信息总览均 `ready`，量化策略均 `unavailable`。
- 本轮 EXE SHA-256：`6ED5422B694881DD825211A2A8FEB7B7015341E53B36FEC60C3F3A105C9723DB`；持久目录保留，smoke 后应用进程与 `17709` 占用均为 0。

### 本轮仍未完成的长期目标

- 继续拆分首屏行情与 ECharts 依赖，必须以 EXE smoke 证据确认，不用浏览器构建体积单独推断启动收益。
- 通达信只读桥恢复后逐字段验证 `Fn/GP/BK/SC/GO`，再绑定到对应菜单。
- 继续使用真实发布数据 smoke 观察量化 `partial` 的字段覆盖变化；当真实样本下降时保持不可用/部分可用，不生成模拟推荐。
- 继续剖析冷盘 API 就绪时间的 Windows 安全扫描波动；窗口首帧已满足 3 秒目标，但冷盘完整验证仍可能高于热启动。

## 2026-08-07 专业探针修正与真实发布烟测

- 修复 `scripts/run-portable-smoke.ps1` 的专业字段探针：原先的 `table_list=Fn` 不符合专业字段契约，现改为 `table_list=Fn193`，并新增发布 smoke 回归断言防止退回非法前缀。
- `/api/v1/tdx/local/professional` 对已知不可用原因返回安全且可行动的说明：官方 Python 专业接口初始化/调用失败、模块或 DLL 不可加载、桥不可达、空响应和缺少验证字段分别区分；未知错误统一降级为不含内部细节的通用说明。
- TDD 证据：先新增 `Fn193` 断言并确认测试失败，再修复脚本；随后新增 Python 初始化失败原因测试，确认失败后实现安全映射；相关回归 `22 passed`。
- API 全量回归：`1131 passed, 1 skipped`，保留 5 个环境相关弃用警告。
- 前端全量回归：72 个测试文件、`469 passed`；Vite/TypeScript 生产构建通过。
- 便携 EXE 已重建，SHA-256：`0886D0EED76769B2E31EB39BF52FD63251308F5A4529951350275244300B210D`。
- 隔离目录 smoke：窗口 `113ms`，API `/health` `2645ms`，完整验证 `4568ms`；信息总览 `ready`，量化策略 `unavailable`，通达信专业 `unavailable`，原因为官方 Python 专业接口初始化或调用失败。
- 真实发布目录 smoke：窗口 `65ms`，API `/health` `2032ms`，完整验证 `10753ms`；信息总览 `ready`，量化策略 `partial`（真实候选 7 只、市场风格覆盖 85.00%），通达信专业 `unavailable`，同样未生成模拟值。
- smoke 后确认无 `xiaoqibao/qibao_desktop/TdxW/TdxSP/TdxNonSP` 残留进程，`127.0.0.1:17709` 未监听；发布目录持久数据未清理。

### 本轮未完成目标

- 通达信只读桥恢复后，逐字段验证 `Fn/GP/BK/SC/GO` 并绑定业务菜单。
- 继续进行冷盘/热启动三次以上的 EXE 性能对照，解释 Windows 安全扫描与 PyInstaller 冷磁盘波动。
- 专业字段恢复后逐菜单执行来源切换和数据状态回归。

## 2026-08-07 三次连续 EXE 启动基线

- 连续三次隔离 smoke 均通过：窗口首帧分别为 `134/110/110ms`，API `/health` 就绪分别为 `2355/2432/2469ms`，完整验证分别为 `4196/4208/4219ms`。
- 三次结果均为信息总览 `ready`、量化策略 `unavailable`、通达信专业 `unavailable`；未因启动优化生成任何模拟行情或候选。
- 每次 smoke 后均释放应用进程，未占用 `127.0.0.1:17709`；该基线用于后续冷盘与热启动对照，不将热启动数据冒充冷盘性能。

## 2026-08-07 预交易时段情绪刷新日志修正

- 将 `MarketSentimentWrongPhase` 从通用异常日志中分离；交易时段外属于确定性跳过，不再附带 traceback，真实异常仍保留堆栈。
- 新 EXE smoke：隔离目录窗口 `112ms`、API `/health` `2684ms`、完整验证 `4514ms`；真实发布目录窗口 `65ms`、API `/health` `2074ms`、完整验证 `10677ms`。
- 新日志已出现 `initial market sentiment refresh skipped outside session`，没有新增预交易 traceback；信息总览 `ready`，真实发布量化 `partial`（7 只候选、85.00% 覆盖），通达信专业保持 `unavailable`。
- 最新 EXE SHA-256：`54D4F206EFC2E45951E8F8D028D48E565B48FC88766567F446F29929112A7FE0`。

## 2026-08-07 盘前快照语义、缓存连续性与量化状态一致性

- 信息总览将“字段完整度”和“时间新鲜度”拆开：`quality` 继续表示字段覆盖，新增 `phase` 和 `freshness` 表示盘前、盘中、收盘后、休市以及实时、上一交易日收盘、当日最终、陈旧、不可用状态。
- 盘前读取上一交易日完整快照时，首页显示“已加载上一交易日快照 · 等待开盘”，专题工作区显示“上一交易日收盘快照 · 等待开盘”；不再把完整缓存误称为“实时证据已连接”。
- 当日收盘后显示“已加载收盘数据 · 等待下一交易日”；陈旧快照显示等待最新数据。加载过程统一使用“正在更新最新数据”，避免盘前承诺不存在的实时行情。
- 首页启动进度把“快照已完整校验”和“盘中实时”分成两个状态：上一交易日完整收盘快照仍能完成 100% 数据准备，但不会显示实时监控。
- 浏览器缓存规则改为：同日快照始终可用；开盘前允许最近 1 至 3 个自然日内的上一交易日收盘快照，以覆盖普通隔夜和周末；09:25 后严格拒绝跨日缓存。旧版本缓存会在读取时补上 `premarket/previous_close` 元数据。
- 量化策略仪表继承信息总览的新鲜度：`previous_close/final` 映射为 `postclose`，`stale` 保持 `stale`，避免首页与量化页面对同一份数据给出矛盾状态。
- TDD 回归覆盖盘前上一收盘、盘中实时、收盘最终、量化上一收盘语义、专题工作区状态和跨日缓存升级。
- API 全量回归：`1136 passed, 1 skipped`；前端全量回归：72 个测试文件、`472 passed`；Vite/TypeScript 生产构建通过。
- 隔离启动连续三次：窗口 `118/112/110ms`，API `/health` `2421/2328/2336ms`，完整验证 `4244/4208/4185ms`；信息总览均为 `ready`，量化策略因隔离环境缺少真实样本保持 `unavailable`。
- 真实发布目录连续三次：窗口 `57/60/54ms`，API `/health` `1980/1958/1993ms`，完整验证 `11373/11251/11345ms`；信息总览均为 `ready`，量化策略均为 `partial`，真实候选 7 只、市场风格覆盖 85.00%。
- 最新 EXE SHA-256：`F440A924F547225CEF7FD8D93A1F5F714AEA349B6BA2430F6579C4B7CCCFFDE0`。
- smoke 后确认无 `xiaoqibao/qibao_desktop/TdxW/TdxSP/TdxNonSP` 残留进程，`127.0.0.1:17709` 未监听；`config/data/news/cache/logs/models/exports/backups` 全部保留。

### 持续计划与未完成目标

- [ ] 通达信客户端完成专业插件初始化并恢复 `127.0.0.1:17709` 后，逐项实测 `Fn/GP/BK/SC/GO` 请求、响应形状、字段单位、来源和时间戳。
- [ ] 只将实测通过的专业字段绑定到财务、个股交易、板块、市场和量化专题；空字段、错误包和单位不明确继续保持 `unavailable`。
- [ ] 真实专业字段恢复后，逐菜单回归缓存、实时、`partial`、`stale`、`unavailable` 的来源切换，确保状态不会互相覆盖。
- [ ] 继续记录真正冷盘（系统缓存未预热）与热启动差异，重点分析 Windows 安全扫描和 PyInstaller 冷磁盘读取；当前窗口首帧和 API 就绪已稳定满足 3 秒目标，真实发布目录的完整业务验证约 11 秒主要包含大体量本地数据查询，不阻塞窗口先展示缓存。
## 2026-08-07 量化候选后台预热复验

- API 全量：`1143 passed, 1 skipped`；前端全量：`72` 个测试文件、`473 passed`；生产构建通过。
- 量化服务回归：首次请求在后台扫描未完成时返回 `candidate_scan_state=pending`，候选为空且 `missing_data` 含 `candidate_scan_pending`；任务完成后下一次请求返回真实候选。
- 隔离 EXE smoke（三次）：窗口 `121/112/118ms`，API `2440/2421/2415ms`，完整验证 `4556/4477/4443ms`；信息总览 `ready`，量化无样本时 `unavailable`。
- 真实发布 EXE smoke（三次）：窗口 `325/91/62ms`，API `5590/1971/1992ms`，完整验证 `19117/11205/11013ms`；信息总览 `ready`，量化最终 `partial`，真实候选 `7` 只、市场风格覆盖 `85.00%`。
- 专业探针仍真实返回 `unavailable`，原因是通达信专业 Python 接口尚未完成客户端/插件初始化；未使用普通行情或缓存文件名替代专业字段。
- smoke 结束后确认无桌面或探测残留进程，`127.0.0.1:17709` 未监听，便携持久目录全部保留。
- EXE SHA-256：`A7391C2B83912EDB2E0519BD3FBC61178A070719E98017C770576F02085EB08A`。

## 2026-08-07 最终构建与安全失败边界

- 后台扫描异常不会向前端透传原始异常文本；固定文案回归通过，API 全量最终为 `1144 passed, 1 skipped`。
- 最终真实发布 smoke：窗口 `63ms`、API `2122ms`、完整验证 `11403ms`；量化真实候选 `7` 只、覆盖 `85.00%`，专业字段 `unavailable`。
- 最终隔离 smoke：窗口 `125ms`、API `2446ms`、完整验证 `4526ms`；隔离数据不足时量化 `unavailable`。
- 最终 EXE SHA-256：`3EF466C656801B4869DD9FB9D04A2E054F0633CF16F1B808A80B1A19DE56D476`；smoke 后进程和 `17709` 已释放。

## 2026-08-07 量化后台预热动态状态

- 量化状态栏在候选扫描 `pending` 时新增无确定进度动画和已运行秒数；不显示未经扫描器提供的虚假百分比。
- 新增前端回归：验证后台预热提示、`aria-busy=true`、无 `aria-valuenow`，以及 5 秒到 7 秒的动态时间更新。
- 真实数据边界保持不变：完成前候选列表为空，失败时显示固定可行动原因，成功后才消费真实候选。

## 2026-08-07 真实扫描进度交付复验

- API 全量回归：`1146 passed, 1 skipped`；前端全量回归：73 个测试文件、`475 passed`；Vite/TypeScript 生产构建通过。
- 真实发布目录 smoke：窗口首帧 `94ms`，API 就绪 `2152ms`，完整验证 `11295ms`；首页 `144ms`、信息总览 `1097ms`、量化首次请求 `171ms`、专业探针 `1020ms`；量化真实候选 `7` 只、市场风格覆盖 `85.00%`，专业字段 `unavailable`。
- 隔离目录 smoke：窗口首帧 `113ms`，API 就绪 `2465ms`，完整验证 `4527ms`；信息总览 `ready`，无真实样本时量化 `unavailable`，未生成模拟候选。
- 进度契约回归覆盖 `loading_history`、`computing_factors`、`ranking`、`ready`、`failed` 以及真实 `processed/total` 百分比；无计数阶段不显示虚假百分比。
- smoke 后应用进程与探测进程均已释放，`127.0.0.1:17709` 未被本程序占用，`config/data/news/cache/logs/models/exports/backups` 全部保留。
- 本轮 EXE SHA-256：`896D6C80A2850451C631B87485425F7F134307B44B9679E53261E8D2F41560E9`。

## 2026-08-07 桌面启动真实里程碑复验

- 启动专项回归：桌面测试目录 `35 passed`（含启动阶段解析、日志尾部读取、API 模块导入里程碑、启动脚本和窗口等待期间更新）。
- 全量回归：API `1152 passed, 1 skipped`；前端 73 个测试文件、`475 passed`；Vite/TypeScript 生产构建通过。
- 真实发布目录连续两次 smoke：一次窗口/API/完整验证为 `317/5570/19459ms`（冷盘环境波动），随后热启动为 `62/1960/11194ms`；两次均为信息总览 `ready`、量化真实候选 `7` 只、覆盖 `85.00%`。
- 隔离目录 smoke：窗口/API/完整验证为 `114/2452/4545ms`；信息总览 `ready`，真实样本不足时量化 `unavailable`。
- 发布日志实际记录并解析 `api-app-imported import_ms=1951`，随后生命周期阶段约 `546ms`；其余差异归入 PyInstaller/Windows 冷盘读取波动，不用热启动结果替代冷盘结论。
- 发布日志实际记录并被解析的里程碑包括 `api-app-imported`、`local-sources-ready`、`repositories-ready`、`bond-universe-ready`、`services-and-instrument-directory-ready`、`a-share-universe-ready`、`market-sentiment-ready` 和 `lifespan-ready`。
- smoke 后应用/探测进程均已释放，`127.0.0.1:17709` 未监听，持久目录全部保留；本轮 EXE SHA-256：`80102A8140A9E794DF44D576288C2BC0624D5B7A14452B5F5671C6F40E76BD13`。

## 2026-08-07 API import milestone revalidation

- 桌面专项回归 `35 passed`；启动导入里程碑由 Uvicorn 字符串应用显式加载后写入日志，启动页可区分 API 模块导入与生命周期初始化。
- 真实发布目录连续三次 smoke：窗口/API/完整验证分别为 `299/5584/19437ms`、`59/1956/11085ms`、`55/2004/11035ms`；信息总览均为 `ready`，量化均为 `partial`（真实候选 7 只、市场风格覆盖 85.00%）。
- 隔离目录 smoke：窗口/API/完整验证 `122/2414/4492ms`；无真实样本时量化保持 `unavailable`，未生成模拟候选。
- 三次真实发布与隔离 smoke 后均无应用/探测残留进程，`127.0.0.1:17709` 未监听，`config/data/news/cache/logs/models/exports/backups` 全部保留。
- 本轮 EXE SHA-256：`EC47CDAFA176977C8D9CE2FBBA8FFF5F59DB763F8003A02DB4B8DCEEAAD08A8E`。

### 本轮仍未完成

- 通达信专业只读桥恢复后逐字段实测 `Fn/GP/BK/SC/GO` 并绑定业务菜单。
- 继续累积冷盘/热启动样本，拆分 PyInstaller/Windows 冷读取成本与业务接口耗时。

## 2026-08-07 冷启动导入成本基线

- EXE 发布 smoke 日志记录到 `api-app-imported import_ms=1951/1974/974` 三组样本；随后生命周期里程碑约 `546-594ms`，说明冷启动主要波动发生在 PyInstaller/Windows 内读取与应用模块导入阶段。
- CPython 基线 `python -X importtime -c "import qibao_api.main"` 约 `637ms`；较大的单项包括 FastAPI/Pydantic schema、公司研究/诊断契约和多路由模块。当前不据此盲目排除依赖。
- 后续优化门槛：任何懒加载或打包调整都必须同时通过 API/前端回归、真实发布 smoke、隔离 smoke，并记录冷盘与热启动两组结果。

## 2026-08-07 信息总览缓存优先与后台刷新

- 新增 `market-overview.json` 便携缓存：只写入上一轮实际生成的 `MarketOverviewResponse`，读取时按当前盘前/盘中/收盘后阶段重新计算 freshness。
- 有完整缓存时，信息总览接口先返回缓存并附带 `market-overview-cache` 来源标记，后台刷新完成后下一次轮询消费最新结果；刷新异常只保留旧证据并增加固定 `market_overview_refresh_failed` 警告。
- 真实发布 smoke 三次：首次建立缓存时信息总览请求 `5215ms`，随后两次为 `616ms`、`569ms`；窗口/API/完整验证分别为 `308/5584/19805ms`、`61/1998/10710ms`、`56/1983/10583ms`。
- 隔离 smoke：窗口/API/完整验证 `114/2445/4461ms`，无发布持久缓存时仍遵循真实数据边界，量化保持 `unavailable`。
- API 全量 `1153 passed, 1 skipped`；专项信息总览/生命周期回归 `24 passed`；生产构建通过；EXE SHA-256：`84AA38BF398D6B151D596F93E731EFEED8D72C0D8496CDBAE6C8DF417756B5DB`。
- smoke 后无应用或探测残留进程，`127.0.0.1:17709` 未监听，便携持久目录全部保留。

## 2026-08-07 通达信专业五类探针复验

- 便携 smoke 已逐项请求 `get_financial_data/Fn193`、`get_gpjy_value/GP1`、`get_bkjy_value/BK5`、`get_scjy_value/SC1`、`get_gp_one_data/GO1`。
- 五类结果均为 `unavailable`，没有因单字段、缓存文件或模块发现状态而误报 `ready`；每类返回原因均为官方 Python 专业接口初始化/调用失败。
- 专业探针总耗时 `5206ms`；本次发布 smoke 窗口/API/完整验证 `56/1968/14450ms`，信息总览请求 `563ms`，量化真实候选 7 只、市场风格覆盖 85.00%。
- `apps/api/tests/desktop/test_packaging.py` 专业探针覆盖回归 `11 passed`；smoke 后应用/探测进程释放，`127.0.0.1:17709` 未监听。

## 2026-08-07 同日旧快照 freshness 边界

- 盘中同日行情只有在观测时间距当前不超过 2 分钟时才标记 `live`；超过窗口统一标记 `stale`，避免当天旧缓存被误称为实时。
- 新增 `test_overview_marks_old_same_day_snapshot_stale_during_session` 回归；信息总览专项测试 `12 passed`。
- 候选后台扫描测试改为等待真实线程事件，专项连续 10 次通过，消除调度竞态造成的误失败。
- 重新构建后的真实发布 EXE 串行 smoke：窗口/API/完整验证 `63/2000/14700ms`；信息总览 `593ms`，量化真实候选 7 只、覆盖 85.00%，五类专业探针均 `unavailable`。
- 本轮 EXE SHA-256：`DA8C2486AA19F8EFEE4088FCFD1934F3639F4F688AB33086BB5F5D68004BABC1`；smoke 后无应用/探测残留进程，`127.0.0.1:17709` 未监听。

## 2026-08-07 通达信专业失败冷却与发布复验

- `TdxQuantPythonSource` 对同一初始化/调用失败增加 10 秒短时冷却；冷却只返回相同的 `unavailable`，不缓存专业数据，也不把失败升级为 `partial/ready`。
- 新增 `test_python_professional_source_cools_down_repeated_unavailable_initialization`，确认连续两次只读查询只执行一次官方客户端初始化；专业源专项 `10 passed`，Ruff 通过。
- API 全量 `1156 passed, 1 skipped`；前端上一轮全量 `475 passed`，Vite/TypeScript 生产构建和 PyInstaller 便携构建通过。
- 真实发布冷盘 smoke：窗口/API/完整验证 `290/5577/18858ms`，信息总览 `4882ms`，专业五类探针 `1032ms`。
- 真实发布热启动 smoke：窗口/API/完整验证 `58/1959/10359ms`，信息总览 `656ms`，专业五类探针 `1079ms`。
- 两次均为信息总览 `ready`、量化 `partial`（7 只真实候选、市场风格覆盖 85.00%）、五类专业字段全部 `unavailable`；没有模拟值。
- 最新 EXE SHA-256：`743434B752F0B13007E261B6B793AE47D872D788B7DA89EAD72953A7D81C6DA6`；smoke 后无应用/探测残留进程，`127.0.0.1:17709` 未监听，持久目录全部保留。

## 2026-08-07 预交易时段无效刷新移除

- 根因：预交易阶段 `MarketSentimentService.refresh()` 必然在阶段检查处结束，但旧启动路径仍将任务放入单线程历史执行器；真实日志显示该无效任务约在启动后 5.5 秒才完成跳过。
- 修复：新增 `_should_defer_initial_market_sentiment_refresh()`，仅在中国时间 `09:30` 以后提交初始市场情绪后台刷新；预交易不排队、不占用历史执行器。
- 回归：新增 premarket/intraday 判定测试；API 全量 `1157 passed, 1 skipped`。
- 真实发布冷盘 smoke：窗口/API/完整验证 `96/2105/11198ms`，信息总览 `770ms`，量化真实候选 7 只、市场覆盖 85.00%，专业五类探针 `1031ms`。
- 真实发布热启动 smoke：窗口/API/完整验证 `62/2029/10529ms`，信息总览 `650ms`，量化真实候选 7 只、市场覆盖 85.00%，专业五类探针 `1031ms`。
- 最新构建沿用持久目录保留策略；测试后 `D:\new_tdx_mock` 进程已清理，`127.0.0.1:17709` 未监听。

### 当前计划与目标

- [ ] 通达信客户端完成专业插件初始化并恢复只读桥后，逐项实测 `Fn/GP/BK/SC/GO`，记录请求、响应形状、字段单位、来源和时间戳。
- [ ] 仅将实测通过的专业字段绑定到业务菜单；空字段、错误包和单位不明确继续显示 `unavailable`。
- [ ] 只有扫描器能提供真实处理数量/阶段时，才将无确定进度升级为确定百分比；当前继续使用真实动态等待状态。
- [ ] 继续积累冷盘与热启动 EXE 样本，单独记录窗口首帧、API 就绪、业务请求和专业探针耗时。

## 2026-08-07 5 秒刷新视觉连续性修复

- 前端回归：`73` 个测试文件、`476 passed`。
- API 回归：`1157 passed, 1 skipped`。
- 生产构建：Vite/TypeScript 通过。
- 真实发布 EXE smoke：窗口 `92ms`、API 就绪 `2122ms`、完整验证 `21787ms`；首页 `98ms`、信息总览 `729ms`、量化请求 `11214ms`、专业探针 `1101ms`。
- 真实数据状态：信息总览 `ready`；量化 `partial`，真实候选 `7` 只、市场风格覆盖 `85.00%`；通达信五类专业字段均 `unavailable`，未使用模拟值。
- 视觉回归：首次有效快照完成后，5 秒后台刷新期间启动遮罩保持隐藏，旧完整行情继续展示；刷新完成后新数据正常替换。
- 资源释放：smoke 后本程序进程与 `127.0.0.1:17709` 已释放；用户通达信进程不应由本项目清理流程主动关闭。
- 最新 EXE：`dist/XiaoQiBao-Portable/xiaoqibao.exe`，SHA-256 `A94DB00085F5182EB529D89EBF7FB748577C6FA8E759D62EFC37DB546C9CCC83`。
