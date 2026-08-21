# 公司研究与量化分析快速加载验证

验证日期：2026-08-21（Asia/Shanghai）

## 交付范围

- 公司研究允许恢复结构有效的当日 `partial` 快照，后台刷新失败时保留 last-good 内容。
- 量化数据按交易日、股票和数据域隔离缓存，分级启动重任务，并在换股、隐藏或卸载时取消旧请求。
- 候选扫描使用独立只读 DuckDB 快照，不再把正式数据库交给长生命周期子进程。
- 事件 K 线、高频采样、策略、回测、walk-forward、Kronos 和研究智能分别保留真实状态，单域失败不清空其他区域。
- 风险闸门按股票卡片展示阻断、警告、通过和不可用标签。
- 自定义标的和自选股进入真实盘中采样范围；自选登记在应用常驻层启动、变更和每 5 分钟续期。
- 同一股票同一观测秒统一读取 canonical TICK，旧的追加式原始记录仍完整保留用于审计。
- 市场概览后台刷新不再把已完成候选扫描误标为 pending，避免量化候选状态闪烁或 smoke 长时间等待。

## 自动验证

- API 全量：`1596 passed, 1 skipped, 5 warnings`。
- Web 全量：`126` 个测试文件，`730 passed`。
- 量化状态归因聚焦回归：`40 passed`。
- Ruff：`All checks passed`。
- TypeScript 与 Vite 生产构建：通过，`2292` 个模块完成构建。
- UTF-8/乱码扫描：修改文件无替换字符或连续问号异常。
- `git diff --check`：通过。
- 独立代码复审：无 Critical 或 Important 问题。

## EXE 验收

- 源码提交：`9f4cb028ab00f344afda3fae9b4f5010b6feafb7`。
- 发布清单：`source_state=clean`。
- EXE：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。
- SHA-256：`5A1D47CD8A2B02893E7FA1314B775E957C72D08EB7611A05EE3A065028238872`。
- 八个持久目录均保留：`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。
- 窗口可见：`321ms`，满足 3 秒目标。
- API 就绪：`7184ms`；完整 smoke：约 `19.3s`。
- 请求耗时：量化策略 `40ms`、公司研究 `108ms`、组合风险 `10ms`。

## 真实数据状态

- 信息总览：`ready`，A 股行情覆盖 `98.77%`，`5153 / 5217`。
- 量化策略：`partial`，返回 `12` 只真实候选，证据覆盖 `85%`。
- 公司研究：`partial`，标的 `600519`，证据覆盖 `0.65`，反方检查 `10` 项。
- 组合风险：无真实持仓，保持 `unavailable`，不生成模拟持仓。
- 通达信专业探针：两个结构响应为 `ready`，三个未初始化能力保持 `unavailable`，未用普通行情冒充专业字段。
- 质量门禁为 `warning`，仅表示量化与公司研究存在真实 `partial` 边界，不代表程序启动失败，也未伪造 `ready`。

## 问题闭环

首次新 EXE smoke 暴露候选状态未在 30 秒内收敛。逐秒诊断证明扫描已在约 18 秒完成，但市场概览后台刷新错误覆盖了候选状态，使响应在 `ready` 与 `pending/loading_overview` 间闪烁。修复后，概览刷新只标记 `market_overview_pending`，已完成候选扫描继续保持 `ready`；相同 smoke 随后连续通过。

测试期间只启动并结束本轮新建的观测台验证实例，没有关闭、重启或控制通达信，也没有控制鼠标或桌面。最终检查未发现观测台测试残留进程，通达信 PID `26392` 保持运行。
