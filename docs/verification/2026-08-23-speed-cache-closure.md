---
type: verification
status: confirmed
updated: 2026-08-23
tags: [verification, performance, cache, portable-exe]
---

# 2026-08-23 速度与缓存闭环

## 本轮变更

- 量化研究智能面板移除独立 60 秒轮询，改用首次加载、`quant_strategy` 实时事件和断线保底刷新。
- 通达信公式证据面板移除独立 15 秒轮询，改用 `market_overview` 实时事件、断线保底和回到前台刷新。
- 公司研究移除独立 5 分钟轮询，统一使用全局实时总线、断线保底和回到前台刷新。
- 公司研究缓存读取向前回退最多 20 条记录，损坏或旧语义校验失败时返回最近一条可验证缓存，所有候选损坏时仍诚实报告完整性错误。
- 尾盘选股清理无效计时器和错误清理逻辑。

## 验证结果

- API：`1665 passed, 1 skipped, 5 warnings`。
- Web：`133` 个测试文件、`755 passed`。
- Ruff：`All checks passed!`。
- Web production build：通过。
- 菜单性能门禁回归：`4 passed`。
- 便携 EXE 冷启动：窗口首帧 `382ms`，API 就绪 `7577ms`，验证完成 `19968ms`；首页 `31ms`，信息总览 `7262ms`，量化 `14ms`，公司研究 `64ms`。
- 便携 EXE 热启动：窗口首帧 `87ms`，API 就绪 `2274ms`，验证完成 `11343ms`；首页 `50ms`，信息总览 `3698ms`，量化 `37ms`，公司研究 `103ms`。
- 恢复演练：通过，临时副本校验 `36` 个数据库，迁移版本 `1`，关键 API smoke 通过。

## 真实边界

- 信息总览覆盖率 `99.88%`，因此状态为 `partial`；没有把 partial 伪装成 ready。
- 量化策略真实候选 `12`，覆盖率 `85%`，状态为 `partial`。
- 公司研究为 `600519`，证据覆盖 `0.65`，反方风险 `10` 条，状态为 `partial`。
- 组合风险因无持仓返回 `unavailable`；通达信专业字段因官方 Python 专业接口初始化失败保持 `unavailable`，未生成代理值或模拟值。
- 用户通达信进程未关闭、重启或控制。

## 发布说明

本轮构建生成于 `dist/XiaoQiBao-Portable`，发布清单已签名。提交源码后需再次构建 clean release，再运行发布质量门禁，确保 manifest 的 `source_state=clean`。
