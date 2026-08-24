# 监控规则模板与中文引导验证

## 变更

- 监控中心增加四个默认停用的中文规则模板：市场风险升高、量化策略风险升高、新闻热点出现、尾盘候选出现。
- 模板提供数据来源、触发条件、用途说明和状态；默认不会自动发送站内、语音或飞书告警。
- 一键启用使用稳定规则 ID，重复启用会更新原规则，不会产生重复规则。
- 默认字段与真实快照对齐：市场/量化使用 `regime.risk_score`，新闻使用 `verified_count`，尾盘使用 `candidate_count`。
- 保留高级规则构建器、旧版单条件规则和后端 DSL 兼容；用户界面主说明不展示英文内部字段路径。
- 模板状态可读为“未启用”“监控中”“最近触发”“暂无数据”，保存和加载失败均显示中文原因。

## 源码与测试

- 提交：`db7379e2efc52848139746cc55ab284ea8080b8c`
- 监控中心定向测试：`10 passed`
- 已完成的全量回归：Web `134` 个测试文件、`772 passed`；API `1698 passed，1 skipped，5 warnings`
- TypeScript/Vite production build：通过
- UTF-8/中文乱码扫描：通过
- `git diff --check`：通过

## 便携 EXE 验证

- EXE：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`7CB5C0A745A7C079FBECD5F088127B5D2FA6856D2010DF23424FC48279024EED`
- 发布清单：`source_state=clean`，迁移版本 `1`，清单签名验证通过
- 热启动 smoke：通过；窗口 `296ms`，API `8011ms`，14/14 菜单门禁通过，缓存首帧不超过 `1s`
- 恢复演练：通过；临时副本校验 `36` 个数据库，迁移版本 `1`，关键 API `pass`
- 发布质量门禁：通过；质量状态为 `warning` 仅因量化策略和公司研究仍为真实 `partial`，没有伪造 `ready`
- 发布目录持续保留 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups`

## 真实数据边界

- 信息总览：`ready`，覆盖率 `99.71%`
- 量化策略：`partial`，12 个候选，因子覆盖 `85%`
- 公司研究：`partial`，标的 `600519`，证据覆盖 `0.65`，反方检查 `10` 项
- 尾盘选股：`partial`，当前扫描到全市场但关键历史字段覆盖不足时如实说明原因，不生成伪造候选
- 无持仓组合风险：`unavailable`（持仓数为 0），不补造持仓或收益
- 通达信专业字段按实际探针保留 `ready/unavailable` 明细；本轮未关闭、重启或控制通达信，也未控制鼠标或桌面

