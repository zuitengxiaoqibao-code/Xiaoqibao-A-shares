# 行情、交易日历与实时数据

## 交易日历和市场目录

| 函数 | 用途 |
| --- | --- |
| `get_trading_day(day)` | 相对当前时间获取前/后交易日 |
| `get_all_trades_days(date=None)` | 获取某日期之前的全部交易日 |
| `get_trade_days(start_date, end_date, count)` | 获取指定范围或数量的交易日 |
| `get_trading_day_by_date(query_date, day=0)` | 以输入日期为锚获取指定交易日 |
| `get_market_list()` | 返回平台支持的市场目录 |
| `get_market_detail(finance_mic)` | 获取市场编码详情 |

版本记录显示，较新版本将市场目录限制为系统支持的四个市场。桥接层不能自行假定所有 MIC 都可用。

## 历史行情

### `get_history`

签名：`get_history(count, frequency='1d', field='close', security_list=None, fq=None, include=False, fill='nan', is_dict=False)`。

- 研究、回测、交易可用；返回最近 N 根 K 线。
- 支持多证券、多字段和日/分钟/周频。
- `include=True` 会包含当前周期。官方 FAQ 建议仅在明确理解语义时使用，日线回测可借此提速，其他场景要谨慎。
- 没传 `security_list` 时可使用 `set_universe` 的默认池。

### `get_price`

签名：`get_price(security, start_date=None, end_date=None, frequency='1d', fields=None, fq=None, count=None, is_dict=False)`。

- 研究、回测、交易可用；按日期范围或数量取历史行情。
- `fq` 支持不复权、前复权、后复权和动态前复权；新版增加 `dypre`。
- `get_price` 不包含当前交易日数据；盘后当天数据需要经过确认的数据链路或次日补录。
- 新版异常返回从空字典调整为 `None`，代码必须同时兼容空字典、`None` 和部分证券缺失。

### 共同约束

- 历史行情从 2005 年开始。
- 官方文档明确警告 `get_history` 与 `get_price` 不要并发调用，否则可能偶发空结果。
- 停牌日期会以前一价格填充，成交量为 0；这不是正常成交，应保留停牌/零量标记。
- 周线由日线合成；为可追溯和规则统一，项目优先存日线后在本地聚合周/月线。
- 请求成功不等于数据完整。每批应记录证券数、期望根数、实际根数、空响应、时间范围、复权方式和耗时。

建议日线字段：`open/high/low/close/volume/money/preclose/high_limit/low_limit/is_open/unlimited`。

## 盘中快照与档位

| 函数 | 环境 | 能力 |
| --- | --- | --- |
| `get_snapshot(security)` | 交易 | 最新价、OHLC、成交、五档、估值、涨跌停、状态等实时快照 |
| `get_gear_price(sids)` | 交易 | 指定代码档位价格 |
| `get_sort_msg(...)` | 交易 | 板块/行业快照及字段排序 |
| `get_trend_data(date, stocks, market)` | 研究/回测/交易 | 集中竞价期间代码数据 |
| `get_tick_direction(...)` | 交易 | 当日分时成交行情 |

`get_snapshot` 异常返回 `{}`。空快照必须计入覆盖率，不能用 0 代替。字段可用于价格强度、活跃度、广度和涨跌停情绪，但只有覆盖达到阈值才允许生成市场级分数。

官方 FAQ 建议：回测用 `data[stock].price` 获取当前不复权价格；交易用 `get_snapshot` 获取最新价。

## Level-2

| 函数 | 内容 | 限制 |
| --- | --- | --- |
| `get_individual_entrust` | 当日逐笔委托 | 仅交易、需要 Level-2，单次最多约 200 条 |
| `get_individual_transaction` | 当日逐笔成交 | 仅交易、需要 Level-2，单次最多约 200 条 |
| `tick_data` | 快照、近期逐笔事件的周期回调 | 约 3 秒；处理超时会丢中间事件 |

云纪仿真环境官方 FAQ 表示不提供 Level-2，券商环境是否提供取决于券商。因此主动买卖比、大单集中度、撤单强度、封单稳定度等指标必须在权限验证后启用，不能在未开通时伪造。

## 行情字段语义

- `BarData` 分钟频率中的 `preclose/high_limit/low_limit/unlimited` 均填充为 `0.0`，不能直接当有效值。
- `BarData` 当前周期首次调用会在线取数，同一周期后续调用返回首次缓存。
- 交易快照字段受行情源、柜台和交易状态影响，使用前要结合 `trade_status`。
- 盘后固定价格、停牌、长期停牌和退市需要分别识别，完整状态值见 `07-objects-and-data-dictionaries.md`。

## 数据桥最低契约

每份导出至少保存：

```text
schema_version, ptrade_version, environment, dataset,
generated_at, trading_date, source_symbol, normalized_symbol,
exchange, frequency, adjustment, record_count, checksum, payload
```

导入前校验 OHLC 关系、交易日期、重复键、证券后缀、记录数和校验和。失败时保留上一份已验证数据，不覆盖为“空”。
