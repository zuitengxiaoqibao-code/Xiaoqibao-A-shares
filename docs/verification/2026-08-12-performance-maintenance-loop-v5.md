# 一树-A股观测台性能与维护闭环 v5.0 验证报告

## 结论

2026-08-12 已完成真实任务进度、API 核心快速启动与重型服务延迟加载、公司研究六区块增量任务、下次启动原子更新、性能仪表盘、完整快照治理、存储清理与数据新鲜度策略。最终便携 EXE 已重建并通过真实发布数据烟测。

## 功能证据

- 通用任务进度统一使用 `queued/running/succeeded/failed/cancelled`；只有存在真实 `total` 时才计算百分比。
- 公司研究延迟初始化，不进入核心启动路径；六区块任务公开真实 `processed/total`，旧完整缓存可持续展示。
- 待更新版本通过 `pending-update.json` 在下次启动时应用；失败回滚，且 `config/data/news/cache/logs/models/exports/backups` 永不替换。
- 性能采样记录最近十次、P50、P95、失败率和缓存命中率，SQLite 写入不阻塞业务响应。
- 快照使用版本信封和原子替换；partial 禁止覆盖 complete。
- 存储清理必须先预览再确认，只允许可重建缓存和过期日志；新鲜度按盘中行情、市场快照、新闻、财务、研报和日线分别判定。

## 发布烟测中发现并修复的问题

1. 普通 GET 仍被全局写锁串行，导致量化策略在并发首屏请求后超过 30 秒。新增 `test_all_read_only_requests_do_not_wait_for_runtime_write` 先确认超时，再将写锁收缩到非 GET/HEAD/OPTIONS 操作；量化请求恢复为 134ms。
2. `AsyncLazyService.get()` 与真实公司研究服务的 `get(symbol, as_of)` 同名，正式 EXE 返回 500。新增同名代理回归测试先确认 `TypeError`，再将内部实例解析方法改名为 `resolve()`；正式 EXE 公司研究返回 partial 且证据覆盖 0.65。

## 自动化验证

- API 全量：`1267 passed, 1 skipped, 5 warnings`。
- Web 全量：`94 files, 556 passed`。
- TypeScript/Vite production build：成功，2260 个模块转换完成。
- UTF-8/乱码扫描：215 个变更文本文件通过。
- `git diff --check`：通过；只有 Windows 行尾转换提示，没有差异错误。

## 真实便携 EXE 验收

- EXE：`dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`272474B4D541D73642514C944F306D3B989199D1552EF186E8B23BCB39A62D09`
- 文件大小：19,830,580 字节。
- 发布目录：1674 个文件，总计约 2347.3 MB，其中真实持久数据约 2209.2 MB。
- 窗口可见：383ms。
- API 健康可用：5385ms；日志拆分为应用导入 1888ms、生命周期初始化 484ms，其余主要为 PyInstaller/Windows 冷读取与首次本地连接。
- 完整验证：25060ms。
- 请求耗时：首页 10ms，信息总览 5271ms，量化策略 134ms，组合风险 678ms，公司研究 11872ms，通达信专业五类探针合计 1204ms。
- 信息总览：ready。
- 数据源健康：ready。
- 量化策略：partial，市场覆盖 85.00%，本次候选为 0；未生成模拟候选。
- 组合风险：partial，读取 1 个用户真实持仓记录并产生 2 条机械风险提醒。
- 公司研究：partial，600519，证据覆盖 0.65，十项反方审查完整。
- 通达信专业 `Fn/GP/BK/SC/GO`：unavailable；官方专业插件未完成可验证初始化，因此没有代理字段或模拟值。

## 安全与资源释放

- 烟测后 `xiaoqibao.exe` 残留进程为 0，测试端口 18765 残留为 0。
- `config/data/news/cache/logs/models/exports/backups` 八个持久目录全部存在。
- 用户通达信 `TdxW.exe` PID 21920 在烟测后仍保持运行，启动时间仍为 2026-08-12 09:02:43；`127.0.0.1:17709` 仍由该进程监听。
- 本轮未关闭、重启或控制通达信，也未控制鼠标或桌面。

