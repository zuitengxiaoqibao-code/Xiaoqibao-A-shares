---
title: 2026-08-24 监控中心升级验证
status: confirmed
commit: b1ac363704be1ca1be1aa70a426eb5ca603fb652
---

## 变更

- 后端告警新增严重级别、活跃/恢复状态、确认人和确认时间、连续触发次数、恢复关联及投递重试次数；旧 `monitor-center.json` 自动补齐默认字段。
- 新增监控摘要、告警确认、投递重试接口；实时总线在规则不再匹配时生成恢复事件。
- 监控中心改为摘要优先仪表盘，展示服务心跳、规则/KPI、主题健康卡、告警时间线和主题/级别/状态/标的筛选；保留规则编辑与飞书配置。
- 前端可见页每 15 秒刷新，页面隐藏时暂停；请求代次保护防止旧响应覆盖新状态，刷新失败保留最后一次有效摘要并显示中文原因。

## 验证

- Web：134 个测试文件，767 passed。
- API：1682 passed，1 skipped，5 warnings。
- Ruff：通过。
- TypeScript/Vite production build：通过。
- UTF-8/乱码扫描：通过；`git diff --check`：通过。
- 便携构建：`dist/XiaoQiBao-Portable/xiaoqibao.exe`。
- EXE smoke：窗口 339ms 可见，API 6608ms 就绪，14/14 菜单性能门禁通过。
- 恢复演练：窗口 86ms 可见，API 2249ms 就绪，36 个数据库、迁移版本 1、关键 API 通过。
- 发布质量门禁：通过。
- EXE SHA-256：`F8DD2223EA8A0922C88FE9007D44389924B6893DE37C1CCF6B44ABC38894F544`。

## 真实数据边界

发布 smoke 仍按证据显示信息总览覆盖率 99.18%、量化策略 partial、公司研究 partial、无持仓组合风险 unavailable；通达信专业字段按探针结果分别显示 ready/unavailable。没有生成模拟行情、模拟告警或虚假 AI 结论。本轮未关闭、重启或控制通达信，也未控制鼠标或桌面。
