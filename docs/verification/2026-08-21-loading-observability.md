# 加载状态与研究性能验收

## 实现

- 左侧可转债下方增加全局 AI 与数据任务状态中心。任务由页面请求真实登记、更新、完成或失败；没有活动任务时不轮询，不伪造百分比。
- 公司研究增加后端 30 秒总任务时限和 8 秒单来源时限。诊断、财务、F10 任一来源超时会保留其它真实证据并标记部分状态；前端 35 秒总等待和 10 秒停滞检测均以中文说明失败阶段。
- 个股事件 K 线复用已按股票过滤的候选事件，不再调用告警服务全量扫描；前端保留缓存首屏，后台刷新失败不清空已有图表。
- 网络异常和取消都会关闭全局任务状态，避免永久显示“处理中”。窄屏状态中心保持 12px 可读字号。

## 验证

- API 聚焦：22 passed（公司研究任务、事件 K 线、新闻仓库与新闻告警）。
- API 全量：1652 passed, 1 skipped；仅依赖库弃用警告。
- Web 聚焦：35 passed（任务状态中心、公司研究请求、主界面接入）。
- Web 全量：130 个测试文件，740 passed。
- Ruff、TypeScript/Vite 生产构建、`git diff --check` 通过。
- 最终真实 EXE smoke：窗口 324ms 可见，API 7316ms 就绪，完整验证 19909ms；公司研究与量化策略继续按真实证据返回 partial，不把缺失字段伪装为 ready。
- 恢复演练：36 个数据库、迁移版本 1、关键 API pass。
- 发布质量门禁：通过。数据质量保留真实 warning：量化策略和公司研究为 partial，通达信专业探针为 unavailable，不使用模拟数据替代。

## 交付

- EXE：`dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`1B167BCE9152A12CEFEEB8D0BFA05489AA9B54E76B4DA8C7796DBD8EDC04B117`
- 发布清单：`dist/XiaoQiBao-Portable/release-manifest.json`
- 本次构建保留 `config/data/news/cache/logs/models/exports/backups` 八个持久目录。
