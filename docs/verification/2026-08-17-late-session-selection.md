# 尾盘选股验证记录

## 实现范围

- 新增一级菜单“尾盘选股”和稳定路由 `/late-session-selection`。
- 新增后端接口 `/api/v1/a-shares/late-session-selection`。
- 七项规则严格判定：14:30–15:00 时间窗口、涨幅 3%–6%、量比 2–5、换手率 6%–15%、市值 60–300 亿元、近 20 个交易日出现涨停、最新价高于真实分时均价。
- 14:30 前返回预筛候选；14:30–15:00 返回实时监控状态；15:00 后冻结收盘状态。
- 六类尾盘行为使用观察/风险提示/待核验标签，缺失分时或指数证据时不使用代理值。

## 测试证据

- API 全量：1419 passed, 1 skipped, 5 warnings。
- Web 全量：120 test files, 676 passed。
- Web TypeScript/Vite 生产构建：通过。
- Ruff、`git diff --check`、UTF-8/乱码扫描：通过。

## EXE 证据

- EXE：`D:/Users/90090/Documents/金融财经/.worktrees/a-share-daily-research/dist/XiaoQiBao-Portable/xiaoqibao.exe`
- SHA-256：`291FD839956D72931207492876A331A570F002E59FFF79F3CF787586ACF40EEF`
- 发布清单签名：`060C7C0B6281092839AC652E742550BCDA30968784D6AD3522E01590D65AA538`
- 真实发布数据 smoke：通过；窗口可见 338ms，API 就绪 7612ms，完整验证 36795ms。
- 信息总览 ready，行情覆盖 99.9%；量化策略 partial（12 个真实候选、因子覆盖 85%）；公司研究 partial（600519、证据覆盖 0.65、反方检查 10 项）；通达信专业接口 unavailable。质量门禁为 warning，仅表示真实数据边界，不把 partial 冒充 ready。
- 本轮未关闭、重启或控制通达信，未控制鼠标或桌面。

## 已知真实边界

- 本地通达信快照是否提供分时黄线、换手率和市值取决于当前桥接字段；缺失时尾盘候选为空或仅预筛部分可用。
- “毫秒级”不做虚假承诺；页面展示本地接口实际刷新周期（实时窗口目标为 1000ms，数据源自身可能更慢）。
