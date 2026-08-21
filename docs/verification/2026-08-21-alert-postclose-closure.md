# 告警与盘后闭环最终验收

验证日期：2026-08-21（Asia/Shanghai）

## 交付范围

- 飞书配置使用 Windows DPAPI 保护，界面只展示脱敏状态；配置、启用、停用、测试发送和业务响应失败均有中文状态。
- 监控中心复用 `RealtimeSnapshotBus`，支持主题、嵌套字段、运算符、阈值、应用内提示、Edge TTS 和飞书独立通道，以及冷却去重。
- 常驻 Edge TTS 播报器领取待播告警、播放音频并回写 `playing/sent/failed`；重启后过期待播告警不会被重复播报。
- 盘后报告沿用 15:30 调度和启动补跑；手动运行也冻结事实。投递重试只重试发送，不重新采集事实或重复运行 AI。
- 历史复盘展示冻结报告、证据覆盖、AI 状态和飞书状态，并提供投递专用重试。
- 数据质量矩阵增加量化策略、公司研究、组合风险和通达信专业字段的真实来源水位、限制和中文修复动作。

## 自动验证

- API 全量：`1650 passed, 1 skipped, 5 warnings`。
- Web 全量：`129` 个测试文件，`736 passed`。
- Ruff：通过。
- TypeScript/Vite 生产构建：通过。
- UTF-8/乱码扫描：无替换字符或连续问号异常。
- `git diff --check`：通过。
- TickFlow 整合门禁：通过。

## 便携 EXE 验收

- 源码提交：`079da11e9e772b0a589c164eb546aa891de34f49`。
- EXE：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`。
- SHA-256：`9CE4778681F3F915359F1A7416BEDDE6D17CD7D41A95E97DE000AAAA9D6D407B`。
- 发布清单绑定 clean 源码提交；迁移版本：`1`。
- 持久目录保留：`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`。
- 真实 EXE smoke：窗口可见 `371ms`，API 就绪 `7400ms`，完整验证 `18888ms`。
- 信息总览：`ready`，覆盖率 `99.56%`。
- 量化策略：`partial`，`1` 只真实候选，证据覆盖 `85%`。
- 公司研究：`partial`，标的 `600519`，证据覆盖 `0.65`，反方检查 `10` 项。
- 组合风险：无真实持仓，保持 `unavailable`。
- 通达信专业字段：按实际探针结果显示 mixed，不用普通行情或模拟值冒充专业能力。

## 恢复与运行约束

- 恢复演练校验 `36` 个数据库文件，迁移版本 `1`，关键 API：`pass`。
- 质量门禁：`pass`。
- 测试结束无观测台 EXE、Python 或 Node 测试残留进程。
- 通达信进程 `TdxW.exe` PID `26392` 保持运行；本轮未启动、关闭、重启或控制通达信，也未控制鼠标或桌面。

## 真实边界

`partial`、`unavailable` 和 mixed 状态均来自实际证据覆盖或本机探针结果。飞书实际发送能力仍取决于用户在设置中提供并启用受保护配置；没有配置时页面显示“未配置”，不会伪造发送成功。
