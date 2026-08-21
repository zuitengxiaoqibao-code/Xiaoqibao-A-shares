# TickFlow 能力原生整合验证

## 范围

- 多格式本地导入、隔离行和多源裁决。
- 受控策略注册、白名单表达式和 AI 草稿门禁。
- A 股矩阵/组合回测与可复现哈希。
- 一级菜单监控中心、通道隔离和告警历史。
- 盘后事实冻结、AI 不可用降级、不可变报告和独立推送状态。

## 已完成验证

- API 全量：`1624 passed, 1 skipped`。
- Web 生产构建：通过；新增监控中心独立代码分块。
- Web 导入/监控/导航聚焦：`8 passed`；仪表盘路由：`27 passed`。
- Ruff：通过；冷启动导入测试确认主程序不会提前加载 DuckDB。
- 所有真实数据不足状态继续使用 `partial`、`stale` 或 `unavailable`，没有随机行情、模拟候选或伪造 AI 概率。

## 最终 EXE 验收

- 便携 EXE：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。
- 发布清单绑定 clean commit：`892a9acb7594689b7b57e550f2e60ce3019885a0`；EXE SHA-256：`394613AF1E2CAD4FE2EC16D290276A65F6C88F99D1030D21424BDBDA46E02F14`；迁移版本：`1`。
- 真实 EXE smoke：窗口可见 `90ms`，API 就绪 `4354ms`，完整验证 `18048ms`；请求耗时：overview `6654ms`、quant `45ms`、portfolio `38ms`、research `273ms`。
- 真实数据状态：信息总览 `ready`、覆盖率 `98.77%`；量化策略 `partial`（12 个真实候选、证据覆盖 `85%`）；公司研究 `partial`（600519、证据覆盖 `0.65`、10 项反方检查）；无持仓组合风险 `unavailable`；通达信专业字段按实际能力保留 `ready/unavailable`，不以普通行情或模拟值替代。
- 恢复演练：临时副本校验 `36` 个数据库文件，迁移 `1`，关键 API `pass`；八个持久目录 `config/data/news/cache/logs/models/exports/backups` 均保留。
- 发布整合门禁：`TickFlow integration gate passed`。API `1624 passed, 1 skipped`，Web `128` 个测试文件/`732 passed`，Ruff、生产构建、UTF-8 乱码扫描和 `git diff --check` 通过。
- 依赖治理：`scripts/build-portable.ps1` 现在会在构建前同步 `apps/api[dev]` 锁定依赖并预检 `python-multipart`，避免测试环境与打包环境分叉。
- 边界：本轮只启动并结束观测台自动验证实例，未启动、关闭、重启或控制通达信，未控制鼠标或桌面；真实数据不足继续使用 `partial/stale/unavailable`，不伪造完整结果。
