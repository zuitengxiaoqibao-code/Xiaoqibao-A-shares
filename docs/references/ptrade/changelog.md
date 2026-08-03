# PTrade 接口版本变更索引

> 官方入口：https://ptrade.i618.com.cn:7766/hub/help/api#接口版本变动
> 共 30 个版本节点，按官网从新到旧排列。以下保留会影响代码、字段、返回类型、环境和依赖的变更。

## PTrade1.0-QTV202401.05.032

- `run_interval` 新增 `interval_timer_ranges`，可限定函数运行时间范围。

## PTrade1.0-QTV202401.05.031

- Python 3.5 新增 `gmssl==3.2.2`、`psycopg2-binary==2.8.6`。
- Python 3.11 新增 `gmssl==3.2.2`、`psycopg2-binary==2.9.11`。

## PTrade1.0-QTV202401.05.030

- `get_fundamentals`：资产负债表增加 `contract_liability/total_fixed_asset/t_constru_in_process`，利润表增加 `r_and_d`。

## PTrade1.0-QTV202401.05.021

- `get_market_list/get_market_detail` 只支持系统内四个市场。
- Python 3.11 新增 `dtaidistance==2.3.13`。

## PTrade1.0-QTV202401.05.013

- `get_price(fq)` 新增 `dypre` 动态前复权。
- `get_price` 异常返回由空字典调整为 `None`。

## PTrade1.0-QTV202401.05.011

- Python 3.5/3.11 的 `sxsc-tushare` 由 `1.2.11` 升至 `20240927`。

## PTrade1.0-QTV202401.05.008

- 期货 `Portfolio` 删除 `capital_used`，增加 `margin`。

## PTrade1.0-QTV202401.05.000

- Python 3.11 升级 `bs4 0.0.2`、`gensim 4.3.3`、`jax/jaxlib 0.4.18`、`line_profiler 4.1.3`、`qdldl 0.1.7.post4`、`TA-Lib 0.4.31`。
- Python 3.11 新增 `asyncache/fastapi/h11/pydantic/starlette/uvicorn/baostock`；Python 3.5 新增 `baostock`。
- 股票 `Position` 增加 `update_time`。
- 新增成交类型和成交状态字典。

## PTrade1.0-QTV202401.04.000

- 新增 `fund_transfer`、`market_fund_transfer`、`set_email_info`。
- `on_trade_response` 增加 `real_type/real_status`。
- `run_interval` 最小间隔规则改为期货 1 秒、股票等其他业务 3 秒。
- `create_dir` 返回由 `None` 改为布尔值。
- Python 3.5 新增 `walrus==0.9.3`。

## PTrade1.0-QTV202401.02.000

- 两融多个接口增加或调整 `cash_group` 默认语义，未传时通常表示普通头寸。
- `get_margin_contract` 增加 `compact_source` 入参与返回。
- 新增/明确 `get_crdt_fund`。
- Python 3.5 新增 `memory-profiler==0.61.0`、`psutil==5.9.5`。

## PTrade1.0-QTV202401.01.000

- `set_parameters` 新增 `not_restart_trade/server_restart_not_do_before`。
- 委托属性增加 `4` 回购。

## PTrade1.0-QTV202401.00.000

- `get_margin_contract/get_margin_contractreal/get_deliver` 的部分委托编号字段改为字符串。
- `set_benchmark` 入参由 `security` 改为 `sids`。
- 新增 `check_strategy`、`get_dominant_contract`。
- Python 3.5 新增 `flameprof/pypinyin`；Python 3.11 新增 `pypinyin`。

## PTrade1.0-QTV202301.03.000

- 弃用拼写错误的 `get_individual_transcation` 和 `get_margin_assert`。
- `check_limit` 增加研究/回测支持。
- `ipo_stocks_order` 的 `market_type` 改为 `submarket_type`。
- 多个两融/港股通接口的 `market_type/entrust_type` 更名为 `exchange_type/trade_type`。
- `get_etf_info` 的 `pre_cash_componet` 修正为 `pre_cash_component`。
- `get_fundamentals(date)` 支持 `datetime.date`，增加 `is_dataframe`，弃用 `date_type`。
- `set_parameters` 不再支持 `individual_data_in_dict/tick_direction_in_dict`。
- 逐笔、分时接口分别增加 `is_dict`。
- `get_gear_price` 不再支持回测。
- `get_stock_status` 增加 `DELISTING_SORTING`。
- 期货回测 `get_trades` 增加开平仓字段。
- 新增 `filter_stock_by_status/get_current_kline_count/get_trading_day_by_date`。
- 股票 `Position` 增加 `today_amount`。
- 新增 Python 3.11；因 Pandas 不再支持 Panel，多个接口在 3.11 默认返回 DataFrame。

## PTrade1.0-QTV202301.02.000

- `get_snapshot` 删除 `close_px/avg_px`。
- 日 K 线 `get_price/get_history` 增加 `is_open`。
- 删除 `arch/cvxopt`，新增 `PuLP`。
- 研究环境新增 `get_history`。
- 新增 `get_business_type/get_ipo_stocks`。

## PTrade1.0-QTV202301.01.000

- 非交易时段的两融/盘后固定价等交易委托直接发柜台。
- `Order` 增加 `cancel_entrust_no`。
- 期货 `Position` 删除 `margin_rate`，增加 `margin`。
- `run_interval` 当时曾把最小周期改为 0.1 秒；后续版本已再次调整。
- `get_trades` 委托编号统一字符串，成交时间统一格式。
- `order_market` 增加 `order_id` 返回。
- 两融平仓接口增加 `market_type`。
- `get_price/get_history` 增加 `is_dict`。
- 新增 `get_margin_asset/get_individual_transaction/get_reits_list`。

## PTrade1.0-QTV202301.00.000

- 两融最大融资数量增加 `cash_group`。
- `get_all_orders` 增加 `entrust_time`。
- `get_open_orders` 改为每日收盘后清空未完成订单列表。
- 新增 `get_cb_info/get_enslo_security_info/get_trend_data`。

## PBOXQT1.0V202202.03.000

- `get_user_name` 增加 `login_account`。
- `debt_to_stock_order` 支持两融交易。
- `get_instruments` 增加涨跌幅限制和最小变动价位。
- 上海股票的 `order_market/margin_trade` 市价委托要求保护限价。
- `send_email` 单交易每分钟最多一次。
- 新增 `get_all_positions/get_lucky_info/get_future_main_code`，新增 `pykalman`。

## PBOXQT1.0V202202.02.000

- `get_price/get_history` 增加期货数据。
- `get_snapshot` 增加 `iopv`。
- `handle_data.data` 明确为 `BarData`；增加日线昨收、涨跌停和无限制字段，时间改为北京时间。
- `on_trade_response` 增加 `withdraw_no/cancel_info`，委托号统一字符串。
- `set_parameters` 当时增加逐笔/分时字典返回开关，后续已取消。
- `set_yesterday_position` 支持 ETF/LOF。
- 两融开仓增加 `cash_group`；上海市价委托保护限价为必传。
- `get_index_stocks` 由多指数改为只支持单指数。
- Keras 因 TensorFlow 兼容问题从 2.3.1 降到 2.2.4。
- 新增 `get_frequency/get_underlying_code`。

## PBOXQT1.0V202202.01.000

- 非交易时段委托直接发送柜台。
- `tick_data` 超过 3 秒会丢中间事件，收盘后清空未执行队列。
- `tick_data.data` 快照改为来自 `get_snapshot`。
- 修复逐笔接口证券数大于 50 时的数据缺失。
- `run_interval/run_daily` 增加 `get_sort_msg` 支持。
- `get_snapshot` 增加内外盘量及多项快照字段。
- `on_trade_response` 支持撤单成交主推。
- 新增备兑开平仓、行权和 `set_parameters`。

## PBOXQT1.0V202202.00.000

- 日志增加 DEBUG。
- 历史行情增加昨收、涨跌停和无限制字段。
- 快照增加委买卖量和金额。
- 成交主推增加 `order_id`；策略外交易没有 Order 时为 `""`。
- 弃用期货平仓方式设置/查询接口；期货平仓改用 `close_today`。
- `run_daily/run_interval` 可多次调用，但累计不超过 5。
- 新增 MACD/KDJ/RSI/CCI 和 `create_dir`。

## PBOXQT1.0V202201.02.000

- `get_snapshot` 补充 `issue_date` 说明。

## PBOXQT1.0V202201.01.000

- 订单状态类型统一为字符串。
- 新增 `get_trade_name`。
- 证券名称/信息增加转债、ETF、LOF。
- `get_history` 增加 `fill`。
- 历史行情增加 5/15/30/60/120 分钟频率。

## PBOXQT1.0V202201.00.000

- 逐笔成交增加买卖方编号、成交标记、盘中/盘后标识和通道。
- 两融合约增加实时利息、金额、数量字段。
- 历史行情增加月、季、年频率。
- `set_commission` 支持 LOF。
- 逐笔价格缩小 1000 倍后返回真实价格。
- 增加期货日盘回测/交易。
- 新增 `get_tick_direction/get_sort_msg/permission_test`。

## PBOXQT1.0V202101.09.000

- 市场目录/详情当时限制盘前盘后调用；后续版本已扩展。
- 快照增加时间戳，Level-2 买卖一档增加委托队列。
- 新股申购增加黑名单。
- 委托主推增加错误信息。

## PBOXQT1.0V202101.08.000

- `initialize` 可调用 API 范围受限，两融委托在盘前盘后也受限。
- 修复单笔成交返回格式和 14:58/14:59 当日 K 线价格为 0。
- 邮件增加附件和主题。
- 新增 `get_cb_list/get_deliver/get_fundjour/get_research_path`。
- `get_market_detail` 增加回测/交易支持。

## PBOXQT1.0V202101.07.000

- 快照增加加权均价、涨跌幅。
- 可转债回测支持 T+0。
- 增加两融回测，初期只支持 `margin_trade`。

## PBOXQT1.0V202101.06.000

- 新增 `get_user_name`。
- 研究 `get_price` 支持周线。
- 快照支持行业板块市场数据。
- 企业微信增加部门、个人、分组目标参数。

## PBOXQT1.0V202101.05.000

- 信用账户支持新股一键申购。
- 五类能力表不再返回 `company_type`。
- 上海转债转股改为传可转债代码。

## PBOXQT1.0V202101.04.000

- `get_all_orders.status` 由整数改为字符串。
- 委托/成交主推可选支持策略外交易；策略外委托主推不含 `order_id`。

## PBOXQT1.0V202101.03.000

- 委托主推增加 `entrust_type/entrust_prop`。
- 修复信用交易兼容。
- 历史行情支持周频。
- `get_fundamentals` 删除不再维护的 `share_change` 表。

## 兼容策略

- 保存实际 PTrade 版本，不用“当前最新版”作为不可变假设。
- 对 `None/{}/DataFrame/dict` 等历史返回形态做显式兼容。
- 订单号统一按字符串存储。
- 版本变化涉及行为而不只是字段时，必须重新回测和柜台沙盒验证。
