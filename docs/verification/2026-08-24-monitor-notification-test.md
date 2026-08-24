---
type: verification
status: confirmed
date: 2026-08-24
scope: monitor-notification-test-and-navigation
---

# 监控中心提醒测试与菜单顺序验收

## 已完成

- 监控中心新增“提醒通道测试”区域。
- “测试语音提醒”调用真实语音合成接口并播放音频，成功、合成失败、空音频、播放失败均有中文状态。
- “测试飞书消息”调用真实飞书测试接口，显示送达、未配置或失败原因；不显示 webhook 原文。
- 规则卡片操作区增加稳定的最小高度并底部对齐，说明文字长短不同不再造成暂停/恢复/停止删除按钮上下错位；窄屏保持整体换行。
- 菜单顺序调整为“历史复盘 → 监控中心 → 数据设置”，保持一级平铺，不增加分类层级。

## 测试结果

- Web 全量：134 个测试文件，777 passed。
- API 全量：1702 passed，1 skipped，5 warnings。
- Web 监控中心与导航定向：21 passed。
- API 通知设置与语音路由定向：11 passed。
- TypeScript/Vite 生产构建：通过。
- `git diff --check`：通过。

## EXE 验收

- EXE：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`1DF31541B19B84837002719BC2A2ECB47BB306AEA984A9A89822BA25F4FCB284`
- 绑定提交：`9a215c5ff2eb724154caeea36f6652e43a958026`
- 热启动 smoke：窗口 104ms、API 2638ms、完整验证 9901ms。
- 14 菜单真实性门禁：14/14 通过。
- 恢复演练：36 个数据库、迁移版本 1、关键 API 通过。
- 发布质量门禁：通过，签名清单校验通过。

## 真实边界与操作边界

没有飞书配置时，测试按钮保持不可用并显示“未配置”；未把未配置伪造成送达。真实数据覆盖率和 `partial/unavailable` 状态继续按证据展示。

本次只启动自动化 EXE smoke 和恢复演练实例，没有关闭、重启或操作通达信，没有控制鼠标或桌面；测试完成后自动化实例已退出。
