# 对象字段与数据字典

## 公共对象

### `g`

回测/交易全局对象，用于跨回调保存用户状态。只保存可序列化且非 `__` 前缀的字段。不可把它当成唯一审计存储。

### `Context`

| 字段 | 含义 |
| --- | --- |
| `capital_base` | 起始资金 |
| `previous_date` | 前一交易日 |
| `sim_params` | 模拟参数对象，含起始资金和数据频率 |
| `portfolio` | `Portfolio` 账户信息 |
| `initialized` | 是否完成初始化 |
| `slippage` | 滑点对象 |
| `volume_limit` | 成交限量 |
| `price_impact` | 价格影响参数 |
| `commission` | 佣金对象，含印花税、佣金、最低佣金 |
| `blotter` | 记录对象；含当前时间 |
| `current_dt` | 当前周期开始时间，北京时间 |
| `recorded_vars` | 收益曲线记录值 |

### `BarData`

字段：`symbol/name/dt/is_open/open/close/price/low/high/volume/money/preclose/high_limit/low_limit/unlimited/datetime`。

分钟频率中 `preclose/high_limit/low_limit/unlimited` 填 `0.0`；同一周期重复调用返回首次在线查询的缓存。

### `Portfolio`

股票账户字段：`cash/positions/portfolio_value/positions_value/capital_used/returns/pnl/start_date`。

期货账户另有 `margin`。交易中默认约 6 秒同步一次，更新时间范围从盘前到盘后。

### `Position`

股票字段：`sid/enable_amount/amount/last_sale_price/cost_basis/today_amount/business_type/update_time`。

期货另有：`short_enable_amount/long_enable_amount/today_short_amount/today_long_amount/long_cost_basis/short_cost_basis/long_amount/short_amount/long_pnl/short_pnl/delivery_date/margin/contract_multiplier`。

交易中的 `update_time` 是最近柜台同步时间；回测返回 `None`。

### `Order`

股票字段：`id/dt/limit/symbol/amount/created/filled/entrust_no/cancel_entrust_no/priceGear/status`。

期货另有 `side/action/entrust_direction`。回测中的 `entrust_no` 和 `cancel_entrust_no` 为 `None`。交易对象由周期查询和后台主推共同更新。

代码后缀注意：`Order.symbol` 可能返回四位 `.XSHG/.XSHE`，桥接层需兼容 `.SS/.SZ`。

## 数据字典

### `status` 委托状态

`0` 未报；`1` 待报；`2` 已报；`3` 已报待撤；`4` 部成待撤；`5` 部撤；`6` 已撤；`7` 部成；`8` 已成；`9` 废单；`+` 已受理；`-` 已确认；`C` 正报；`V` 已确认。

### `entrust_type` 委托类别

`0` 委托；`2` 撤单；`4` 确认；`6` 信用融资；`7` 信用融券；`9` 信用交易。

### `entrust_prop` 委托属性

`0` 买卖；`1` 配股；`3` 申购；`4` 回购；`7` 转股；`9` 股息；`N` ETF 申赎；`Q` 对手方最优；`R` 五档即时成交剩余转限价；`S` 本方最优；`T` 即时成交剩余撤销；`U` 五档即时成交剩余撤销；`V` 全成交或撤销；`b` 定价；`c` 确认；`d` 限价；`HKN` 港股订单；`HKO` 港股零股订单。

### `business_direction` 成交方向

`0` 卖；`1` 买；`2` 借入；`3` 出借。

### `trans_kind` 委托类型

深圳：`1` 市价、`2` 限价、`3` 本方最优。上海：`4` 增加订单、`5` 删除订单。

### `trade_status` 交易状态

| 值 | 含义 |
| --- | --- |
| `START` | 市场启动，初始化后、集合竞价前 |
| `PRETR` | 盘前 |
| `OCALL` | 开始集合竞价 |
| `TRADE` | 连续撮合交易 |
| `HALT` | 暂停交易 |
| `SUSP` | 停盘 |
| `BREAK` | 休市 |
| `POSTR` | 盘后 |
| `ENDTR` | 交易结束 |
| `STOPT` | 长期停盘 |
| `DELISTED` | 退市 |
| `POSMT` | 盘后交易 |
| `PCALL` | 盘后集合竞价 |
| `INIT` | 盘后固定价格启动前 |
| `ENDPT` | 盘后固定价格闭市 |
| `POSSP` | 盘后固定价格停牌 |

### 逐笔与方向

- `trans_flag`：`0` 普通成交，`1` 撤单成交。
- `trans_identify_am`：`0` 盘中，`1` 盘后。
- `entrust_bs`：`1` 买，`2` 卖。

### `cash_replace_flag` ETF 现金替代

`0` 禁止；`1` 允许；`2` 必须；`3` 非沪市退补；`4` 非沪市必须；`5` 非沪深退补；`6` 非沪深必须。

### `exchange_type/futu_exch_type` 交易类别

`0` 资金；`1` 上海；`2` 深圳；`9` 特转 A；`A` 特转 B；`D` 沪 B；`G` 沪港通；`H` 深 B；`Q` 青岛产权；`S` 深港通；`T` 场外 OTC；`U` 转融通；`J` 金华基金；`K` 香港；`X` 固定收益；`F1` 郑州期货；`F2` 大连期货；`F3` 上海期货；`F4` 金融期货；`F5` 能源；`Z1` 业务受理；`R` H 股全流通。

### 证券、期货和期权

- `delist_flag`：`0` 正常，`1` 退市。
- `hedge_type`：`0` 投机，`1` 套保，`2` 套利，`3` 做市商，`4` 备兑。
- `opthold_type`：`0` 权利方，`1` 义务方，`2` 备兑方。
- `option_type`：`C` 看涨，`P` 看跌。

### `market_type` 市价委托类型

`0` 对手方最优；`1` 五档即时成交剩余转限价；`2` 本方最优；`3` 即时成交剩余撤销；`4` 五档即时成交剩余撤销；`5` 全额成交或撤单。

### `submarket_type` 申购市场

`0` 上证普通；`1` 科创板；`2` 深证普通；`3` 创业板；`4` 可转债。

### 两融合约

- `cash_group`：`0` 核心，`1` 普通业务，`2` 专项业务。
- `compact_type`：`0` 融资，`1` 融券，`2` 其他负债。
- `compact_status`：`0` 开仓未归还，`1` 部分归还，`2` 合约过期，`3` 客户自行归还，`4` 手工了结，`5` 未形成负债。

### `underlying_type` 关联类型

`0` A 股；`1` B 股；`2` H 股；`3` 期货；`4` 期权；`5` 港股认购；`6` 港股认沽；`7` 牛证；`8` 熊证；`9` 界内证；`10` 英股；`11` 美股；`12` 股本认股权证认购；`13` 股本认股权证认沽；`14` 正股关联可转债；`15` 可转债关联正股。

### 成交结果

- `real_type`：`0` 买卖，`1` 查询，`2` 撤单，`6` 融资，`7` 融券，`8` 平仓，`9` 信用，`G` 期权强平。
- `real_status`：`0` 成交，`2` 废单，`4` 确认。

官方入口：[公共资源](https://ptrade.i618.com.cn:7766/hub/help/api#公共资源)。
