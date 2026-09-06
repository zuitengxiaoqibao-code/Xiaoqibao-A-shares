---
type: verification
status: confirmed
date: 2026-09-03
tags: [overseas-market, data-screen, portable-exe]
---

# 美股风向标验收记录

## 范围

数据大屏新增“隔夜外盘”区域，统一展示三大美股指数和七个美股风向标：道琼斯、标普 500、纳斯达克、苹果、微软、英伟达、谷歌、亚马逊、Meta、特斯拉。前端通过单一批量接口读取，不按卡片重复请求。

## 真实性与失败语义

- 数据源为腾讯财经海外行情批量接口，响应按 GBK 解码。
- 缺少任一白名单标的时，整组标记为“暂不可用”，不生成模拟行情。
- 首次请求失败时展示中文失败原因。
- 刷新失败但存在上一份完整快照时保留旧快照，并标记“数据陈旧”。
- 每条报价包含价格、涨跌额、涨跌幅、源交易日期和“盘中/最近收盘”状态。

## 验证结果

后端专项测试：5 passed。

后端全量回归：1784 passed，1 skipped，5 warnings。

前端全量测试：140 个文件、850 项通过。

前端生产构建：`pnpm --filter @qibao/web build` 成功。

便携版冷启动烟测：窗口 85ms 可见，API 3217ms 就绪，14/14 菜单性能门禁通过；退出后无 `xiaoqibao.exe` 残留。

正式 EXE 真实接口核验：`GET /api/v1/market/overseas` 返回 `quality=ready`，指数 3 个、风向标 7 个，源交易日期为 `2026-09-02`，交易状态为最近收盘。

## 交付物

- EXE：`dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`9675B8DCC71680350DC5E93CE788DE47D364D4FE344DE820EFA00ED6F95EA0BD`
- 发布清单中的可执行文件哈希与 EXE 一致。

## 残余边界

隔离烟测环境中的部分 A 股数据源、量化策略和通达信专业模块可能显示 `partial/unavailable`；这是实际数据源状态，程序会如实显示，不以模拟值掩盖。
