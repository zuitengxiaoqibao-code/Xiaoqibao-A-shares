# Kronos 价格路径预测证据设计

## 目标

把 Kronos 接入首次涨停量化分析页，作为独立的价格路径预测证据。它只补充 OHLCV 的未来情景，不替代首次涨停规则、市场情绪、新闻、基本面、回测或风险审核。

## 范围

### 本次包含

- 后端增加 Kronos 预测契约、适配器、服务和查询路由。
- 预测服务读取本地 A 股日线，默认使用最近 250 根有效日线和未来 20 个交易日窗口。
- 预测响应必须明确 `ready`、`unavailable`、`insufficient` 或 `error` 状态，并携带原因、模型版本、数据截至时间和来源。
- 前端量化分析页增加“价格路径预测”面板，展示中位路径、上下行区间、路径分歧度和证据状态。
- 未安装 PyTorch、Kronos 源码或模型权重时，页面显示配置指引，不生成随机预测值。
- 增加单元测试、路由测试、前端状态测试和构建验证。

### 本次不包含

- 不自动下载模型权重。
- 不在 API 启动阶段强制加载大型模型。
- 不做 Kronos 微调；当前本地股票样本量不满足可靠微调条件。
- 不连接券商、不自动下单、不新增模拟资金功能。
- 不把预测结果直接转换成买入、卖出或仓位指令。

## 数据流

```text
FirstLimitUpCandidate
        |
        v
BarRepository.latest(symbol, 250, as_of)
        |
        v
KronosForecastService
  - 检查依赖/模型配置
  - 组织 OHLCV + amount + 交易日时间戳
  - 生成多条预测路径
  - 计算中位数、上下分位、预期收益、下行风险、分歧度
        |
        v
GET /api/v1/a-shares/first-limit-up/quant-forecast
        |
        v
QuantAnalysisDashboard / 价格路径预测面板
```

## 后端接口

### `GET /api/v1/a-shares/first-limit-up/quant-forecast`

查询参数：

- `symbol`: 6 位 A 股代码，必填。
- `as_of`: 研究截止日期，可选，不能晚于服务器日期。
- `horizon`: 预测交易日数量，可选，限制在 5–20。

响应核心字段：

```json
{
  "status": "ready | unavailable | insufficient | error",
  "symbol": "600000",
  "as_of": "2026-07-24",
  "observed_through": "2026-07-24",
  "model": "Kronos-mini",
  "frequency": "1d",
  "lookback_bars": 250,
  "horizon_bars": 20,
  "sample_count": 20,
  "summary": {
    "median_return_pct": 3.4,
    "upper_return_pct": 11.2,
    "lower_return_pct": -6.1,
    "path_dispersion_pct": 8.7,
    "downside_probability_pct": 35.0
  },
  "points": [
    {
      "trade_date": "2026-07-27",
      "median_close": 10.42,
      "lower_close": 10.12,
      "upper_close": 10.71
    }
  ],
  "reasons": [],
  "sources": ["local-daily-bars", "kronos"],
  "warnings": []
}
```

数值只有在 `status=ready` 时存在。其他状态必须返回空 `points` 和可读原因。

## 模型边界

- 适配器通过配置的 Kronos 源码路径加载官方 `KronosTokenizer`、`Kronos` 和 `KronosPredictor`。
- 模型和 tokenizer 通过配置的 Hugging Face 名称或本地路径加载。
- 运行时懒加载并缓存模型，避免 API 启动时联网或重复加载。
- 默认建议 `Kronos-mini`；若本机已经配置更大模型，可替换为 `Kronos-small` 或 `Kronos-base`。
- 模型输出只表示价格路径情景，不等同于经过校准的交易概率。

## 前端展示

量化分析页新增第五个证据面板：

- 标题：`Q5 / PRICE PATH`、`Kronos 价格路径预测`。
- `ready`: ECharts 折线显示历史收盘、预测中位线、上下区间带，并显示预期收益、下行概率、路径分歧度。
- `unavailable`: 显示“模型未启用”，同时说明需要 PyTorch、Kronos 源码和模型权重，不显示假数据。
- `insufficient`: 显示实际缺失项，例如日线不足 250 根或数据存在空值。
- `error`: 显示可重试的错误状态，但保留其他四个面板。
- 使用现有金色、青色和洋红色语义：中位线金色，上行边界青色，下行边界洋红色。

## 验证标准

- 服务单测覆盖依赖缺失、历史不足、有效预测摘要和异常隔离。
- 路由测试覆盖参数校验与响应状态。
- 前端测试覆盖 ready/unavailable/insufficient/error 四种状态。
- 不允许出现 `NaN`、`Infinity`、随机曲线或未标注的模型数字。
- 全量 API 测试、量化相关 Web 测试和 Web 构建通过。

