# 2026-08-06 缓存优先与启动性能验证

## 本轮目标

- 信息总览启动时优先展示当天缓存，后台继续请求最新真实快照。
- 最新快照成功后显示“已加载最新数据 · 实时监控中”；失败时保留缓存并说明失败原因。
- 健康检查不再等待运行时写锁，避免后台写任务拖住桌面就绪探测。
- 量化 ECharts 图表复用同一实例，只更新 option，减少切股和实时刷新时的初始化开销。
- 烟测脚本分别记录窗口显示、API 健康就绪和完整验证完成时间，避免把后续接口耗时误报为 API 就绪时间。

## 实施文件

- `apps/web/src/features/market-overview/marketOverviewCache.ts`
- `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- `apps/web/src/features/market-overview/overview.css`
- `apps/web/src/features/quant-analysis/QuantChart.tsx`
- `apps/api/src/qibao_api/main.py`
- `scripts/run-portable-smoke.ps1`

## 验证结果

- 前端全量测试：68 个测试文件、426 项通过。
- API 全量测试：1065 项通过、1 项按设计跳过。
- 前端生产构建：`npm run build` 通过，TypeScript/Vite 退出码 0。
- 便携构建：`scripts/build-portable.ps1 -SkipTests` 通过。
- 便携烟测：通过；窗口 300ms 出现，API `/health` 11524ms 就绪，完整接口验证 11939ms 完成，信息总览 `ready`，量化策略 `unavailable`（真实样本不足时不虚构）。
- 烟测结束后没有残留 `xiaoqibao` 进程。
- EXE SHA-256：`8C05483CAF72C952C61CA5A351593822D9115BC4BB7A3E67909A28659591ADC0`。

## 数据真实性边界

- 当天缓存按上海时区日期隔离；跨日缓存不会作为当前市场快照展示。
- 缓存只作为最新请求完成前的临时可见证据，不改变 API 的真实状态和来源字段。
- API 或缓存不可用时保留空缺和明确原因，不用零值、随机曲线或其他股票数据补齐。

## 交付入口

`dist/XiaoQiBao-Portable/xiaoqibao.exe`

便携持久目录 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 已保留。
