# 证券、基本面、基金与可转债

## 证券基础信息

| 函数 | 作用 | 当前项目用途 |
| --- | --- | --- |
| `get_stock_name` | 批量获取股票、转债、ETF 等名称 | 代码规范化、展示和校验 |
| `get_stock_info` | 获取证券基础字段 | 上市状态、证券元数据 |
| `get_stock_status` | 查询 ST、停牌、退市等状态 | 活跃 A 股池、风控标签 |
| `filter_stock_by_status` | 按状态过滤股票代码 | 批量构建可研究池 |
| `get_underlying_code` | 获取关联代码 | 转债与正股、衍生品关联 |
| `get_stock_exrights` | 获取除权除息 | 复权验证和事件证据 |
| `get_stock_blocks` | 获取所属板块 | 热点、扩散与行业解释 |
| `get_index_stocks` | 获取指数成分股 | 基准、风格和候选池 |
| `get_industry_stocks` | 获取行业成分股 | 行业强弱与相对比较 |
| `get_Ashares` | 获取指定日期沪深 A 股列表 | 全市场分母与历史证券池 |

`get_Ashares` 和部分基本面接口是在线调用，回测时应按交易日缓存，不要在每根 K 线重复请求。

## A 股证券池流程

1. 使用 `get_Ashares(date)` 取得目标日沪深 A 股。
2. 查询 `DELISTING`、`DELISTING_SORTING`、`ST`、`HALT` 等状态。
3. 退市证券从活跃池排除；ST、停牌保留标签，由策略规则决定是否纳入。
4. 保存代码、名称、交易所、目标交易日、状态、获取时间和 PTrade 版本。
5. 与通达信/公开目录交叉核验，差异进入人工审计，不静默删除。

这样可以避免把历史失效代码纳入“当前全市场覆盖率”的分母。

## 财务与估值

`get_fundamentals(security, table, fields=None, date=None, start_year=None, end_year=None, report_types=None, merge_type=None, is_dataframe=False)` 支持：

- `valuation` 日频估值。
- `balance_statement` 资产负债表。
- `income_statement` 利润表。
- `cashflow_statement` 现金流量表。
- 成长、盈利、每股、营运、偿债等能力指标。

防未来数据规则：

- 回测优先 `merge_type=None`，使用首次发布数据。
- 研究/当前诊断在明确报告期后可使用更新合并模式，但必须记录查询日和发布日期。
- 官方标注成长、盈利、EPS、营运、偿债五类能力表为非 PIT 数据，不能直接用于无偏历史回测。
- `None`/`NaN` 表示无披露或无数据，不等于 0。
- 最新变更记录为部分三表新增字段；代码必须允许字段随版本扩展。

## ETF、IPO 与 REITs

| 函数 | 环境/柜台限制 | 内容 |
| --- | --- | --- |
| `get_etf_list` | PTrade 客户端股票交易；部分柜台不支持 | ETF 代码列表 |
| `get_etf_info` | 同上 | 单只或多只 ETF 信息 |
| `get_etf_stock_list` | 同上 | ETF 成分券列表 |
| `get_etf_stock_info` | 同上 | ETF 成分券信息 |
| `get_ipo_stocks` | PTrade 客户端股票交易；部分柜台不支持 | 当日 IPO 申购标的 |
| `get_reits_list` | 研究/回测/交易 | 指定日期公募 REITs 列表 |

这些能力先归档，当前产品不把 ETF/IPO/REITs 混入 A 股候选池。

## 可转债

### `get_cb_list`

- 仅交易模块可用。
- 返回当前可转债市场全部代码，包含停牌代码。
- 同一分钟多次调用可能返回本分钟首次查询缓存。
- 必须结合快照 `trade_status` 过滤或标记 `HALT/SUSP/STOPT/DELISTED`。

### `get_cb_info`

- 研究和交易模块可用。
- 可能需要券商单独提供可转债基础数据权限；失败或无权限返回空 DataFrame。
- 包含转债/正股代码名称、上市日、转股起始日、到期日、溢价率、转股比例、转股价和转股价值等。

### 交易语义

- 可转债回测按张，官方文档支持 T+0；交易具体单位必须咨询券商。
- 限价精度为三位小数。
- `order_market` 不支持可转债。
- `debt_to_stock_order` 用于转股；上海市场规则变更后传入可转债代码，而不是转股代码。

A 股与可转债要保留独立领域模型、候选池、风险规则和页面；只通过正股关联、板块和事件证据互相引用。
