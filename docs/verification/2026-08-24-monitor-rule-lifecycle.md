---
type: verification
status: confirmed
date: 2026-08-24
scope: monitor-rule-lifecycle
---

# 监控规则生命周期验收

## 功能范围

监控中心规则现在支持完整生命周期：

- 已启用规则可以“暂停监控”，暂停后不再评估新快照，并关闭活跃告警。
- 已暂停规则可以“恢复监控”，恢复后重新进入实时评估。
- 已暂停规则可以“停止并删除”，删除前需要二次确认；历史告警和审计记录保留。
- 条件可以逐条增加或删除；最后一条条件的删除按钮置灰，并提示至少保留一个条件。
- 模板规则和用户规则使用同一组状态操作，状态在刷新后保持。

后端接口：

- `PATCH /api/v1/monitor-center/rules/{rule_id}/status`
- `DELETE /api/v1/monitor-center/rules/{rule_id}`

## 验证结果

- Web 全量：134 个测试文件，775 passed。
- API 全量：1702 passed，1 skipped，5 warnings。
- 监控中心前端定向：13 passed。
- 监控中心后端定向：21 passed。
- TypeScript/Vite 生产构建：通过。
- `git diff --check`：通过。

暂停、恢复、删除和条件操作均有定向回归覆盖；实时运行链路另有最小端到端验证，确认连续确认、恢复和规则状态落盘可生效。

## Windows 交付证据

- EXE：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`CA20A731178DA14342E7B6C43A2641D38E47CDDCA332EC7444F88EB00AF66411`
- 绑定源码提交：`d118123`
- portable smoke：窗口 89ms，API 3823ms，14/14 菜单门禁通过。
- 恢复演练：36 个数据库通过，迁移版本为 1，关键 API 通过。
- 发布质量门禁：通过。

## 真实数据边界

发布包继续按证据状态展示真实数据，不用模拟值填充缺口：信息总览覆盖率约 99.67%；量化策略为 `partial`（12 个候选、约 85% 覆盖）；公司研究为 `partial`（600519、证据覆盖约 0.65）；无持仓组合风险为 `unavailable`；通达信专业字段按本机探针显示 `ready` 或 `unavailable`。

当前发布目录没有已保存的 `monitor-center.json` 时，不会凭空产生告警；用户需要先保存并启用规则。飞书未配置时只保留站内告警，不宣称已发送。

## 操作边界

本次验证只启动了自动化 EXE smoke 和恢复演练实例；没有关闭、重启或操作通达信，没有控制鼠标或桌面。测试完成后自动化实例已退出。
