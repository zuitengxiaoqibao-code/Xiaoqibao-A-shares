# 2026-08-06 全站视觉证据内核验证

## 本轮范围

- 新增共享证据状态与可视化原语：数据状态提示、指标带、仪表行、排名条和证据徽章。
- 新增 ECharts 图形工厂：柱线组合、双轴、雷达、热力、treemap、仪表和 K 线。
- 信息总览新增非重复的高密度指标带；数据不可用时显示空缺，不把占位 0 当成真实数据。
- 分时、事件 K 线和量化因子雷达统一使用字面量主题色，红涨绿跌；雷达缺失因子保持空值。

## 验证结果

- 前端测试：67 个测试文件，416 项通过。
- TypeScript/Vite：`npm run build` 通过。
- 乱码扫描：`apps/web/src` 与 `apps/api/src` 自定义扫描无异常。
- 知识库校验：`validate_vault.py` 通过。
- 便携重建：`scripts/build-portable.ps1 -SkipTests` 通过。
- EXE 烟测：`scripts/run-portable-smoke.ps1` 通过；窗口可见 308ms，API 就绪约 12473ms，信息总览 ready，量化策略 unavailable（样本不足时不虚构）。
- EXE SHA-256：`ABB1D70ED8B4B8B0595DD99B86B8D9C86DEB3DA07F6B962F71CA688C0191239E`。

## 交付入口

`dist/XiaoQiBao-Portable/xiaoqibao.exe`

便携版持久目录已保留：`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。
