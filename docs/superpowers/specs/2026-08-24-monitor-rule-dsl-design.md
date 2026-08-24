# 监控规则 DSL 与分层实时引擎设计

**日期：** 2026-08-24

## 目标

把监控中心从单字段阈值升级为可组合、可解释、可追溯的规则系统，同时按数据源能力提供真实的分层实时刷新。规则不因数据缺失、过期或来源不可信而误触发。

## 范围

- 兼容现有 `conditions` 规则 JSON。
- 新增 `logic`（all/any/n_of）、确认次数、确认窗口、冷却时间、恢复滞回、数据新鲜度、交易时段和数据质量门控。
- 基础模式提供表单配置，高级模式提供结构化 JSON 预览和复制。
- 实时规则评估继续消费统一实时快照总线，不新增外部服务。
- 首批支持市场总览、量化策略、新闻事件、尾盘选股、个股观察、公司研究和数据源主题。

## 规则契约

```json
{
  "id": "rule-量价突破",
  "name": "量价突破",
  "enabled": true,
  "topics": ["quant_strategy"],
  "logic": "all",
  "conditions": [
    {"field": "change_pct", "op": "gte", "value": 2},
    {"field": "volume_ratio", "op": "gte", "value": 1.5}
  ],
  "confirm_count": 3,
  "confirm_window_seconds": 10,
  "cooldown_seconds": 300,
  "recovery": {"enabled": true, "logic": "all", "conditions": [{"field": "change_pct", "op": "lte", "value": 1.5}]},
  "freshness_seconds": 5,
  "require_freshness": true,
  "severity": "warning",
  "channels": {"in_app": true, "tts": true, "feishu": false}
}
```

支持的基础比较符：`eq`、`gt`、`gte`、`lt`、`lte`。兼容旧格式 `{field: {operator: value}}` 时自动转换为 all 条件组。

## 实时语义

- 快照进入规则引擎前校验 `observed_at`、`freshness`、`source` 和字段完整性。
- `freshness_seconds` 超限时规则不触发，状态显示为“数据过期”；不使用旧快照冒充实时数据。
- `confirm_count` 在窗口内连续满足才触发；窗口内断开则清零。
- `cooldown_seconds` 防止同一规则/标的重复告警。
- 恢复规则独立于触发规则，满足恢复条件后生成一次恢复事件。
- 规则状态、触发快照、实际值、阈值、来源和延迟都写入审计记录。
- 继续采用事件驱动为主、15 秒摘要轮询为保底；页面隐藏时暂停轮询。

## 界面

- 规则配置提供逻辑模式、动态条件行、连续确认次数、确认窗口、冷却时间、数据新鲜度、严重级别和恢复条件。
- 保存前显示规则预览和“缺失字段/实时门控”提示。
- 高级 JSON 只读预览，支持复制，不允许绕过后端校验。
- 已有规则点击后可编辑，保存后保持旧规则字段和投递配置。

## 错误与安全边界

- 字段不存在、操作符不支持、阈值类型错误、窗口/冷却为负数均返回中文校验错误。
- 未配置通道、数据源不可用、数据过期、主题无事件均显示明确状态，不生成告警。
- 规则评估不能调用 AI、重新采集行情或阻塞实时总线；AI 分析只能作为后续异步解释。

## 验收

- 后端测试覆盖 DSL 兼容、组合逻辑、确认窗口、冷却、过期数据阻断、恢复条件、校验错误和实时总线回归。
- 前端测试覆盖动态条件配置、逻辑模式、实时参数、规则预览和保存请求。
- API/Web 全量测试、Ruff、TypeScript/Vite、乱码扫描、EXE smoke、恢复演练和发布质量门禁全部通过。
