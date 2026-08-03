# 账户、持仓、委托与成交

## 账户和持仓查询

| 函数 | 环境 | 作用 |
| --- | --- | --- |
| `get_position(security)` | 回测/交易 | 单标的 `Position` |
| `get_positions(security)` | 回测/交易 | 多标的持仓详情 |
| `get_all_positions()` | 交易 | 当前账户全部持仓 |
| `get_user_name(login_account=True)` | 回测/交易 | 登录终端资金账号 |
| `get_trade_name()` | 交易 | 当前交易名称 |
| `get_trades_file(save_path='')` | 回测 | 对账数据文件 |
| `convert_position_from_csv(path)` | 回测 | 将 CSV 转为回测底仓参数 |
| `get_deliver(start_date, end_date)` | 交易 | 历史交割单；仅盘前/盘后阶段，部分柜台不支持 |
| `get_fundjour(start_date, end_date)` | 交易 | 历史资金流水；仅盘前/盘后阶段，部分柜台不支持 |
| `get_lucky_info(start_date, end_date)` | 交易 | 历史中签信息；部分柜台不支持 |

交易环境的账户、持仓和订单数据通常约 6 秒一次与柜台同步，具体以券商配置为准。`Portfolio`、`Position` 和 `Order` 都可能暂时落后于真实柜台状态，策略必须使用过渡状态防止重复判断和重复下单。

## 股票委托

| 函数 | 意图 | 关键语义 |
| --- | --- | --- |
| `order` | 按增减数量交易 | 买入为正、卖出为负；可指定限价 |
| `order_target` | 调整到目标数量 | 适合清仓或定量仓位 |
| `order_value` | 按目标交易金额增减 | 实际数量受价格和交易单位影响 |
| `order_target_value` | 调整到目标持仓市值 | 回测和交易可用 |
| `order_market` | 按指定市价类型委托 | 仅交易；不支持可转债；可带保护限价 |
| `ipo_stocks_order` | 当日新股一键申购 | 仅交易；部分柜台不支持 |
| `after_trading_order` | 盘后固定价委托 | 仅 PTrade 客户端股票交易；部分柜台不支持 |
| `after_trading_cancel_order` | 撤销盘后固定价委托 | 同上 |
| `etf_basket_order` | ETF 成分券篮子下单 | 仅客户端股票交易；柜台限制明显 |
| `etf_purchase_redemption` | ETF 申赎 | 仅客户端股票交易；柜台限制明显 |
| `order_tick` | Tick 回调中按档位委托 | 仅交易；用于 `tick_data` |
| `debt_to_stock_order` | 可转债转股 | 仅交易；上海市场传转债代码 |

官方 FAQ 的重要说明：

- 数量必须是整数，否则委托失败并返回 `None`。
- 限价类函数未传 `limit_price` 时，引擎可能用快照最新价报单；快照为空会形成废单。
- 集合竞价可以下单，但策略仍要检查时间、涨跌停和行情有效性。
- 批量委托官方测试口径约为 300 笔 2 秒；这不是所有券商、柜台和网络环境的性能保证。

## 撤单和查询

| 函数 | 作用 |
| --- | --- |
| `cancel_order(order_param)` | 按 `Order` 或订单 ID 撤单；回测/交易 |
| `cancel_order_ex(order_param)` | 按 `get_all_orders` 返回字典撤单；交易 |
| `get_open_orders(security=None)` | 策略内未完成订单 |
| `get_order(order_id)` | 指定订单 |
| `get_orders(security=None)` | 当日本策略订单；约 6 秒同步 |
| `get_all_orders(security=None)` | 账户当日全部订单，包含非本交易订单 |
| `get_trades()` | 策略内当日成交详情 |

`get_all_orders` 配合 `cancel_order_ex` 可以处理手工委托单，但必须严格过滤账户、证券、方向和订单状态，不能把其他策略的订单误撤。

## 主推与轮询

- `on_order_response` 提供委托主推，通常快于 `get_order/get_orders`，部分柜台不支持。
- `on_trade_response` 提供成交主推，通常快于 `get_trades`。
- 主推与约 6 秒轮询会同时更新本地对象，状态机要允许重复事件和乱序事件。
- 回调内新下单可能再次触发回调，必须以订单意图 ID 和状态守卫防止递归下单。
- 柜台回报是最终事实，本地估算只能作为暂态。

## 安全执行状态机

```text
建议生成 -> 风控通过 -> 人工确认 -> 创建唯一意图
-> 委托已提交 -> 柜台受理/废单 -> 部成/全成/撤单
-> 盘后交割与资金流水核对 -> 审计完成
```

每一步保存 `intent_id/account/trade_date/symbol/side/amount/limit_price/source_rule/created_at/status/entrust_no/fill_qty`。重试只查询或推进同一意图，不创建重复订单。

## 本项目边界

当前项目以观察、分析、建议和风险提示为主，不自动下单。未来接入也要先完成：

1. 分析与执行进程隔离。
2. 人工确认和账户白名单。
3. 交易时段、停牌、涨跌停、数量、资金、持仓和精度校验。
4. 模拟环境长周期验证。
5. 委托/成交/交割/资金四方核对。
