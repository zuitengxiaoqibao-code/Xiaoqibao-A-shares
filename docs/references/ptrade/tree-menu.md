# PTrade 左侧知识树镜像

> 来源：https://ptrade.i618.com.cn:7766/hub/help/api
> 页面主知识树：10 个一级章节、49 个三级分组、178 个归一化四级知识条目。

## 1. 使用说明

1. 新建策略
2. 新建回测
3. 新建交易
4. 策略运行周期
5. 策略运行时间
6. 交易策略委托下单时间
7. 回测支持业务类型
8. 交易支持业务类型
9. 交易标的对应最小价差

本地归档：`01-platform-and-lifecycle.md`、`02-settings-and-scheduling.md`。

## 2. 开始写策略

1. 简单但是完整的策略
2. 添加一些交易
3. 实用的策略
4. 模拟盘和实盘注意事项（含持久化）
5. 策略中支持的代码尾缀
6. 关于异常处理
7. 关于限价交易的价格

本地归档：`01-platform-and-lifecycle.md`、`08-runtime-libraries-examples-and-changelog.md`。

## 3. 策略引擎简介

1. 业务流程框架

四级条目：`initialize/before_trading_start/handle_data/after_trading_end/tick_data/on_order_response/on_trade_response`。

## 4. 策略 API 介绍

1. 设置函数
2. 定时周期性函数
3. 获取信息函数
4. 获取基础信息
5. 获取市场信息
6. 获取行情信息
7. 获取证券信息
8. 获取其他信息
9. 交易相关函数
10. 股票交易函数
11. 公共交易函数
12. 融资融券专用函数
13. 融资融券交易类函数
14. 融资融券查询类函数
15. 期货专用函数
16. 期货交易类函数
17. 期货查询类函数
18. 期货设置类函数
19. 期权专用函数
20. 期权查询类函数
21. 期权交易类函数
22. 期权其他函数
23. 港股通专用函数
24. 港股通查询类函数
25. 港股通交易类函数
26. 计算函数
27. 技术指标计算函数
28. 其他函数
29. `fund_transfer` 资金调拨
30. `market_fund_transfer` 市场间资金调拨

本地归档：`api-catalog.md` 及 `02` 至 `06` 专题文档。

## 5. 公共资源

1. 对象
2. 数据字典

对象：`g/Context/BarData/Portfolio/Position/Order`。数据字典共 23 组。完整内容见 `07-objects-and-data-dictionaries.md`。

## 6. 策略示例

主页面链接到官方示例子页：

- 集合竞价追涨停策略
- Tick 级均线策略
- 双均线策略
- MACD 策略
- 融资融券双均线策略

本地索引：`08-runtime-libraries-examples-and-changelog.md`。

## 7. 常见问题

主页面链接到 FAQ 子页，分为：平台部署、数据、研究、回测、模拟交易、实盘交易、委托、三方库和其他，共 55 条。

本地归档：`faq.md`。

## 8. 支持的三方库

- Python 3.5：122 个包。
- Python 3.11：278 个包。

本地归档：`third-party-libraries.md`。

## 9. 三方库变动

覆盖 NumPy、Pandas 等从旧环境迁移到 Python 3.11 时的函数签名、参数、默认值和弃用项。

本地归档：`08-runtime-libraries-examples-and-changelog.md`。

## 10. 接口版本变动

官网从 `PBOXQT1.0V202101.03.000` 到 `PTrade1.0-QTV202401.05.032` 共列出 30 个版本节点。

本地归档：`changelog.md`。

## 计数说明

官网 DOM 含 187 个四级标题节点。两个资金调拨函数的 HTML 将各自的“使用场景/接口说明/参数/返回/示例”重复标成四级标题，去除 8 个结构性重复后得到 179 个内容块；再排除“关于持久化”说明块，得到 178 个可索引 API/对象/字典条目。
