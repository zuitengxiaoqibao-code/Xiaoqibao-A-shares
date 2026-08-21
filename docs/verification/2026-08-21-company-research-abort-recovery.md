# 2026-08-21 公司研究取消恢复验证

## 问题与根因

- 公司研究页面可能显示 `signal is aborted without reason`，随后最新数据加载失败；没有可用缓存时页面无法继续展示研究结果。
- 根因是同一股票的共享请求绑定了第一位调用者的 `AbortSignal`。旧页面或旧控制器取消请求后，新调用者仍复用了已经取消的共享请求。
- 五分钟定时刷新还会中断同一股票仍在执行的研究，并把底层英文异常直接展示给用户。

## 修复内容

- 共享请求被取消时，新调用者自动启动新一代请求，不再继承旧控制器的取消状态。
- 请求账本将主动取消记录为 `cancelled`，不计入普通失败。
- 公司研究存在同股在途请求时，定时刷新等待当前请求完成，不再中断并重启。
- 保留后端返回的中文业务原因；底层英文异常统一转换成明确的中文提示。
- 新增共享请求取消恢复、定时刷新不打断在途研究、英文异常中文化三组回归测试。

## 自动验证

- 聚焦回归：`22 passed`。
- Web 全量：`125` 个测试文件，`717 passed`。
- API 全量：`1587 passed, 1 skipped`。
- TypeScript/Vite 生产构建：通过，`2291` 个模块完成转换。
- 中文乱码扫描与 `git diff --check`：通过。

## 便携 EXE 验收

- staged EXE：`dist/XiaoQiBao-Portable-staged-7bfec30b34054136b0a329274078735b/XiaoQiBao-Portable/xiaoqibao.exe`
- 发布源码提交：`b5830bd3bb0bd60f905ebdc0f4fbdd50a0efeb82`
- `source_state=clean`，`working_tree_dirty=false`。
- EXE SHA-256：`7B898797A8E2F3D1626D63762CE8CA270903CBDE35D79E1863A498E7AD544AA5`，与发布清单一致。
- 发布清单签名：`D3CD768022EB68232025DE0768CC112942FA79A9879C9266C3CABFA2E2E48BF6`。
- 实际 EXE smoke：窗口 `340ms` 可见，API `5640ms` 就绪，完整验证 `18830ms`；公司研究 `2489ms` 返回 `partial`，股票 `600519`、证据覆盖 `0.65`、反方检查 `10` 条。
- `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 八个持久目录全部存在。

## 操作边界

- 用户正在运行的正式 EXE 保持不变；构建器使用 staged 发布并登记为下次正常启动自动应用。
- smoke 只结束本轮自行启动的隔离测试实例，结束后没有 staged EXE、Python 或 Node 测试进程残留。
- 本轮未关闭、重启或控制通达信，未控制鼠标或桌面。
- 通达信专业插件在隔离 smoke 中未初始化，相关字段按真实能力显示 `unavailable` 和中文原因，没有使用模拟数据替代。
