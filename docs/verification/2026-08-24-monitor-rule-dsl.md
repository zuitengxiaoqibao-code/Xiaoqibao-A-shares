---
title: 2026-08-24 监控规则 DSL 与实时门控验证
status: confirmed
commit: 28bbf5efe9a909779720f95e69aa5a995b8b732a
---

## 变更

- 监控规则支持 `all`、`any`、`n_of` 组合条件，旧版 `{field: {operator: value}}` 配置继续兼容。
- 新增连续确认次数、确认窗口、冷却时间、数据新鲜度门控和自定义恢复条件；过期、缺失或不可信数据不会触发告警。
- 实时订阅补充 `stock_observation` 与 `data_sources`，规则状态持久化并记录 pending/active/recovery 生命周期。
- 规则 API 保存前统一标准化和校验，列表响应包含 `validation_state`、`condition_summary` 和标准化规则。
- 监控中心前端增加自由规则构建器、动态条件行、逻辑选择器、实时参数、严重级别、恢复条件和 JSON 预览，同时保留通知通道与旧规则编辑能力。

## 验证

- API 全量：1698 passed，1 skipped，5 warnings，108.12 秒。
- Web 全量：134 个测试文件，768 passed，24.23 秒。
- Ruff：`All checks passed!`。
- TypeScript/Vite production build：通过，Vite 构建 4.79 秒。
- 本轮 4 个提交的 `git diff --check`：全部通过。
- 本轮 9 个受影响源码/文档文件严格 UTF-8 解码：9/9 通过；替换字符和连续问号命中 0。

## 便携 EXE

- 构建命令：`scripts/build-portable.ps1 -SkipTests`。
- EXE：`dist/XiaoQiBao-Portable/xiaoqibao.exe`。
- 便携包：1832 个文件，约 8.53 GB；`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 持久目录已保留。
- EXE SHA-256：`AFB2CACCF2BB09ECB28FDD8480D918882ABB023CE5149FAA718FFE9E77F7604A`。
- 热启动 smoke：窗口可见 106ms，API 就绪 3939ms，14/14 菜单性能门禁通过；验证完成 14601ms。
- 恢复演练：窗口可见 98ms，API 就绪 3967ms，36 个数据库，迁移版本 1，关键 API 通过。
- 发布质量门禁：通过；签名清单校验通过。

## 真实数据边界

- 热启动真实覆盖率为 99.69%，恢复演练环境覆盖率为 98.73%；均按 `partial` 警告呈现，不伪装成 ready。
- 量化策略为 partial（候选 12 个、覆盖率 85%）；公司研究为 partial（600519、覆盖率 0.65、反方风险 10 条）；无持仓组合风险为 unavailable。
- 通达信专业字段按探针结果分别显示 ready/unavailable；未把结构响应直接冒充业务字段已映射。
- 没有生成模拟行情、模拟告警或虚假 AI 结论；本轮未关闭、重启或控制通达信，也未控制鼠标或桌面。

