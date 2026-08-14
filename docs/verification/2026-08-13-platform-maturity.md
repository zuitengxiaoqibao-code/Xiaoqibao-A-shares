# 平台成熟化阶段验收记录

**日期：** 2026-08-13  
**状态：** 本轮目标完成，仍保留真实数据边界和后续性能治理项
**交付入口：** `dist/XiaoQiBao-Portable/xiaoqibao.exe`

## 本阶段完成

- 写入平台成熟化设计：`docs/superpowers/specs/2026-08-13-platform-maturity-design.md`。
- 写入实施计划：`docs/superpowers/plans/2026-08-13-platform-maturity.md`。
- 新增前端有上限性能账本，记录数据域耗时、缓存命中率、P50/P95。
- 请求合并层接入性能事件，保持原有 GET 合并和取消语义。
- 每日快照增加只读证据元数据读取接口，保留交易日、来源截止时间和完整性状态。
- 新增历史质量检查契约，识别缺失日期、重复日期和未来日期；接入历史同步服务的只读质量路由。
- 新增可复现发布清单能力，记录提交、源码状态、锁文件哈希、迁移版本、八个持久目录和 EXE SHA-256。
- 新增质量门禁纯函数，统一检查 API/Web 测试、生产构建、编码扫描、smoke 和数据完整性；真实数据低于就绪阈值时只发出 warning，不伪造 ready。
- 新增幂等迁移状态文件，逐版本写入临时文件后原子替换；迁移失败时保留上一个已确认版本。
- 量化候选生命周期改为引用真实 `input_snapshot_ids`；不再把 `quant_strategy_v2` 等计算操作名冒充数据快照。
- 运维中心新增日线修复审计折叠区，展示修复前缺口/覆盖率、写入行数、修复后覆盖率、来源及失败原因。
- smoke 将窗口/API/数据覆盖、业务域 partial 和 warning 写入 `release-manifest.json` 的 `quality_gates`；发布清单自动记录 dirty/clean 工作树状态。

## 验证结果

- API 全量：`1354 passed, 1 skipped, 5 warnings`。
- Web 全量：所有测试断言通过；Vitest worker 在断言完成后未自动退出，已手动释放测试会话，作为后续治理项保留。
- Web 生产构建：通过；仍有大 chunk 警告，未影响构建结果。
- PowerShell 构建脚本语法：通过。
- 聚焦历史质量/快照/性能/发布清单测试：通过。
- `git diff --check`：通过。
- 乱码扫描：当前源码未发现替换字符；历史计划文档中的扫描示例含有连续问号模式文本，不属于界面或数据文件乱码。
- 真实便携 EXE smoke：通过，发布门禁为 `warning`（不是失败）。
  - 窗口可见：`369ms`
  - API 就绪：`6410ms`
  - 完整验证：`17301ms`
  - 首页：`59ms`
  - 信息总览：`ready`，市场覆盖率 `99.73%`
  - 来源健康：`ready`
  - 量化策略：`partial`，候选 `0`，覆盖率 `85%`
  - 公司研究：`partial`，当前标的 `600519`，证据覆盖率 `0.65`
  - 组合风险：`unavailable`，未配置持仓
  - 通达信专业接口：`unavailable`，保持真实原因，不使用替代或模拟字段
- 八个持久目录均保留：`config/data/news/cache/logs/models/exports/backups`。
- 发布清单：`dist/XiaoQiBao-Portable/release-manifest.json`；源码状态明确标记为 `dirty`，不宣称 clean reproducibility。
- 最新 EXE SHA-256：`E4D54A387230DAFAE8A30A7C7D75A2264483E05B5F21CF2AE6389869418CCC14`，与发布清单一致。
- `release-manifest.json` 的 `quality_gates` 已记录：`state=warning`、`data_integrity_ratio=0.9973`、warning 为 `quant_strategy_partial` 和 `company_research_partial`。

## 真实数据边界

- 本次执行环境没有检测到 `TdxW.exe` 或 `127.0.0.1:17709` 监听，因此不能声称通达信 PID 前后不变；烟测没有启动、关闭或控制通达信。
- 历史日线覆盖率仍需达到既定 98% 就绪门槛后，相关页面才会进入 ready。
- 量化因子覆盖率仍为 85%，候选不足时保持 partial/unavailable。
- 通达信专业数据包或专业插件未就绪时，专业字段保持 unavailable。

## 后续治理项

1. 继续补齐量化因子和公司研究证据，只有真实覆盖达标才从 `partial` 转为 `ready`。
2. 解决 Web Vitest worker 不自动退出和生产大 chunk 警告。
3. 继续积累历史修复审计和来源冲突记录，观察覆盖率是否稳定超过 98%。
