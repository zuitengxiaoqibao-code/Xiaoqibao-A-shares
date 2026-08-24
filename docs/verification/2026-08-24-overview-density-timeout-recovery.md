# 信息总览密度与分区恢复验证

## 变更

- 工作区栅格改为内容自适应：取消无关 block 等高，短指标卡不再被长表拉高。
- 盘中异动列表和资讯列表改为有界高度；无内容时使用紧凑中文空态。
- 题材/证据地图只有在资讯、题材、A 股三者存在可验证关联时才渲染关系画布，否则显示原因明确的紧凑空态。
- 新增 `SectionRefreshState`：信息总览刷新失败且存在 last-good 数据时保留旧快照，显示中文阶段、失败原因和单次区块重试按钮。

## 源码与测试

- 提交：`6db106f01e005908ef40e0c001d453daf1be7db1`
- Web：`134` 个测试文件，`758 passed`
- API：`1665 passed, 1 skipped, 5 warnings`
- Ruff：通过
- Web production build：通过
- UTF-8/乱码扫描：通过
- `git diff --check`：通过

## 便携 EXE 验证

- EXE：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`773428D0F7D28AC7F9964D3CD56256AE3DF08786B67DC70F0570A66714121C45`
- 发布清单：`source_state=clean`
- 热启动 smoke：通过；窗口 `102ms`，API `2467ms`，14 菜单 `14/14` 通过，缓存首帧均不超过 `1s`
- 恢复演练：通过；复制并校验 `36` 个数据库，迁移版本 `1`，关键 API `pass`
- 发布质量门禁：通过；质量状态为 `warning` 仅因真实量化候选和公司研究仍为 `partial`，没有伪造 `ready`

## 真实数据边界

- 信息总览覆盖 `98.47%`，真实状态 `ready`。
- 量化策略 `partial`：12 个候选，因子覆盖 `85%`。
- 公司研究 `partial`：600519，证据覆盖 `0.65`，反方检查 `10` 项。
- 无持仓组合风险 `unavailable`，不是错误，也没有补造持仓。
- 通达信专业探针按真实能力保留 `ready/unavailable` 明细。
- 冷启动探针曾在公司研究请求处返回 HTTP 0 空响应；随后热启动完整 smoke 通过。该次失败已作为探针时序/外部服务边界记录，不掩盖为通过。

## 运行安全

本轮未关闭、重启或控制通达信，未控制鼠标或桌面。便携目录中的 `config/data/news/cache/logs/models/exports/backups` 持久目录已保留。
