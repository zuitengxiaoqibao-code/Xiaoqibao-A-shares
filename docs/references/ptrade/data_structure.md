# PTrade 永久知识库索引

> 官方入口：https://ptrade.i618.com.cn:7766/hub/help/api
> 最后核对：2026-07-27
> 最新版本线索：`PTrade1.0-QTV202401.05.032`
> 状态：外部能力资料库；不代表本项目已经获得券商权限或已完成数据接入。

## 知识库边界

本目录按 PTrade 官网左侧知识树整理，目标是为后续数据桥、研究、回测、风控和可能的交易执行保留可检索资料。内容来自官方文档的结构化摘要，不把文档中的“支持”误写成当前账户“已开通”。

PTrade 策略运行在券商提供的研究、回测或交易环境中，不是本地 FastAPI 可以直接调用的公开 HTTP API。项目接入必须经过 PTrade 内部策略导出、文件交换或经过验证的桥接服务。

## 覆盖清单

| 知识面 | 已索引数量 | 存放位置 |
| --- | ---: | --- |
| 一级知识树章节 | 10 | 本文件、各专题文档 |
| 三级功能分组 | 49 | 本文件、`api-catalog.md` |
| 事件与可调用函数 | 149 | `api-catalog.md` |
| 公共对象 | 6 | `07-objects-and-data-dictionaries.md` |
| 数据字典 | 23 | `07-objects-and-data-dictionaries.md` |
| 有效四级知识条目 | 178 | `api-catalog.md`、对象与字典文档 |
| FAQ | 55 | `faq.md` |
| 官方策略示例 | 5 | `08-runtime-libraries-examples-and-changelog.md` |
| Python 3.5 三方库 | 122 | `third-party-libraries.md` |
| Python 3.11 三方库 | 278 | `third-party-libraries.md` |
| 接口历史版本节点 | 30 | `changelog.md` |

说明：官网 DOM 有 187 个四级标题节点，其中 `fund_transfer` 和 `market_fund_transfer` 的页面标记把“使用场景/接口说明/参数/返回/示例”重复当成四级标题。归一后是 178 个有效条目：149 个事件/函数、6 个对象、23 个字典。

## 左侧知识树

1. 使用说明：新建策略、回测、交易、运行周期、运行时间、支持业务和最小价差。
2. 开始写策略：最小策略、下单示例、实用策略、持久化、代码后缀、异常处理和价格精度。
3. 策略引擎简介：生命周期事件、回调和定时任务。
4. 策略 API 介绍：设置、调度、信息查询、行情、证券、账户、交易、两融、期货、期权、港股通、指标和工具。
5. 公共资源：`g`、`Context`、`BarData`、`Portfolio`、`Position`、`Order` 以及数据字典。
6. 策略示例：股票和两融示例。
7. 常见问题：部署、数据、研究、回测、模拟、实盘、委托、三方库和其他问题。
8. 支持的三方库：Python 3.5 与 Python 3.11 环境清单。
9. 三方库变动：Python 3.5 到 3.11 的 API 兼容性差异。
10. 接口版本变动：30 个历史版本节点及其变动。

## 文件导航

| 文件 | 内容 |
| --- | --- |
| `01-platform-and-lifecycle.md` | 平台边界、运行周期、阶段事件、持久化和并发模型 |
| `02-settings-and-scheduling.md` | 设置、调度、回测逼真度和任务限制 |
| `03-market-data.md` | 交易日历、历史行情、实时快照、Level-2 和行情语义 |
| `04-securities-fundamentals-and-bonds.md` | 证券池、状态、基本面、ETF、IPO、转债和 REITs |
| `05-account-orders-and-trades.md` | 账户、持仓、订单、成交、撤单和资金流水 |
| `06-margin-and-deferred-markets.md` | 两融、期货、期权、港股通及暂缓接入边界 |
| `07-objects-and-data-dictionaries.md` | 六个公共对象的字段和 23 组字典映射 |
| `08-runtime-libraries-examples-and-changelog.md` | 示例、运行环境、依赖迁移和变更记录导航 |
| `09-project-integration-map.md` | 与本项目盘前/盘中/盘后、A 股、转债和数据桥的映射 |
| `api-catalog.md` | 149 个事件/函数的全量签名目录和官方锚点 |
| `faq.md` | 55 个官方常见问题的结构化摘要 |
| `third-party-libraries.md` | Python 3.5/3.11 全量包名和版本 |
| `changelog.md` | 30 个版本节点的变化索引 |
| `tree-menu.md` | 官网左侧 10 个一级章节、49 个三级分组和外部子页镜像 |
| `../ptrade-api-reference.md` | 面向当前项目的执行摘要 |

## 使用约定

- `现在`：可直接帮助 A 股/转债的数据、研究、盘前盘中盘后或风控设计。
- `后续`：未来可能使用，但当前项目不连接或没有权限证明。
- `归档`：为兼容历史策略、环境迁移和排错保留。
- 官方锚点是最终定义；本地摘要用于检索和设计，不替代券商环境中的实际权限测试。
- 任何空响应、权限失败、延迟或字段缺失都必须显式记录，不能用推测值补齐。
- 券商、柜台、客户端版本可能造成能力差异，上线前必须在目标账户做最小样本验证。
