# 2026-08-21 量化研究智能升级验收

## 本轮目标

在现有一树-A股观测台中原生吸收外部量化项目中可验证的方法，不整包复制外部 Web、回测或 HARNESS 代码。新增因子生命周期、因子健康、风险闸门、七类机会、可追溯 Pitch、60 日影子验证、ETF 暴露和 AI 可证伪假设，并保持 EXE 快速启动、缓存优先和真实数据边界。

## 已完成内容

- 因子注册表只纳入七个当前可计算的真实价量因子；重复注册、退休状态和公式版本有明确契约。
- 因子健康按日横截面计算 20/60/120 日 RankIC、方向修正、ICIR、覆盖率和陈旧状态；样本不足不输出伪造统计。
- 风险闸门分别检查证据、可交易性、财务异常、信号冲突和集中度，状态区分 `pass/warn/block/unavailable`。
- 七类机会和类型化失效条件已注册；综合分不转换成概率，同类成熟样本不足 20 条时不展示胜率。
- 影子账本扩展到 `1/3/5/10/20/60` 日，并支持决策来源和机会类型分组。
- ETF 映射要求不少于 60 个共同交易日并通过流动性门槛；AI 只能创建研究草案，必须通过 PIT、walk-forward、成本和 FDR 确定性验证才能接受。
- 新增 `GET /api/v1/a-shares/quant-research` 聚合接口和量化研究智能界面；局部模块失败不清空整页，优先读取 last-good 快照。

## 自动验证证据

- API 全量：`1587 passed, 1 skipped, 5 warnings`，耗时 `83.93s`。
- Web 全量：`125` 个测试文件，`714 passed`，耗时 `20.81s`；便携构建内置复跑结果同样为 `714 passed`。
- Ruff：`All checks passed`。
- TypeScript/Vite 生产构建：通过，`2291` 个模块完成转换。
- 中文源码与设计文档乱码扫描：无产品源码命中；实施计划中的扫描命令示例为唯一自引用命中。
- `git diff --check`：通过。

## 真实 EXE 验收

- 隔离数据 smoke：窗口 `93ms` 可见，API `2500ms` 就绪，完整验证 `11269ms`。
- 真实发布数据 smoke：窗口 `99ms` 可见，API `2382ms` 就绪，完整验证 `26751ms`。
- 真实数据状态：信息总览 `partial`、覆盖率 `99.87%`；来源健康 `ready`；量化策略 `partial`，`12` 个候选、证据覆盖 `85%`；公司研究 `partial`；无持仓的组合风险 `unavailable`。
- 新量化研究接口由真实 EXE 验证：契约版本 `quant-research-intelligence-v1`，七个模块、七个因子完整返回；真实量化候选生成 `12` 张机会卡。
- 量化研究模块状态：因子注册 `ready`；风险和机会 `partial`；因子健康 `insufficient`；ETF 与 AI 假设 `unavailable`。这些状态来自真实证据边界，不使用占位数据提升等级。

## 发布证据

- EXE：`dist/XiaoQiBao-Portable/xiaoqibao.exe`
- 发布清单绑定源码提交：`ff058877a6b124cde43074e60c3bb9e1cd5b8a6e`
- EXE SHA-256：`4AEABE1CC1606FE75364650C56191C3A0FE93936C6A767B40BAF43C199F05DE2`
- 发布清单签名：`D418AF9E0C94C7B20BE9F4ECC3FF02491DD71DF4A44160F91DF23AB0CEDAAC82`
- `source_state=clean`，`working_tree_dirty=false`。
- `config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 八个持久目录均已保留。

## 已知边界

- 第三方 `exchange_calendars` 产生 5 条 NumPy 时间单位弃用警告，不影响本次测试结论。
- Vite 仍提示图表依赖块超过 500 kB；量化页面本身已按路由拆分，但图表依赖的进一步按需加载应作为后续性能治理项。
- 因子健康、ETF 映射和 AI 假设只有在真实横截面历史、ETF 共同样本或确定性研究任务满足门槛后才会提升状态。
- 通达信专业探针只对结构已验证的接口显示 `ready`；语义未映射或客户端插件未初始化的接口继续显示 `unavailable`。

## 安全与操作边界

- 本轮未启动、关闭、重启或控制通达信。
- 未控制鼠标或桌面。
- smoke 和接口验证只结束本轮自行启动的观测台测试进程，测试结束后立即释放。
- 未使用模拟行情、模拟新闻、硬编码胜率或伪造 AI 结论。
