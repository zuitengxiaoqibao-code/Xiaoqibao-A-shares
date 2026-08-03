# 两融与后续市场能力

本项目当前只做 A 股和独立可转债。两融、期货、期权、港股通仍完整归档，状态统一为“后续/未接入”，防止未来扩展时重新调查，也防止当前误用。

## 融资融券

### 交易函数

| 函数 | 作用 |
| --- | --- |
| `margin_trade` | 担保品买卖；两融回测/交易 |
| `margincash_open` | 融资买入 |
| `margincash_close` | 卖券还款 |
| `margincash_direct_refund` | 直接还款 |
| `marginsec_open` | 融券卖出 |
| `marginsec_close` | 买券还券 |
| `marginsec_direct_refund` | 直接还券 |

除 `margin_trade` 外，大部分只在 PTrade 客户端两融交易模块可用。`cash_group` 区分核心、普通和专项业务头寸。

### 查询函数

| 函数 | 作用 |
| --- | --- |
| `get_margincash_stocks` | 融资标的列表 |
| `get_marginsec_stocks` | 融券标的列表 |
| `get_margin_contract` | 合约查询 |
| `get_margin_contractreal` | 实时合约流水 |
| `get_margin_asset` | 信用资产 |
| `get_assure_security_list` | 担保券列表 |
| `get_margincash_open_amount` | 融资最大可买数量 |
| `get_margincash_close_amount` | 卖券还款最大可卖数量 |
| `get_marginsec_open_amount` | 融券最大可卖数量 |
| `get_marginsec_close_amount` | 买券还券最大可买数量 |
| `get_margin_entrans_amount` | 现券还券数量 |
| `get_enslo_security_info` | 融券信息 |
| `get_crdt_fund` | 可融资金信息 |

这些接口受客户端版本和柜台差异影响明显。接入前应以 `permission_test` 和目标账户实测为准。

## 期货（归档）

交易：`buy_open` 多开、`sell_close` 多平、`sell_open` 空开、`buy_close` 空平。

查询：`get_margin_rate`、`get_instruments`、`get_dominant_contract`。

设置：`set_future_commission`、`set_margin_rate`。

重要语义：

- 期货持仓按多头/空头分开，包含今仓、可用量、保证金、浮盈亏、合约乘数和交割日。
- 平仓接口包含 `close_today` 语义，不能用股票式正负数量模型替代。
- 当前项目明确不看期货，所有期货接口仅用于历史策略兼容和未来架构预留。

## 期权（归档）

查询：

- `get_opt_objects`：期权标的列表。
- `get_opt_last_dates`：标的到期日。
- `get_opt_contracts`：挂牌合约列表。
- `get_contract_info`：合约信息。
- `get_covered_lock_amount`、`get_covered_unlock_amount`：备兑锁定/解锁数量。

交易：

- `option_buy_open`、`option_sell_close`、`option_sell_open`、`option_buy_close`。
- `open_prepared`、`close_prepared`：备兑开平仓。
- `option_exercise`：到期日行权。
- `option_covered_lock`、`option_covered_unlock`：现货标的备兑锁定/解锁。

字典中 `opthold_type` 区分权利方、义务方、备兑方，`option_type` 区分看涨/看跌。当前项目不启用。

## 港股通（归档）

| 函数 | 作用 |
| --- | --- |
| `get_hks_list(market)` | 港股通代码列表 |
| `get_hks_price_gap()` | 不同价格区间的最小价差 |
| `get_hks_unit_amount(security, trade_type)` | 每手/委托单位数量 |
| `hks_order` | 港股通买卖 |
| `hks_odd_lot_order` | 零股卖出 |

港股每只标的的交易单位不同，必须先查委托单位和价差。当前项目不启用。

## 资金调拨（高风险归档）

- `fund_transfer(trans_direction, occur_balance, exchange_type='1')`：UF20 与极速柜台/双中心资金调拨。
- `market_fund_transfer(exchange_type, occur_balance)`：极速柜台双中心资金调拨。

两者只在特定股票交易柜台场景使用，属于高风险外部状态变更。项目不得在没有券商书面说明、账户白名单、双人确认和审计日志时调用。
