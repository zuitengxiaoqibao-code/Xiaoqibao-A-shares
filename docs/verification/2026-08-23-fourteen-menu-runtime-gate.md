---
type: verification
status: confirmed
updated: 2026-08-23
tags: [verification, performance, menus, portable-exe]
---

# 十四菜单真实运行门禁

## 证据缺口

此前 `verify-menu-performance.ps1` 只验证输入样本的契约，发布 smoke 未从真实 EXE 逐项采集十四菜单，发布质量门禁也不要求该证据。因而“十四菜单十秒内可用或明确降级”只有规则自测，没有完整运行证据。

## 实现

- 新增 `probe-menu-performance.ps1`，从运行中的便携 EXE 逐项请求十四个页面快照。
- 端到端计时覆盖 HTTP 请求，不使用后端内部计时冒充用户等待时间。
- 请求失败记录菜单中文名称、失败阶段和原始原因；十秒内明确降级可以通过，超时、缺菜单、重复菜单、无原因空结果或缓存首帧超过一秒会失败。
- `run-portable-smoke.ps1` 将完整结果写入签名发布清单的 `quality_gates.menu_performance`。
- `verify-release-quality.ps1` 重新计算门禁，不接受缺失、数量不足、伪造状态或失败的十四菜单证据。
- 采样脚本使用带 BOM 的 UTF-8，同时兼容 Windows PowerShell 5.1 和当前 PowerShell。

## 最终便携 EXE 结果

| 菜单 | 状态 | 端到端耗时 | 缓存首帧 |
| --- | --- | ---: | ---: |
| 信息总览 | ready | 35ms | 2ms |
| 今日研判 | ready | 30ms | 3ms |
| 个股观察 | ready | 11ms | 6ms |
| 公司研究 | ready | 9ms | 3ms |
| 首次涨停 | ready | 7ms | 3ms |
| 尾盘选股 | ready | 8ms | 3ms |
| 量化分析 | ready | 9ms | 5ms |
| 监控中心 | ready | 11ms | 1ms |
| 新闻热点 | ready | 7ms | 2ms |
| 风险提醒 | ready | 6ms | 2ms |
| 历史复盘 | ready | 5ms | 2ms |
| 数据设置 | ready | 9ms | 不需要共享缓存帧 |
| 本地运维 | ready | 13ms | 不需要共享缓存帧 |
| 可转债 | ready | 10ms | 不需要共享缓存帧 |

最终 EXE cold smoke：窗口 `538ms`，API `7800ms`，完整验证 `19513ms`；hot smoke：窗口 `217ms`，API `2678ms`，完整验证 `10959ms`。两次十四菜单均为 `14/14 pass`。恢复演练校验 `36` 个数据库、迁移版本 `1`、关键 API `pass`，发布质量门禁通过。

发布清单绑定源码提交 `3176aaf21c343e659d5759d5e437c401bcbd0f13`，`source_state=clean`；便携 EXE SHA-256 为 `430FF47E24FA550A6DAC35EBD32DB1DAEF1CF1341007046F504B5277D66E73C4`。业务数据的 `partial/unavailable` 状态仍由各领域接口独立保留，不因页面快照 `ready` 而提升。
