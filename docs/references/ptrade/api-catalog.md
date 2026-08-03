# PTrade API 全量目录

> 共 149 个事件/函数。环境缩写：`R` 研究、`B` 回测、`T` 交易、`MT` 两融交易、`OT` 期权交易、`HK` 港股通交易。
> “现在”表示与当前 A 股/转债辅助决策项目相关；“后续”表示保留扩展能力；“归档”表示仅作兼容和知识储备。
> 柜台/客户端限制以官方锚点和目标账户实测为准。

## 生命周期（7）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`initialize`](https://ptrade.i618.com.cn:7766/hub/help/api#initialize) | `initialize(context)` | B/T | 初始化策略，必选 | 现在 |
| [`before_trading_start`](https://ptrade.i618.com.cn:7766/hub/help/api#before_trading_start) | `before_trading_start(context, data)` | B/T | 每日盘前准备 | 现在 |
| [`handle_data`](https://ptrade.i618.com.cn:7766/hub/help/api#handle_data) | `handle_data(context, data)` | B/T | 日/分钟主逻辑，必选 | 现在 |
| [`after_trading_end`](https://ptrade.i618.com.cn:7766/hub/help/api#after_trading_end) | `after_trading_end(context, data)` | B/T | 每日盘后处理 | 现在 |
| [`tick_data`](https://ptrade.i618.com.cn:7766/hub/help/api#tick_data) | `tick_data(context, data)` | T | 约 3 秒 Tick 回调 | 后续 |
| [`on_order_response`](https://ptrade.i618.com.cn:7766/hub/help/api#on_order_response) | `on_order_response(context, order_list)` | T | 委托主推 | 后续 |
| [`on_trade_response`](https://ptrade.i618.com.cn:7766/hub/help/api#on_trade_response) | `on_trade_response(context, trade_list)` | T | 成交主推 | 后续 |

## 设置（10）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`set_universe`](https://ptrade.i618.com.cn:7766/hub/help/api#set_universe) | `set_universe(security_list)` | B/T | 设置股票池 | 现在 |
| [`set_benchmark`](https://ptrade.i618.com.cn:7766/hub/help/api#set_benchmark) | `set_benchmark(sids)` | B/T | 设置评价基准 | 现在 |
| [`set_commission`](https://ptrade.i618.com.cn:7766/hub/help/api#set_commission) | `set_commission(commission_ratio=0.0003, min_commission=5.0, type='STOCK')` | B | 设置佣金 | 现在 |
| [`set_fixed_slippage`](https://ptrade.i618.com.cn:7766/hub/help/api#set_fixed_slippage) | `set_fixed_slippage(fixedslippage=0.0)` | B | 设置固定滑点 | 现在 |
| [`set_slippage`](https://ptrade.i618.com.cn:7766/hub/help/api#set_slippage) | `set_slippage(slippage=0.001)` | B | 设置比例滑点 | 现在 |
| [`set_volume_ratio`](https://ptrade.i618.com.cn:7766/hub/help/api#set_volume_ratio) | `set_volume_ratio(volume_ratio=0.25)` | B | 设置成交量比例 | 现在 |
| [`set_limit_mode`](https://ptrade.i618.com.cn:7766/hub/help/api#set_limit_mode) | `set_limit_mode(limit_mode='LIMIT')` | B | 设置成交数量限制模式 | 现在 |
| [`set_yesterday_position`](https://ptrade.i618.com.cn:7766/hub/help/api#set_yesterday_position) | `set_yesterday_position(poslist)` | B | 设置股票回测底仓 | 后续 |
| [`set_parameters`](https://ptrade.i618.com.cn:7766/hub/help/api#set_parameters) | `set_parameters(**kwargs)` | T | 设置交易策略参数 | 后续 |
| [`set_email_info`](https://ptrade.i618.com.cn:7766/hub/help/api#set_email_info) | `set_email_info(email_address, smtp_code, email_subject)` | T | 配置报错邮件 | 后续 |

## 调度（2）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`run_daily`](https://ptrade.i618.com.cn:7766/hub/help/api#run_daily) | `run_daily(context, func, time='9:31')` | B/T | 每日指定时点运行 | 现在 |
| [`run_interval`](https://ptrade.i618.com.cn:7766/hub/help/api#run_interval) | `run_interval(context, func, seconds=10, interval_timer_ranges='')` | T | 秒级周期运行 | 后续 |

## 交易日历（4）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`get_trading_day`](https://ptrade.i618.com.cn:7766/hub/help/api#get_trading_day) | `get_trading_day(day)` | R/B/T | 相对当前日期取交易日 | 现在 |
| [`get_all_trades_days`](https://ptrade.i618.com.cn:7766/hub/help/api#get_all_trades_days) | `get_all_trades_days(date=None)` | R/B/T | 获取历史全部交易日 | 现在 |
| [`get_trade_days`](https://ptrade.i618.com.cn:7766/hub/help/api#get_trade_days) | `get_trade_days(start_date=None, end_date=None, count=None)` | R/B/T | 获取范围交易日 | 现在 |
| [`get_trading_day_by_date`](https://ptrade.i618.com.cn:7766/hub/help/api#get_trading_day_by_date) | `get_trading_day_by_date(query_date, day=0)` | R/B/T | 按日期定位交易日 | 现在 |

## 市场目录（2）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`get_market_list`](https://ptrade.i618.com.cn:7766/hub/help/api#get_market_list) | `get_market_list()` | R/B/T | 市场目录 | 后续 |
| [`get_market_detail`](https://ptrade.i618.com.cn:7766/hub/help/api#get_market_detail) | `get_market_detail(finance_mic)` | R/B/T | 市场编码详情 | 后续 |

## 行情（9）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`get_history`](https://ptrade.i618.com.cn:7766/hub/help/api#get_history) | `get_history(count, frequency='1d', field='close', security_list=None, fq=None, include=False, fill='nan', is_dict=False)` | R/B/T | 最近 N 根历史行情 | 现在 |
| [`get_price`](https://ptrade.i618.com.cn:7766/hub/help/api#get_price) | `get_price(security, start_date=None, end_date=None, frequency='1d', fields=None, fq=None, count=None, is_dict=False)` | R/B/T | 区间/N 根历史行情 | 现在 |
| [`get_individual_entrust`](https://ptrade.i618.com.cn:7766/hub/help/api#get_individual_entrust) | `get_individual_entrust(stocks=None, data_count=50, start_pos=0, search_direction=1, is_dict=False)` | T/L2 | 当日逐笔委托 | 后续 |
| [`get_individual_transaction`](https://ptrade.i618.com.cn:7766/hub/help/api#get_individual_transaction) | `get_individual_transaction(stocks=None, data_count=50, start_pos=0, search_direction=1, is_dict=False)` | T/L2 | 当日逐笔成交 | 后续 |
| [`get_tick_direction`](https://ptrade.i618.com.cn:7766/hub/help/api#get_tick_direction) | `get_tick_direction(symbols=None, query_date=0, start_pos=0, search_direction=1, data_count=50, is_dict=False)` | T | 当日分时成交 | 后续 |
| [`get_sort_msg`](https://ptrade.i618.com.cn:7766/hub/help/api#get_sort_msg) | `get_sort_msg(sort_type_grp=None, sort_field_name=None, sort_type=1, data_count=100)` | T | 板块/行业快照排序 | 现在 |
| [`get_gear_price`](https://ptrade.i618.com.cn:7766/hub/help/api#get_gear_price) | `get_gear_price(sids)` | T | 档位行情价格 | 后续 |
| [`get_snapshot`](https://ptrade.i618.com.cn:7766/hub/help/api#get_snapshot) | `get_snapshot(security)` | T | 实时行情快照 | 现在 |
| [`get_trend_data`](https://ptrade.i618.com.cn:7766/hub/help/api#get_trend_data) | `get_trend_data(date=None, stocks=None, market=None)` | R/B/T | 集中竞价期间数据 | 现在 |

## 证券、财务和基金（18）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`get_stock_name`](https://ptrade.i618.com.cn:7766/hub/help/api#get_stock_name) | `get_stock_name(stocks)` | R/B/T | 证券名称 | 现在 |
| [`get_stock_info`](https://ptrade.i618.com.cn:7766/hub/help/api#get_stock_info) | `get_stock_info(stocks, field=None)` | R/B/T | 证券基础信息 | 现在 |
| [`get_stock_status`](https://ptrade.i618.com.cn:7766/hub/help/api#get_stock_status) | `get_stock_status(stocks, query_type='ST', query_date=None)` | R/B/T | ST、停牌、退市状态 | 现在 |
| [`get_underlying_code`](https://ptrade.i618.com.cn:7766/hub/help/api#get_underlying_code) | `get_underlying_code(symbols)` | T | 关联标的代码 | 现在 |
| [`get_stock_exrights`](https://ptrade.i618.com.cn:7766/hub/help/api#get_stock_exrights) | `get_stock_exrights(stock_code, date=None)` | R/B/T | 除权除息信息 | 现在 |
| [`get_stock_blocks`](https://ptrade.i618.com.cn:7766/hub/help/api#get_stock_blocks) | `get_stock_blocks(stock_code)` | R/B/T | 所属板块 | 现在 |
| [`get_index_stocks`](https://ptrade.i618.com.cn:7766/hub/help/api#get_index_stocks) | `get_index_stocks(index_code, date)` | R/B/T | 指数成分股 | 现在 |
| [`get_industry_stocks`](https://ptrade.i618.com.cn:7766/hub/help/api#get_industry_stocks) | `get_industry_stocks(industry_code)` | R/B/T | 行业成分股 | 现在 |
| [`get_fundamentals`](https://ptrade.i618.com.cn:7766/hub/help/api#get_fundamentals) | `get_fundamentals(security, table, fields=None, date=None, start_year=None, end_year=None, report_types=None, merge_type=None, is_dataframe=False)` | R/B/T | 财务、估值和能力指标 | 现在 |
| [`get_Ashares`](https://ptrade.i618.com.cn:7766/hub/help/api#get_Ashares) | `get_Ashares(date=None)` | R/B/T | 指定日期沪深 A 股 | 现在 |
| [`get_etf_list`](https://ptrade.i618.com.cn:7766/hub/help/api#get_etf_list) | `get_etf_list()` | T/客户端 | ETF 列表 | 后续 |
| [`get_etf_info`](https://ptrade.i618.com.cn:7766/hub/help/api#get_etf_info) | `get_etf_info(etf_code)` | T/客户端 | ETF 信息 | 后续 |
| [`get_etf_stock_list`](https://ptrade.i618.com.cn:7766/hub/help/api#get_etf_stock_list) | `get_etf_stock_list(etf_code)` | T/客户端 | ETF 成分券列表 | 后续 |
| [`get_etf_stock_info`](https://ptrade.i618.com.cn:7766/hub/help/api#get_etf_stock_info) | `get_etf_stock_info(etf_code, security)` | T/客户端 | ETF 成分券信息 | 后续 |
| [`get_ipo_stocks`](https://ptrade.i618.com.cn:7766/hub/help/api#get_ipo_stocks) | `get_ipo_stocks()` | T/客户端 | 当日 IPO 申购标的 | 后续 |
| [`get_cb_list`](https://ptrade.i618.com.cn:7766/hub/help/api#get_cb_list) | `get_cb_list()` | T | 可转债市场列表（含停牌） | 现在 |
| [`get_cb_info`](https://ptrade.i618.com.cn:7766/hub/help/api#get_cb_info) | `get_cb_info()` | R/T | 可转债基础信息 | 现在 |
| [`get_reits_list`](https://ptrade.i618.com.cn:7766/hub/help/api#get_reits_list) | `get_reits_list(date=None)` | R/B/T | 公募 REITs 列表 | 后续 |

## 持仓与账户历史（11）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`get_position`](https://ptrade.i618.com.cn:7766/hub/help/api#get_position) | `get_position(security)` | B/T | 单标的持仓 | 后续 |
| [`get_positions`](https://ptrade.i618.com.cn:7766/hub/help/api#get_positions) | `get_positions(security)` | B/T | 多标的持仓 | 后续 |
| [`get_all_positions`](https://ptrade.i618.com.cn:7766/hub/help/api#get_all_positions) | `get_all_positions()` | T | 账户全部持仓 | 后续 |
| [`get_trades_file`](https://ptrade.i618.com.cn:7766/hub/help/api#get_trades_file) | `get_trades_file(save_path='')` | B | 回测对账文件 | 现在 |
| [`convert_position_from_csv`](https://ptrade.i618.com.cn:7766/hub/help/api#convert_position_from_csv) | `convert_position_from_csv(path)` | B | CSV 转底仓参数 | 后续 |
| [`get_user_name`](https://ptrade.i618.com.cn:7766/hub/help/api#get_user_name) | `get_user_name(login_account=True)` | B/T | 资金账号 | 后续 |
| [`get_deliver`](https://ptrade.i618.com.cn:7766/hub/help/api#get_deliver) | `get_deliver(start_date, end_date)` | T/盘前盘后 | 历史交割单 | 后续 |
| [`get_fundjour`](https://ptrade.i618.com.cn:7766/hub/help/api#get_fundjour) | `get_fundjour(start_date, end_date)` | T/盘前盘后 | 历史资金流水 | 后续 |
| [`get_research_path`](https://ptrade.i618.com.cn:7766/hub/help/api#get_research_path) | `get_research_path()` | B/T | 研究根路径 | 现在 |
| [`get_trade_name`](https://ptrade.i618.com.cn:7766/hub/help/api#get_trade_name) | `get_trade_name()` | T | 当前交易名称 | 后续 |
| [`get_lucky_info`](https://ptrade.i618.com.cn:7766/hub/help/api#get_lucky_info) | `get_lucky_info(start_date, end_date)` | T | 历史中签信息 | 后续 |

## 股票与公共交易（19）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`order`](https://ptrade.i618.com.cn:7766/hub/help/api#order) | `order(security, amount, limit_price=None)` | B/T | 按数量买卖 | 后续 |
| [`order_target`](https://ptrade.i618.com.cn:7766/hub/help/api#order_target) | `order_target(security, amount, limit_price=None)` | B/T | 调整到目标数量 | 后续 |
| [`order_value`](https://ptrade.i618.com.cn:7766/hub/help/api#order_value) | `order_value(security, value, limit_price=None)` | B/T | 按价值买卖 | 后续 |
| [`order_target_value`](https://ptrade.i618.com.cn:7766/hub/help/api#order_target_value) | `order_target_value(security, value, limit_price=None)` | B/T | 调整到目标市值 | 后续 |
| [`order_market`](https://ptrade.i618.com.cn:7766/hub/help/api#order_market) | `order_market(security, amount, market_type, limit_price=None)` | T | 市价委托；不支持转债 | 后续 |
| [`ipo_stocks_order`](https://ptrade.i618.com.cn:7766/hub/help/api#ipo_stocks_order) | `ipo_stocks_order(submarket_type=None, black_stocks=None)` | T | 新股一键申购 | 后续 |
| [`after_trading_order`](https://ptrade.i618.com.cn:7766/hub/help/api#after_trading_order) | `after_trading_order(security, amount, entrust_price)` | T/客户端 | 盘后固定价委托 | 后续 |
| [`after_trading_cancel_order`](https://ptrade.i618.com.cn:7766/hub/help/api#after_trading_cancel_order) | `after_trading_cancel_order(order_param)` | T/客户端 | 盘后固定价撤单 | 后续 |
| [`etf_basket_order`](https://ptrade.i618.com.cn:7766/hub/help/api#etf_basket_order) | `etf_basket_order(etf_code, amount, price_style=None, position=True, info=None)` | T/客户端 | ETF 篮子下单 | 归档 |
| [`etf_purchase_redemption`](https://ptrade.i618.com.cn:7766/hub/help/api#etf_purchase_redemption) | `etf_purchase_redemption(etf_code, amount, limit_price=None)` | T/客户端 | ETF 申赎 | 归档 |
| [`order_tick`](https://ptrade.i618.com.cn:7766/hub/help/api#order_tick) | `order_tick(sid, amount, priceGear='1', limit_price=None)` | T | Tick 档位委托 | 后续 |
| [`cancel_order`](https://ptrade.i618.com.cn:7766/hub/help/api#cancel_order) | `cancel_order(order_param)` | B/T | 撤单 | 后续 |
| [`cancel_order_ex`](https://ptrade.i618.com.cn:7766/hub/help/api#cancel_order_ex) | `cancel_order_ex(order_param)` | T | 撤账户订单 | 后续 |
| [`debt_to_stock_order`](https://ptrade.i618.com.cn:7766/hub/help/api#debt_to_stock_order) | `debt_to_stock_order(security, amount)` | T | 可转债转股 | 后续 |
| [`get_open_orders`](https://ptrade.i618.com.cn:7766/hub/help/api#get_open_orders) | `get_open_orders(security=None)` | B/T | 未完成订单 | 后续 |
| [`get_order`](https://ptrade.i618.com.cn:7766/hub/help/api#get_order) | `get_order(order_id)` | B/T | 指定订单 | 后续 |
| [`get_orders`](https://ptrade.i618.com.cn:7766/hub/help/api#get_orders) | `get_orders(security=None)` | B/T | 本策略全部订单 | 后续 |
| [`get_all_orders`](https://ptrade.i618.com.cn:7766/hub/help/api#get_all_orders) | `get_all_orders(security=None)` | T | 账户当日全部订单 | 后续 |
| [`get_trades`](https://ptrade.i618.com.cn:7766/hub/help/api#get_trades) | `get_trades()` | B/T | 当日成交 | 后续 |

## 融资融券（20）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`margin_trade`](https://ptrade.i618.com.cn:7766/hub/help/api#margin_trade) | `margin_trade(security, amount, limit_price=None, market_type=None)` | MB/MT | 担保品买卖 | 归档 |
| [`margincash_open`](https://ptrade.i618.com.cn:7766/hub/help/api#margincash_open) | `margincash_open(security, amount, limit_price=None, market_type=None, cash_group=None)` | MT | 融资买入 | 归档 |
| [`margincash_close`](https://ptrade.i618.com.cn:7766/hub/help/api#margincash_close) | `margincash_close(security, amount, limit_price=None, market_type=None, cash_group=None)` | MT | 卖券还款 | 归档 |
| [`margincash_direct_refund`](https://ptrade.i618.com.cn:7766/hub/help/api#margincash_direct_refund) | `margincash_direct_refund(value, cash_group=None)` | MT | 直接还款 | 归档 |
| [`marginsec_open`](https://ptrade.i618.com.cn:7766/hub/help/api#marginsec_open) | `marginsec_open(security, amount, limit_price=None, cash_group=None)` | MT | 融券卖出 | 归档 |
| [`marginsec_close`](https://ptrade.i618.com.cn:7766/hub/help/api#marginsec_close) | `marginsec_close(security, amount, limit_price=None, market_type=None, cash_group=None)` | MT | 买券还券 | 归档 |
| [`marginsec_direct_refund`](https://ptrade.i618.com.cn:7766/hub/help/api#marginsec_direct_refund) | `marginsec_direct_refund(security, amount, cash_group=None)` | MT | 直接还券 | 归档 |
| [`get_margincash_stocks`](https://ptrade.i618.com.cn:7766/hub/help/api#get_margincash_stocks) | `get_margincash_stocks()` | MT | 融资标的 | 归档 |
| [`get_marginsec_stocks`](https://ptrade.i618.com.cn:7766/hub/help/api#get_marginsec_stocks) | `get_marginsec_stocks()` | MT | 融券标的 | 归档 |
| [`get_margin_contract`](https://ptrade.i618.com.cn:7766/hub/help/api#get_margin_contract) | `get_margin_contract(compact_source=None)` | MT | 两融合约 | 归档 |
| [`get_margin_contractreal`](https://ptrade.i618.com.cn:7766/hub/help/api#get_margin_contractreal) | `get_margin_contractreal()` | MT | 实时合约流水 | 归档 |
| [`get_margin_asset`](https://ptrade.i618.com.cn:7766/hub/help/api#get_margin_asset) | `get_margin_asset()` | MT | 信用资产 | 归档 |
| [`get_assure_security_list`](https://ptrade.i618.com.cn:7766/hub/help/api#get_assure_security_list) | `get_assure_security_list()` | MT | 担保券 | 归档 |
| [`get_margincash_open_amount`](https://ptrade.i618.com.cn:7766/hub/help/api#get_margincash_open_amount) | `get_margincash_open_amount(security, price=None, cash_group=None)` | MT | 融资最大可买 | 归档 |
| [`get_margincash_close_amount`](https://ptrade.i618.com.cn:7766/hub/help/api#get_margincash_close_amount) | `get_margincash_close_amount(security, price=None, cash_group=None)` | MT | 卖券还款最大可卖 | 归档 |
| [`get_marginsec_open_amount`](https://ptrade.i618.com.cn:7766/hub/help/api#get_marginsec_open_amount) | `get_marginsec_open_amount(security, price=None, cash_group=None)` | MT | 融券最大可卖 | 归档 |
| [`get_marginsec_close_amount`](https://ptrade.i618.com.cn:7766/hub/help/api#get_marginsec_close_amount) | `get_marginsec_close_amount(security, price=None, cash_group=None)` | MT | 买券还券最大可买 | 归档 |
| [`get_margin_entrans_amount`](https://ptrade.i618.com.cn:7766/hub/help/api#get_margin_entrans_amount) | `get_margin_entrans_amount(security, cash_group=None)` | MT | 现券还券数量 | 归档 |
| [`get_enslo_security_info`](https://ptrade.i618.com.cn:7766/hub/help/api#get_enslo_security_info) | `get_enslo_security_info(cash_group=None)` | MT | 融券信息 | 归档 |
| [`get_crdt_fund`](https://ptrade.i618.com.cn:7766/hub/help/api#get_crdt_fund) | `get_crdt_fund(cash_group=None)` | MT | 可融资金 | 归档 |

## 期货（9）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`buy_open`](https://ptrade.i618.com.cn:7766/hub/help/api#buy_open) | `buy_open(contract, amount, limit_price=None)` | B/T | 多开 | 归档 |
| [`sell_close`](https://ptrade.i618.com.cn:7766/hub/help/api#sell_close) | `sell_close(contract, amount, limit_price=None, close_today=False)` | B/T | 多平 | 归档 |
| [`sell_open`](https://ptrade.i618.com.cn:7766/hub/help/api#sell_open) | `sell_open(contract, amount, limit_price=None)` | B/T | 空开 | 归档 |
| [`buy_close`](https://ptrade.i618.com.cn:7766/hub/help/api#buy_close) | `buy_close(contract, amount, limit_price=None, close_today=False)` | B/T | 空平 | 归档 |
| [`get_margin_rate`](https://ptrade.i618.com.cn:7766/hub/help/api#get_margin_rate) | `get_margin_rate(transaction_code)` | B | 保证金比例 | 归档 |
| [`get_instruments`](https://ptrade.i618.com.cn:7766/hub/help/api#get_instruments) | `get_instruments(contract)` | B/T | 合约信息 | 归档 |
| [`get_dominant_contract`](https://ptrade.i618.com.cn:7766/hub/help/api#get_dominant_contract) | `get_dominant_contract(contract, date=None)` | R/B/T | 主力合约 | 归档 |
| [`set_future_commission`](https://ptrade.i618.com.cn:7766/hub/help/api#set_future_commission) | `set_future_commission(transaction_code, commission)` | B | 期货手续费 | 归档 |
| [`set_margin_rate`](https://ptrade.i618.com.cn:7766/hub/help/api#set_margin_rate) | `set_margin_rate(transaction_code, margin_rate)` | B | 回测保证金比例 | 归档 |

## 期权（15）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`get_opt_objects`](https://ptrade.i618.com.cn:7766/hub/help/api#get_opt_objects) | `get_opt_objects(date=None)` | R/B/T | 期权标的列表 | 归档 |
| [`get_opt_last_dates`](https://ptrade.i618.com.cn:7766/hub/help/api#get_opt_last_dates) | `get_opt_last_dates(security, date=None)` | R/B/T | 到期日列表 | 归档 |
| [`get_opt_contracts`](https://ptrade.i618.com.cn:7766/hub/help/api#get_opt_contracts) | `get_opt_contracts(security, date=None)` | R/B/T | 合约列表 | 归档 |
| [`get_contract_info`](https://ptrade.i618.com.cn:7766/hub/help/api#get_contract_info) | `get_contract_info(contract)` | R/B/T | 期权合约信息 | 归档 |
| [`get_covered_lock_amount`](https://ptrade.i618.com.cn:7766/hub/help/api#get_covered_lock_amount) | `get_covered_lock_amount(code)` | T | 可备兑锁定数量 | 归档 |
| [`get_covered_unlock_amount`](https://ptrade.i618.com.cn:7766/hub/help/api#get_covered_unlock_amount) | `get_covered_unlock_amount(code)` | T | 可备兑解锁数量 | 归档 |
| [`option_buy_open`](https://ptrade.i618.com.cn:7766/hub/help/api#option_buy_open) | `option_buy_open(contract, amount, limit_price=None)` | B/T | 权利仓开仓 | 归档 |
| [`option_sell_close`](https://ptrade.i618.com.cn:7766/hub/help/api#option_sell_close) | `option_sell_close(contract, amount, limit_price=None)` | B/T | 权利仓平仓（官网标题存在历史措辞差异） | 归档 |
| [`option_sell_open`](https://ptrade.i618.com.cn:7766/hub/help/api#option_sell_open) | `option_sell_open(contract, amount, limit_price=None)` | B/T | 义务仓开仓 | 归档 |
| [`option_buy_close`](https://ptrade.i618.com.cn:7766/hub/help/api#option_buy_close) | `option_buy_close(contract, amount, limit_price=None)` | B/T | 义务仓平仓 | 归档 |
| [`open_prepared`](https://ptrade.i618.com.cn:7766/hub/help/api#open_prepared) | `open_prepared(contract, amount, limit_price=None)` | T | 备兑开仓 | 归档 |
| [`close_prepared`](https://ptrade.i618.com.cn:7766/hub/help/api#close_prepared) | `close_prepared(contract, amount, limit_price=None)` | T | 备兑平仓 | 归档 |
| [`option_exercise`](https://ptrade.i618.com.cn:7766/hub/help/api#option_exercise) | `option_exercise(contract, amount)` | T | 行权 | 归档 |
| [`option_covered_lock`](https://ptrade.i618.com.cn:7766/hub/help/api#option_covered_lock) | `option_covered_lock(code, amount)` | T | 标的备兑锁定 | 归档 |
| [`option_covered_unlock`](https://ptrade.i618.com.cn:7766/hub/help/api#option_covered_unlock) | `option_covered_unlock(code, amount)` | T | 标的备兑解锁 | 归档 |

## 港股通（5）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`get_hks_list`](https://ptrade.i618.com.cn:7766/hub/help/api#get_hks_list) | `get_hks_list(market)` | HK/客户端 | 港股通代码 | 归档 |
| [`get_hks_price_gap`](https://ptrade.i618.com.cn:7766/hub/help/api#get_hks_price_gap) | `get_hks_price_gap()` | T | 港股通价差 | 归档 |
| [`get_hks_unit_amount`](https://ptrade.i618.com.cn:7766/hub/help/api#get_hks_unit_amount) | `get_hks_unit_amount(security, trade_type)` | T | 委托单位数量 | 归档 |
| [`hks_order`](https://ptrade.i618.com.cn:7766/hub/help/api#hks_order) | `hks_order(security, amount, limit_price=None, style=None)` | HK/客户端 | 港股通买卖 | 归档 |
| [`hks_odd_lot_order`](https://ptrade.i618.com.cn:7766/hub/help/api#hks_odd_lot_order) | `hks_odd_lot_order(security, amount, limit_price=None)` | HK/客户端 | 零股卖出 | 归档 |

## 技术指标（4）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`get_MACD`](https://ptrade.i618.com.cn:7766/hub/help/api#get_MACD) | `get_MACD(close, short=12, long=26, m=9)` | B/T | MACD | 现在 |
| [`get_KDJ`](https://ptrade.i618.com.cn:7766/hub/help/api#get_KDJ) | `get_KDJ(high, low, close, n=9, m1=3, m2=3)` | B/T | KDJ | 现在 |
| [`get_RSI`](https://ptrade.i618.com.cn:7766/hub/help/api#get_RSI) | `get_RSI(close, n=6)` | B/T | RSI | 现在 |
| [`get_CCI`](https://ptrade.i618.com.cn:7766/hub/help/api#get_CCI) | `get_CCI(close, n=14)` | B/T | CCI | 现在 |

## 工具与资金调拨（14）

| API | 签名 | 环境 | 用途 | 优先级 |
| --- | --- | --- | --- | --- |
| [`log`](https://ptrade.i618.com.cn:7766/hub/help/api#log) | `log(content)` | B/T | 日志 | 现在 |
| [`is_trade`](https://ptrade.i618.com.cn:7766/hub/help/api#is_trade) | `is_trade()` | B/T | 判断回测/交易场景 | 现在 |
| [`check_limit`](https://ptrade.i618.com.cn:7766/hub/help/api#check_limit) | `check_limit(security, query_date=None)` | R/B/T | 涨跌停判断 | 现在 |
| [`send_email`](https://ptrade.i618.com.cn:7766/hub/help/api#send_email) | `send_email(send_email_info, get_email_info, smtp_code, info='', path='', subject='')` | T | 邮件推送 | 后续 |
| [`send_qywx`](https://ptrade.i618.com.cn:7766/hub/help/api#send_qywx) | `send_qywx(corp_id, secret, agent_id, info='', path='', toparty='', touser='', totag='')` | T | 企业微信推送 | 后续 |
| [`permission_test`](https://ptrade.i618.com.cn:7766/hub/help/api#permission_test) | `permission_test(account=None, end_date=None)` | T | 账户和有效期权限校验 | 后续 |
| [`create_dir`](https://ptrade.i618.com.cn:7766/hub/help/api#create_dir) | `create_dir(user_path)` | R/B/T | 创建研究子目录 | 现在 |
| [`get_frequency`](https://ptrade.i618.com.cn:7766/hub/help/api#get_frequency) | `get_frequency()` | B/T | 当前周期 | 现在 |
| [`get_business_type`](https://ptrade.i618.com.cn:7766/hub/help/api#get_business_type) | `get_business_type()` | B/T | 当前业务类型 | 现在 |
| [`get_current_kline_count`](https://ptrade.i618.com.cn:7766/hub/help/api#get_current_kline_count) | `get_current_kline_count()` | R/B/T | 当前分钟 K 线数量 | 现在 |
| [`filter_stock_by_status`](https://ptrade.i618.com.cn:7766/hub/help/api#filter_stock_by_status) | `filter_stock_by_status(stocks, filter_type=['ST', 'HALT', 'DELISTING'], query_date=None)` | R/B/T | 按状态过滤股票 | 现在 |
| [`check_strategy`](https://ptrade.i618.com.cn:7766/hub/help/api#check_strategy) | `check_strategy(strategy_content=None, strategy_path=None)` | R | 检查升级兼容性 | 现在 |
| [`fund_transfer`](https://ptrade.i618.com.cn:7766/hub/help/api#fund_transfer) | `fund_transfer(trans_direction, occur_balance, exchange_type='1')` | T/特定柜台 | 资金调拨 | 归档 |
| [`market_fund_transfer`](https://ptrade.i618.com.cn:7766/hub/help/api#market_fund_transfer) | `market_fund_transfer(exchange_type, occur_balance)` | T/特定柜台 | 市场间资金调拨 | 归档 |

## 覆盖校验

分组计数：`7 + 10 + 2 + 4 + 2 + 9 + 18 + 11 + 19 + 20 + 9 + 15 + 5 + 4 + 14 = 149`。

公共对象和数据字典不重复计入本表，见 `07-objects-and-data-dictionaries.md`。
