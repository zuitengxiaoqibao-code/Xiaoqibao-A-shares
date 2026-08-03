# PTrade API 项目参考

> 状态：外部能力储备，当前项目尚未接入
> 官方文档：https://ptrade.i618.com.cn:7766/hub/help/api
> 核对日期：2026-07-27
> 文档版本线索：页面最新变更记录包含 `PTrade1.0-QTV202401.05.032`

> 完整知识库入口：[`ptrade/data_structure.md`](ptrade/data_structure.md)
> 完整库覆盖 149 个事件/函数、6 个对象、23 组数据字典、55 条 FAQ、两套三方库清单、官方示例和 30 个历史版本节点。本文件只保留当前项目最相关的执行摘要。

## 使用原则

PTrade 是运行在券商研究、回测和交易环境中的 Python 策略引擎，不是可以从本地 FastAPI 直接调用的公开 HTTP API。任何接入都必须通过 PTrade 内部策略导出数据或通过经过验证的桥接程序完成。

在没有完成券商权限、数据完整性和实盘隔离验证前：

- 不把 PTrade 标记为当前已连接的数据源。
- 不因为文档存在接口就假定账户具有对应权限。
- 不从本地系统自动触发实盘委托。
- 缺失或空结果必须标记为不可用，不能补造数据。
- 数据必须保留来源、PTrade 运行环境、获取时间和交易日期。

## 对本项目最有价值的能力

| 项目用途 | PTrade 能力 | 适用模块 | 关键限制 |
| --- | --- | --- | --- |
| 有效 A 股证券池 | `get_Ashares`、`get_stock_status` | 日线回填、市场情绪、首次涨停 | 仅沪深 A 股；退市、ST、停牌需分别查询 |
| 历史行情 | `get_history`、`get_price` | 日线、周线、月线、回测、技术指标 | 仅 2005 年后；不能并发调用；`get_price` 不含当日 |
| 实时行情 | `get_snapshot` | 盘中监测、个股诊断、情绪分析 | 仅交易模块；异常返回空字典 |
| Level-2 | `get_individual_entrust`、`get_individual_transaction` | 盘口强弱、成交主动性、短线信号 | 需要 Level-2 权限；仅交易模块；单次最多 200 条 |
| 基本面 | `get_fundamentals` | 估值、质量、风险、首次涨停筛选 | 部分指标非 PIT；回测必须防未来数据 |
| 可转债 | `get_cb_list`、`get_cb_info` | 独立转债观察与诊断 | 列表含停牌；基础资料可能需单独权限 |
| 交易日历 | `get_trading_day`、`get_trade_days`、`get_all_trades_days` | 调度、回填、盘前盘后任务 | 按 PTrade 环境交易日口径使用 |
| 盘前/盘中/盘后 | `before_trading_start`、`handle_data`、`after_trading_end`、`run_daily` | 三阶段决策系统 | 事件执行时间由券商环境和策略频率决定 |
| 委托与成交回报 | `on_order_response`、`on_trade_response` | 将来实盘执行与审计 | 仅交易模块；回调内下单要防止递归循环 |
| 持仓与订单 | `get_position(s)`、`get_all_positions`、`get_order(s)`、`get_trades` | 将来实盘状态核对 | 必须以柜台回报为最终事实 |

## 第一优先级：修复全市场日线和证券池

PTrade 最先值得利用的不是自动下单，而是建立可靠的券商数据桥。

### 有效证券池

建议在 PTrade 中按目标交易日执行：

1. `get_Ashares(date)` 获取该日沪深 A 股列表。
2. 分批调用 `get_stock_status(stocks, 'DELISTING', date)` 排除已退市证券。
3. 调用 `get_stock_status(stocks, 'DELISTING_SORTING')` 标记退市整理期。该类型只支持交易场景当日查询。
4. 调用 `get_stock_status(stocks, 'ST', date)` 和 `get_stock_status(stocks, 'HALT', date)`，保留标签而不是默认删除，交由策略规则决定。
5. 导出代码、名称、交易日、状态和获取时间，作为可追溯的证券池快照。

该流程可以替换当前仅凭公开证券目录造成的虚假分母，避免 `PT金田A`、`招商地产` 等历史失效代码进入“当前活跃 A 股”覆盖率。

### 日线回填

推荐使用 `get_price` 按代码批次、串行回填：

```python
fields = [
    "open", "high", "low", "close", "volume", "money",
    "preclose", "high_limit", "low_limit", "is_open", "unlimited",
]

bars = get_price(
    securities,
    end_date=target_date,
    frequency="1d",
    fields=fields,
    count=300,
    fq=None,
    is_dict=True,
)
```

必须遵守：

- `get_price` 与 `get_history` 官方明确不支持同时多线程调用，否则可能偶发空数据。
- 以串行小批次执行；每批独立记录成功、空响应、异常和耗时。
- 日线停牌日会使用停牌前价格填充且成交量为 0，入库时保留原值并标记停牌/零成交，不把它当正常交易日量价信号。
- `get_price` 不返回当日数据。当日收盘数据应在盘后通过确认过的接口或次日补录。
- 周线和月线可由日线本地聚合；PTrade 周线本身也是日线合成结果。
- 数据可追溯字段至少包括 `source=ptrade`、`retrieved_at`、`target_date`、PTrade 版本、代码后缀和复权类型。
- 只有实际覆盖达到门槛才标记完成，不能以“请求成功”代替“300 日完整”。

### 代码格式

PTrade 使用以下后缀：

| 市场 | 全称 | 简称 | 本项目规范化结果 |
| --- | --- | --- | --- |
| 上海 | `XSHG` | `SS` | 六位代码 + `sh` |
| 深圳 | `XSHE` | `SZ` | 六位代码 + `sz` |

桥接层必须统一完成 `600519.SS -> 600519`、`000001.SZ -> 000001`，并单独保存交易所字段。

## 第二优先级：盘中行情与情绪因子

`get_snapshot(security)` 可以补充当前公开行情源不稳定时缺失的盘中字段：

- 最新价、今开、最高、最低、昨收。
- 涨跌幅、成交量、成交额、成交笔数。
- 五档买卖价格、委托量、委托笔数。
- 委比、委差、内盘、外盘、加权均价。
- PE、PB、换手率、量比、流通股本。
- 涨停价、跌停价、交易状态、最小报价单位。

可映射到现有市场情绪模型：

| 情绪分项 | 可利用字段 |
| --- | --- |
| 波动率情绪 | `high_px`、`low_px`、`preclose_px`、分钟线 |
| 成交活跃度 | `business_amount`、`business_balance`、`business_count`、`turnover_ratio`、`vol_ratio` |
| 价格强度 | `last_px`、`preclose_px`、`px_change_rate`、`wavg_px` |
| 风险偏好 | 不同板块/市值组涨跌、涨停触达率、成交额占比 |
| 市场广度 | 全市场快照上涨、下跌、平盘数量 |
| 涨跌停情绪 | `up_px`、`down_px`、`last_px`、`trade_status` |
| 赚钱效应 | 个股收益分布、中位数、强势股持续性 |
| 板块扩散 | `get_stock_blocks`、`get_sort_msg` 与板块内上涨比例 |
| 风格偏好 | 市值、估值、行业分组后的相对强弱 |

`get_snapshot` 仅在交易模块可用，异常返回 `{}`。任何空快照都必须计入覆盖率，不能用零值参与评分。

## Level-2 和短线信号

如果账户开通 Level-2，可以利用：

- `get_individual_entrust`：逐笔委托，包含时间、价格、委托量、委托编号、方向和委托类型。
- `get_individual_transaction`：逐笔成交，包含成交编号、买卖方编号、方向、通道等。
- `tick_data`：股票策略约每 3 秒触发一次，可携带快照、最近逐笔委托和逐笔成交。
- `run_interval`：股票等业务最小 3 秒；定时任务线程总数限制为 5，堵塞任务不会累积执行。

适合后续构建但当前不应伪装成已有数据的指标：

- 主动买卖成交比例。
- 大单成交集中度。
- 买卖盘失衡与撤单强度。
- 价格突破时的成交确认。
- 涨停封单稳定度和开板风险。

约束：逐笔接口只在交易模块可用，没有 Level-2 时返回空。`tick_data` 单次执行超过 3 秒时会丢弃中间事件，因此 AI 推理不能放在该回调的同步路径中。

## 可转债能力

### `get_cb_list`

- 仅交易模块可用。
- 返回当前市场全部可转债代码，包含停牌代码。
- 同一分钟多次调用返回本分钟首次查询的缓存。
- 必须结合 `get_snapshot` 的 `trade_status` 过滤 `HALT`、`SUSP`、`STOPT`、`DELISTED` 等状态。

### `get_cb_info`

- 研究和交易模块可用。
- 需要券商提供可转债基础数据权限；无权限或失败返回空 DataFrame。
- 可用字段包括转债/正股代码和名称、上市日、溢价率、转股起始日、到期日、转股比例、转股价、转股价值。

这些字段适合补充独立的可转债诊断页，但 A 股和转债仍须保持不同领域模型，不混成同一个候选池。

交易限制：`order_market` 明确不支持可转债。可转债限价价格精度为三位小数，回测数量按 10 张取整；交易时具体单位仍需向券商确认。

## 财务与估值数据

`get_fundamentals` 支持：

- `valuation`：估值数据。
- `balance_statement`：资产负债表。
- `income_statement`：利润表。
- `cashflow_statement`：现金流量表。
- 成长、盈利、每股、营运和偿债能力指标。

防未来数据规则：

- 回测优先 `merge_type=None`，使用首次发布数据。
- 研究和盘中诊断可以在明确指定报告期后使用 `merge_type=1` 获取更新数据。
- 成长、盈利、EPS、营运和偿债能力五类指标被官方标注为非 PIT 数据，不能直接用于无偏历史回测。
- 所有财务证据应保存报告期、发布日期、查询日期和更新模式。
- 返回 `None` 或 `NaN` 表示未披露/无数据，不能当作 0。

## 三阶段决策映射

| 本项目阶段 | PTrade 事件/函数 | 推荐职责 |
| --- | --- | --- |
| 盘前研判 | `before_trading_start`、`run_daily` | 更新证券池、状态、前一交易日日线、候选与风险标记 |
| 盘中监测 | `handle_data`、`run_interval`、`tick_data` | 快照、盘口、成交、触发条件和风险提醒 |
| 盘后复盘 | `after_trading_end`、盘后 `run_daily` | 落地当日事实、核对成交、复盘信号、生成次日观察池 |

PTrade 的 `initialize` 和 `handle_data` 是基础必选函数。框架会持久化可序列化的全局 `g` 状态；以 `__` 开头的私有变量和不可序列化对象不会持久化。桥接任务应另建幂等账本，不能只依赖 `g`。

## 将来实盘执行边界

可用接口包括 `order`、`order_target`、`order_value`、`order_target_value`、`order_market`、撤单、订单查询以及委托/成交主推。

在本项目真正接入前必须满足：

1. 分析系统与执行系统进程隔离。
2. 默认仅生成建议，不自动下单。
3. 每笔委托经过人工确认、标的白名单、交易时段、涨跌停、停牌、资金和持仓风控。
4. 使用唯一意图 ID，避免重启或重试产生重复订单。
5. 委托回报和成交回报持久化，柜台状态优先于本地推测。
6. 回调中调用委托接口必须有状态机保护，防止无限递归。
7. 限价精度按品种处理：股票两位小数，可转债/ETF/LOF 三位小数。
8. 先做研究导出，再做模拟或极小规模人工确认交易，最后才评估自动执行。

## 建议的桥接数据契约

PTrade 侧只导出事实，不输出 AI 结论。建议使用 JSON Lines 或 Parquet：

```text
manifest
  schema_version
  ptrade_version
  environment: research | backtest | trade
  dataset: universe | daily_bars | snapshots | fundamentals | bonds
  generated_at
  trading_date
  record_count
  checksum

record
  normalized_symbol
  source_symbol
  exchange
  observed_at
  source: ptrade
  payload
```

本地导入必须先校验 schema、记录数、校验和、交易日期、重复键和 OHLC 合法性，之后才写入 DuckDB/SQLite。导入失败不覆盖上一份已验证快照。

## 权限和可用性验证清单

只有以下检查通过后，才可以把 PTrade 数据源状态改为“已配置”：

- [ ] 券商账户可进入 PTrade 研究环境。
- [ ] 明确 Python 版本（优先验证 3.11）。
- [ ] `get_Ashares` 返回当日合理数量且沪深市场齐全。
- [ ] `get_stock_status` 能识别已知 ST、停牌和退市样本。
- [ ] `get_price` 对沪深各一只股票返回 300 根合法日线。
- [ ] 确认批量大小和串行运行耗时。
- [ ] `get_snapshot` 权限和盘中更新时间验证通过。
- [ ] 确认可转债基础数据权限；无权限时维持现有转债来源。
- [ ] 确认是否具备 Level-2；无权限时禁用逐笔相关指标。
- [ ] 导出文件能够安全传到本地且不包含账号、Cookie、Token 或其他凭据。
- [ ] 本地导入具备幂等、断点恢复、来源健康和覆盖率统计。

## 当前结论

PTrade 对本项目最现实的价值顺序是：

1. 有效 A 股证券池和退市状态。
2. 全市场历史日线回填。
3. 盘中快照与市场情绪增强。
4. 财务和估值证据增强。
5. 可转债基础资料增强。
6. 有 Level-2 权限后再开发短线微观结构信号。
7. 实盘订单桥接最后考虑。

在完成权限验证和桥接实现前，当前数据源优先级保持不变。接通并验证后，可以在日线与证券池领域将 PTrade 作为券商级首选来源，同时继续用通达信、腾讯和百度进行交叉核验与故障回退。
