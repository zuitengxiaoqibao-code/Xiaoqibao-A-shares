# 全站加载进度连续反馈验证记录

日期：2026-08-12

## 修复范围

- 公司研究和个股观察共享请求层不再长时间停留在 `1%`。
- 响应头返回前每 `250ms` 更新一次受限阶段估算，百分比从 `1%` 平滑趋近 `45%`，并显示真实等待秒数。
- 阶段估算明确标注“阶段估算”，不冒充后端真实完成度。
- 响应开始传输后切换“真实字节”；有 `Content-Length` 时按实际接收比例推进，无长度时公开已接收字节。
- 数据接收完成后进入“已核验节点”的校验与解析阶段；只有 JSON 成功解析才进入 `100%`。
- 进度单调不倒退，成功、失败或取消都会释放估算计时器。
- 进度轨道增加持续流光，并尊重 `prefers-reduced-motion`。

## 全站审计

当前用户可见百分比进度共三套：

1. 公司研究与个股观察：本轮统一为阶段估算、真实字节、解析完成三段式进度。
2. 信息总览：继续使用桌面启动和市场快照真实阶段节点，已有逐点平滑动画。
3. 量化候选扫描：继续优先使用后端 `processed / total` 真实处理数量；缺少总量时采用不显示虚假百分比的动态轨道。

## 自动化验证

- 共享进度、公司研究、个股观察聚焦测试：`74 passed`。
- Web 全量：`94` 个测试文件、`553 passed`。
- API 全量：`1241 passed, 1 skipped, 5 warnings`；警告为 `exchange_calendars` 上游弃用提示。
- TypeScript/Vite production build：成功，`2260 modules transformed`。
- 严格 UTF-8 与乱码扫描：`208` 个变更文本文件通过。
- `git diff --check`：通过，仅有 Windows 换行提醒。

## 便携 EXE 验收

构建时正式便携程序正在运行，PID 为 `26036` 和 `20860`。按照不控制用户桌面的约束，没有关闭或重启它们；完整新版生成在：

`dist/XiaoQiBao-Portable-staged-d37a8871286344dab29e25f0742766b7/XiaoQiBao-Portable/xiaoqibao.exe`

SHA-256：

`3D75C1B13F19DBF21C68274BEEBF81533E2E94D1417011F12C191EF3A1B48BF8`

新版共 `1670` 个文件，八个持久目录 `config/data/news/cache/logs/models/exports/backups` 全部存在。

真实发布数据 smoke：

- 窗口可见：`351ms`
- API 就绪：`6642ms`
- 首页：`13ms`
- 信息总览：`6079ms`，`ready`
- 量化策略：`32ms`，`partial`
- 组合风险：`108ms`，`partial`
- 公司研究：`5106ms`，`partial`
- 专业字段：`1040ms`，`unavailable`，未使用代理值
- 完整验证：`20054ms`

smoke 只结束自身启动的新版测试实例。用户当前运行的正式观测台及通达信 `TdxW.exe/tdxcef.exe` PID 均保留。

因为本轮为纯前端资源修复，已把新版 `web/index.html` 和新资源以只新增/覆盖、不删除旧资源的方式同步到正式便携目录；没有替换正在运行的 EXE。正式 `web/index.html` SHA-256 为：

`CFB11179B88109B3136C76C2EA5B274734961A863B82E9CAFB59EB39CAC39978`

用户下次自行重新打开正式 EXE 时会加载新版进度反馈。
