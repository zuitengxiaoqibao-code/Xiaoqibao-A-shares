# 全站速度、数据与信息架构最终验证

## 发布结果

- EXE：`dist/XiaoQiBao-Portable/xiaoqibao.exe`
- 源码提交：`ad3781e1ef11027b8e1e7cf7f684a217619a7910`
- EXE SHA-256：`42AE39DB4D09020CC402F549C96AFCDFCAD1AF0622448644BCD38D21D8F92CB7`
- 八个持久目录：`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 全部保留。

## 自动验证

- API 全量：`1664 passed, 1 skipped`。
- Web 全量：`133 files / 755 tests passed`。
- Ruff、TypeScript、Vite 生产构建、`git diff --check`：通过。
- 14 菜单性能门禁自测：4 项通过。
- 启动性能门禁自测：3 项通过。
- 恢复演练：36 个数据库、迁移版本 1、关键 API `pass`。
- 发布质量门禁和清单签名：通过。

## 真实 EXE 性能

- 主窗口可见：229ms。
- API 就绪：2956ms。
- 首页请求：210ms。
- 信息总览：3334ms。
- 量化策略：41ms。
- 公司研究：108ms。此前 18.45 秒的重型懒服务前置问题已由版本仓库快路径消除。

恢复副本验证为窗口 264ms、API 3205ms、信息总览 4007ms、量化 37ms、公司研究 105ms。

## 真实数据边界

- 信息总览：`partial`，覆盖率 99.88%。
- 量化策略：`partial`，12 个真实候选，证据覆盖 85%。
- 公司研究：`partial`，600519，证据覆盖 0.65，10 项反方检查。
- 无真实持仓时组合风险：`unavailable`。
- 通达信专业字段：探针返回 `unavailable`，未使用普通行情或模拟值替代。

本轮未关闭、重启或控制通达信，未控制鼠标或桌面。
