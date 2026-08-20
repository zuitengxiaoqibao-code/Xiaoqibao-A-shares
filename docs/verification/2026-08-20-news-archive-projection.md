# 2026-08-20 新闻归档投影与便携发布验证

## 已确认

- 默认个股新闻查询 `NewsRepository.events_for_symbol()` 现在排除 `news_event_archives` 中的事件；原始新闻证据仍保留，归档只改变默认有效投影。
- 新闻热点主列表 `/api/v1/news/events` 改为读取 `effective_events(cutoff=server_time)`，已归档或晚于服务时间的事件不再进入页面和实时新闻快照。
- 回归测试先复现失败，再通过：个股查询归档排除、新闻热点路由有效事件投影均有测试覆盖。

## 验证结果

- API 全量：`1514 passed, 1 skipped, 5 warnings`。
- Web 全量：`122` 个测试文件，`701 passed`；生产构建成功。
- Ruff：通过。
- `git diff --check`：通过。
- 修改文件定向 UTF-8/乱码扫描：通过。
- 新便携 EXE：
  - 路径：`dist/XiaoQiBao-Portable-staged-dc4fcedbd0cc434e86ac547dd3446ac3/XiaoQiBao-Portable/xiaoqibao.exe`
  - SHA-256：`F58287F93FDEF7D55009EA0A5C165EBCE8192DE1A6E02F04A11B2858D32F5715`
  - 正式 release 仍被 PID `17144` 使用，构建器未覆盖正式目录，已写入待更新机制。
- 隔离数据 smoke：通过；窗口 `309ms`、API `5569ms`、完整验证 `17156ms`，公司研究返回 `partial`，未用模拟数据填充。
- 真实发布数据 smoke：信息总览、来源健康、公司研究、专业探针请求均可返回；量化候选后台扫描在 30 秒门槛内未收敛，按真实状态记录为性能边界，未伪报通过。
- 恢复演练：两次在临时副本中被尾盘全市场扫描 `9.008–9.460s` 超过现有 `8s` 门槛阻断；临时目录均已自动清理。该失败与新闻归档投影改动无直接调用链关系，下一步应单独优化尾盘扫描或重新评估门槛，不能把它标成恢复通过。

## 运行约束

- 本轮没有关闭、重启或控制通达信；正式 EXE 未被停止；只释放了本轮自动诊断遗留的 staged 测试 PID `508`。
