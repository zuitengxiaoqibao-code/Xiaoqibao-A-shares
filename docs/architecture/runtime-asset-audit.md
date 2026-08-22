# 运行时资产与删除门禁

## 结论

当前没有同时满足以下四项证据的运行时文件，因此本轮不做推测性删除：

1. Vite 构建图不可达。
2. Python 导入与 FastAPI 路由图不可达。
3. PyInstaller `xref-xiaoqibao.html` 和发布包含清单均未引用。
4. 全量测试、菜单契约和恢复演练均不依赖。

测试、计划、验证文档、迁移文件、恢复脚本和八个持久目录不属于可删除候选。它们即使不进入前端运行包，也承担回归、数据兼容或灾备职责。

## 当前分包

- 入口包只保留应用壳、信息总览与共享运行时。
- 公司研究、量化分析、新闻、首板、尾盘、风险、设置和运维按路由动态加载。
- React、ECharts、图标和字体进入独立 vendor chunk。
- EXE 由 PyInstaller 分析图确定 Python 模块和二进制依赖。

## 运行时边界

- `main.py` 是兼容装配入口，领域实现分别位于 `a_shares`、`operations`、`routes`、`storage`、`tasks` 和 `zhongshu`。
- 页面请求只读取首屏快照；外部采集、全市场扫描和 AI 分析通过后台任务运行。
- 便携发布必须保留 `config`、`data`、`news`、`cache`、`logs`、`models`、`exports` 和 `backups`。

后续只有四项证据重新收集并全部成立时，才允许删除候选文件。删除后必须重新运行 API/Web 全量、生产构建、真实 EXE smoke 和恢复演练。
