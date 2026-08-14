# 真实决策闭环 v3.0 验证记录

日期：2026-08-11

## 交付边界

- 唯一用户交付入口为 Windows 便携 EXE。
- 所有候选、评分、市场状态、公司研究、新闻事件和专业字段均遵循真实数据状态；缺失时返回 `partial / unavailable / insufficient`，不随机生成、不缺失补零、不用代理数据冒充。
- 全程未关闭、重启或控制通达信。

## 已完成能力

1. 日线修复中心：提供覆盖水位、主导交易日、缺口分类、修复任务创建/暂停/继续和失败原因；读取状态不触发网络。
2. 策略影子账本：冻结当时证据，按真实后续日线评估 1/3/5/10/20 日表现，并区分成熟度、MFE、MAE 和失效状态。
3. 启动性能：将旧复盘缓存 DuckDB 校验、全市场行情/复盘扫描、板块资金采样和量化候选扫描移出首屏关键路径；路由代码预加载不提前发起无关业务请求。
4. 公司研究时效：机构预测保留机构、报告日、预测年度、机构数量、最新报告日和过期边界；证据不足时明确降级。
5. 新闻公告联动：已核验公告和新闻进入统一事件图与 K 线映射；未核验关联明确显示“关联待核验”，不强行绑定股票或板块。
6. 数据源治理：设置页数据源健康默认折叠，读取后台快照；通达信专业能力使用六步只读恢复向导，明确检测、失败步骤和可执行说明。
7. 真实性门槛：市场水位仅在覆盖率至少 98% 且无阻塞项时为 `ready`；候选漏斗按完整 eligible 集合计数；少于 5 笔闭合交易时不展示分段回测证据。

## 自动化验证

### API

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest apps\api\tests -q
```

结果：`1219 passed, 1 skipped, 5 warnings in 43.74s`。

### Web

命令：

```powershell
cd apps\web
npm test -- --run
npm run build
```

结果：

- `90 passed` 测试文件。
- `542 passed` 测试。
- TypeScript 与 Vite production build 通过，2255 个模块完成转换。

### 便携 EXE

构建命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-portable.ps1
```

构建结果：成功；发布目录 1663 个文件，约 2132.6MB。

真实发布数据 smoke：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run-portable-smoke.ps1 -UseReleaseData
```

结果：

- 窗口可见：75ms。
- API 就绪：2074ms。
- 首页请求：36ms。
- 信息总览请求：454ms，状态 `ready`。
- 量化策略请求：12ms，状态 `partial`，覆盖率 85%，候选 0。
- 通达信专业五类探针：1145ms，均为真实 `unavailable`。
- 完整验证：4357ms。
- smoke 结束后只终止自身 EXE 和自身进程池子进程，无本程序残留进程。

烟测脚本同时修复了持久日志误判：现在只读取本次进程启动后新增的日志字节，不会把上一次的 `lifespan-ready` 当作本次就绪并过早探测预绑定端口。

## 启动根因与改进

原始阻塞链：

`LocalMarketReviewSource.__init__ -> _load_cache -> cache_is_stale -> BarRepository.trade_dates`

便携版冷启动因此首次打开约 79MB DuckDB，构造阶段约 5.14 秒，整个 `market-review-cache-ready` 约 5.56 秒。

修复后：

- 便携版构造期延迟旧复盘缓存校验，旧缓存不会冒充最新数据。
- 本地全市场行情与复盘首次后台扫描延后 15 秒。
- 市场总览后台刷新给予缓存响应 1 秒首屏宽限。
- 板块资金采样首次执行延后 30 秒。
- 最新日志 `lifespan-ready elapsed_ms=406`。

## 真实不可用边界

通达信官方 Python 专业接口五类方法当前均返回 `unavailable`。真实原因是官方专业接口初始化或调用失败，需要通达信客户端已打开并完成专业插件初始化。程序没有控制通达信，也没有用普通行情、缓存拼接值或模拟值填充这些字段。

## 发布物

- EXE：`dist\XiaoQiBao-Portable\xiaoqibao.exe`
- SHA-256：`59A8F07822FB835A057A95EFC59B826601EA75D4CFED5AE544B36A8A39FE09C2`
- 持久目录：`config`、`data`、`news`、`cache`、`logs`、`models`、`exports`、`backups` 均存在并在重建后保留。
