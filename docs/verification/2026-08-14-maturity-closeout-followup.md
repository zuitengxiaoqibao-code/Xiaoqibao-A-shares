# 2026-08-14 成熟化收尾补强验收

## 本次补强

- 量化风格评估持久化前一交易日风险分；启动后可读取已验证的历史风险快照，缺失时保持 `null` 并标记证据限制。
- 资金净流入因子增加真实符号覆盖率；覆盖不足时不计算全市场净流入率，界面显示覆盖比例和未达门槛原因。
- 公司研究字段证据新增 F10 公司概况、行业分析、最新提示及前向 PE 的来源、观测时间和缺失原因。
- 通达信只读能力探测增加稳定诊断码，区分方法不可用、桥接不可达、空响应和结构无效；专业字段仍保持 detected-only/unavailable，不用普通行情替代。
- 数据设置页显示通达信能力诊断码，便于定位本地接口问题。

## 验证结果

源码提交：`a13b1810f01c59c5c4dc881075b8cb0b0092355a`

- API：`1366 passed, 1 skipped, 5 warnings`
- Web：`110 test files / 648 passed`
- Ruff：通过
- TypeScript/Vite：通过；应用入口约 354 KB，ECharts 独立约 1.04 MB vendor chunk；保留现有大 chunk 提示
- UTF-8/乱码扫描：通过
- Web 测试结束后：无遗留 Node/Vitest 进程

真实发布数据 smoke：

- 窗口可见：`87ms`
- API 就绪：`2379ms`
- 完整验证：`10619ms`
- 信息总览：`ready`，覆盖率 `98.52%`
- 量化策略：`partial`，真实候选 `12` 只，因子覆盖 `85.00%`
- 公司研究：`partial`，标的 `600519`，证据覆盖 `0.65`，反方检查 `10` 项
- 组合风险：无持仓时 `unavailable`
- 通达信专业能力：`Fn193`、`GO1` 仅结构响应已验证；`GP1`、`BK5`、`SC1` 按真实初始化/可用性显示 unavailable

便携 EXE：

- 路径：`dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`E8429A763B429100198C4DA293E602A957816D93D40DA9FF5F56C9793F293D92`
- 发布清单：`source_state=clean`，提交与源码一致
- `config/data/news/cache/logs/models/exports/backups` 八个持久目录保留

## 通达信与桌面安全

- smoke 前后通达信 `TdxW.exe` PID `12760` 保持存在。
- 本次没有关闭、重启或控制通达信，也没有控制鼠标或桌面。
- smoke 后无本程序 EXE、Node 或测试 Python 残留进程。

## 仍保持的真实数据边界

- 全市场资金流当前只报告已验证覆盖率；未达到门槛时净流入率为 `null`。
- 日线历史覆盖仍为 `partial` 时，量化扫描使用最新共同覆盖交易日，不把旧日期冒充实时。
- 通达信专业字段未完成语义/单位映射前不绑定业务菜单。
- 公司研究缺少历史估值序列、市场份额等证据时保持 partial/unavailable，不用 AI 文本填充原始证据。
