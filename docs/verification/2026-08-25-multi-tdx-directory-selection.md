# 多通达信目录与日线主源验证

## 实现

- 新增 `qibao_api.gongbu.tdx_directory_discovery`，只读扫描已知目录和受限搜索目录。
- 默认已知目录包含 `D:\new_tdx_mock`；它不会被强制选为主源，必须通过真实日线证据评分。
- 评分维度为最新交易日、可读取日线数、A 股覆盖率和文件活跃时间，设置页展示评分依据。
- 日线历史按主源优先、低分目录补缺；同一交易日冲突时保留高分目录并避免静默覆盖。
- 新增 `/api/v1/settings/tdx-directories` 查询和 `/api/v1/settings/tdx-directories/select` 手动选择/恢复自动选择接口。

## 本机扫描证据

本次只读扫描发现：

| 目录 | 最新交易日 | 可读取文件 | 覆盖率 | 评分 | 自动结果 |
| --- | --- | ---: | ---: | ---: | --- |
| `D:\new_tdx64` | 2026-08-25 | 9497 | 58.62% | 91.72 | 主源 |
| `D:\new_tdx_mock` | 2026-08-24 | 9475 | 58.64% | 83.66 | 缺口回退源 |

当前结果说明：`D:\new_tdx64` 的最新交易日和可读取量证据更强，因此自动主源选择它；`D:\new_tdx_mock` 仍会参与缺失股票和历史日期回退，不会被忽略。

## 验证结果

- 目录发现、排序和跨目录读取专项：通过。
- API 全量：`1718 passed, 1 skipped`。
- Web 全量：`134` 个测试文件，`780 passed`。
- Web 生产构建：通过。
- 便携构建：通过，使用 staged 目录，未覆盖正在运行的正式 EXE。
- EXE smoke：通过；窗口 `387ms`，API `6074ms`，14/14 菜单性能门禁通过，验证完成 `14456ms`。
- staged EXE：`dist/XiaoQiBao-Portable-staged-1aeb2b10870e4166b76f95e204b9b8b3/XiaoQiBao-Portable/xiaoqibao.exe`。
- staged EXE SHA-256：`E82A7E27207DF22D8EB66DFEB52FFE32010EC4EB3C1616154581C663FAF802FE`。
- smoke 结束后新增 `xiaoqibao.exe` 残留为 `0`；用户原正式程序仍保持运行。
- 通达信进程未关闭、重启或控制。

质量门禁仍提示历史发布清单存在旧编码诊断文本警告；不影响本次 EXE 启动、目录评分或日线读取。
