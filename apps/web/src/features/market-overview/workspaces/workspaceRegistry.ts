import type { WorkspaceBlock, WorkspaceDefinition, WorkspaceEvidence } from "./workspaceTypes";

const quoteTruth = "价格与成交只取本地通达信当前快照；代表股票集合不是全市场完整排名。";
const newsTruth = "只展示已写入本地新闻库且已关联 A 股代码的资讯，未核验内容会明确标记。";
const historyTruth = "只有本地日线窗口完整时才给出历史结论，覆盖不足时保持未验证。";
const seatTruth = "只采用东方财富公开龙虎榜的上榜日期、席位名称和买卖金额；缺失时不使用成交额替代。";
const orderTruth = "当前接口没有逐笔委托队列，开盘缺口不能解释为真实隔夜单或封单金额。";
const flowTruth = "当前接口未提供真实大单净流入，成交额只表示活跃度，不能解释为主力方向。";

const b = (kind: WorkspaceBlock["kind"], title: string, variant: string, size: WorkspaceBlock["size"] = "half"): WorkspaceBlock => ({ kind, title, variant, size });

function define(
  label: string,
  family: string,
  layout: string,
  question: string,
  beginnerGuide: string,
  truthBoundary: string,
  requiredEvidence: WorkspaceEvidence[],
  blocks: WorkspaceBlock[],
): WorkspaceDefinition {
  return { label, family, layout, question, beginnerGuide, truthBoundary, requiredEvidence, blocks };
}

export const WORKSPACE_DEFINITIONS: WorkspaceDefinition[] = [
  define("盘中异动", "竞价与盘中", "intraday-command", "盘中何时发生了可验证的价格、题材或资讯异动？", "先沿时间线看触发时刻，再核对关联股票和新闻来源。", `${quoteTruth}${newsTruth}`, ["realtime-quotes", "local-news"], [
    b("event-timeline", "盘中异动时间线", "minute-anchor", "wide"), b("news-wire", "异动关联资讯", "linked-only", "half"), b("sector-heatmap", "异动板块扩散", "event-sector", "half"),
  ]),
  define("异动语音播报", "竞价与盘中", "voice-control", "哪些最新异动需要按优先级进入语音队列？", "先听风险和强度变化，再回到事件原文核验，不把语音当成交易指令。", newsTruth, ["local-news"], [
    b("event-timeline", "待播异动队列", "voice-priority", "tall"), b("data-audit", "语音引擎状态", "tts-runtime", "half"), b("news-wire", "播报原文核验", "voice-source", "wide"),
  ]),
  define("AI+题材", "题材与板块", "theme-evidence-ai", "题材新闻是否得到关联股票和板块行情的同向验证？", "先看证据数量，再看关联股表现；AI 只解释证据，不负责补数据。", `${newsTruth}AI 不生成缺失行情或确定性收益预测。`, ["local-news", "realtime-quotes"], [
    b("theme-atlas", "AI 题材证据卡", "ai-evidence", "wide"), b("evidence-map", "新闻到股票证据链", "theme-link", "half"), b("stock-matrix", "题材行情验证", "theme-confirm", "half"),
  ]),
  define("隔夜单/抢筹", "竞价与盘中", "overnight-gap", "哪些股票出现显著开盘缺口，且当前价格仍在确认强度？", "高开只是结果，必须区分高开高走和高开回落，并查看委托数据是否可用。", orderTruth, ["realtime-quotes", "order-book"], [
    b("auction-gap", "高开缺口分布", "overnight", "wide"), b("stock-ranking", "抢筹观察榜", "gap-strength", "half"), b("data-audit", "隔夜委托证据", "order-book-missing", "half"),
  ]),
  define("竞价封单", "竞价与盘中", "seal-ladder", "竞价阶段有哪些股票接近或达到涨停，封单证据是否真实可得？", "只把实时价格状态当成已验证，封单金额缺失时不要推断排队强弱。", orderTruth, ["realtime-quotes", "order-book"], [
    b("limit-ecology", "竞价封板状态梯", "auction-seal", "third"), b("auction-gap", "开盘强度对照", "seal-gap", "third"), b("data-audit", "封单字段审计", "seal-order-book", "third"), b("stock-ranking", "竞价强势股票", "seal-watch", "wide"),
  ]),
  define("板块精选", "题材与板块", "sector-selection", "哪些板块同时具备涨幅、上涨广度、涨停扩散和成交确认？", "优先观察强度和广度同时靠前的板块，再进入成分股核验。", `${quoteTruth}板块成交额是活跃度，不等于净流入。`, ["realtime-quotes", "sector-membership"], [
    b("sector-quadrant", "板块强度四象限", "strength-breadth", "wide"), b("sector-heatmap", "精选板块热力", "selection", "half"), b("sector-members", "领涨成分验证", "leaders", "half"),
  ]),
  define("涨停板", "涨停生态", "limit-wall", "当前有多少股票严格封在涨停价，集中在哪些板块？", "先看封板与炸板是否分离，再看涨停是否有板块扩散；涨停当日不追涨。", quoteTruth, ["realtime-quotes"], [
    b("limit-ecology", "涨停生态总表", "sealed", "wide"), b("limit-board", "已封涨停清单", "strict-limit", "tall"), b("sector-heatmap", "涨停板块集中度", "limit-cluster", "half"),
  ]),
  define("连板表现", "涨停生态", "height-pyramid", "连续涨停的高度、晋级和失败结构是否具备完整历史证据？", "先确认本地日线覆盖，再看高度；覆盖不足时只能看当前强势，不能称为连板。", historyTruth, ["realtime-quotes", "daily-history-previous"], [
    b("height-pyramid", "连板高度金字塔", "history-required", "wide"), b("history-audit", "连板历史覆盖", "consecutive-days", "half"), b("stock-ranking", "当前强势候选", "not-confirmed-chain", "half"),
  ]),
  define("龙头晋级", "涨停生态", "promotion-pipeline", "强势股票从候选到前排需要通过哪些可验证条件？", "晋级是条件流程，不是收益预测；任何一项失效都回到观察。", `${quoteTruth}${historyTruth}`, ["realtime-quotes", "daily-history-previous", "local-news"], [
    b("promotion-funnel", "龙头晋级漏斗", "gate-by-gate", "wide"), b("rule-gates", "晋级条件与阻断", "leader-rules", "half"), b("risk-board", "晋级失败信号", "promotion-risk", "half"),
  ]),
  define("竞价异动", "竞价与盘中", "auction-radar", "哪些股票的开盘价相对昨收出现显著正负缺口？", "先辨别高开或低开，再看现价是否延续；缺口不代表委托方向。", orderTruth, ["realtime-quotes"], [
    b("auction-gap", "开盘缺口分布", "positive-negative", "wide"), b("stock-matrix", "竞价异动矩阵", "gap-vs-now", "half"), b("risk-board", "高开回落与低开修复", "auction-failure", "half"),
  ]),
  define("竞价选股", "竞价与盘中", "auction-screener", "哪些股票通过开盘缺口、当前确认、成交活跃和风险闸门？", "只有所有规则都通过才进入观察池，缺少委托数据时自动降低证据等级。", orderTruth, ["realtime-quotes", "order-book"], [
    b("auction-gates", "竞价筛选闸门", "deterministic", "wide"), b("stock-ranking", "规则通过候选", "auction-pass", "half"), b("data-audit", "竞价字段完整度", "auction-coverage", "half"),
  ]),
  define("板块赛道", "题材与板块", "sector-race", "板块之间的涨幅、广度和成交活跃度如何轮动？", "横向比较赛道，不用单一涨幅判断持续性；成交额只作活跃度参考。", quoteTruth, ["realtime-quotes", "sector-membership"], [
    b("sector-heatmap", "赛道轮动热力", "rotation", "wide"), b("sector-quadrant", "涨幅与广度矩阵", "race", "half"), b("distribution", "赛道强弱分层", "sector-bands", "half"),
  ]),
  define("板块涨停", "涨停生态", "sector-limit-spread", "涨停股票是否在板块内形成扩散，而不是单点封板？", "看涨停家数的同时必须看板块股票总数和上涨家数。", quoteTruth, ["realtime-quotes", "sector-membership"], [
    b("sector-performance", "板块涨跌与领涨对照", "rise-fall", "wide"), b("sector-heatmap", "板块涨停扩散", "limit-count", "half"), b("limit-board", "板块涨停成员", "sector-limit", "half"), b("sector-members", "同板块跟随强度", "limit-followers", "wide"),
  ]),
  define("炸板", "涨停生态", "failure-lab", "哪些股票触及涨停后未能封住，当前回落了多少？", "炸板是风险状态，先看回落幅度和市场封板率，不做自动反包推断。", quoteTruth, ["realtime-quotes"], [
    b("failure-board", "炸板风险台", "strict-broken", "wide"), b("limit-ecology", "封板与炸板对照", "seal-failure", "half"), b("risk-board", "炸板风险分层", "drawdown", "half"),
  ]),
  define("题材库", "题材与板块", "theme-library", "本地资讯中有哪些可追溯题材，各自关联多少证据与股票？", "把题材当索引而非结论；点击前先看来源数量和最后更新时间。", newsTruth, ["local-news"], [
    b("theme-atlas", "题材索引库", "catalog", "tall"), b("evidence-map", "题材证据档案", "source-count", "half"), b("stock-matrix", "题材关联股票", "theme-members", "wide"),
  ]),
  define("情绪周期", "排名与统计", "regime-engine", "A 股当前属于哪一种短线市场风格，策略应如何切换？", "先定市场风格，再选策略模型，最后等待个股触发条件。", quoteTruth, ["realtime-quotes"], [
    b("market-pulse", "市场风格仪表", "regime", "wide"), b("strategy-route", "策略模型路由", "regime-map", "half"), b("data-audit", "原始因子覆盖", "factor-coverage", "half"),
  ]),
  define("游资追踪", "资金与席位", "seat-ledger", "当前是否取得可验证的龙虎榜席位买卖记录？", "只有席位名称、买卖额和上榜日期完整时才谈游资行为。", seatTruth, ["dragon-tiger-seats"], [
    b("seat-tracker", "席位净额追踪榜", "verified-seats", "wide"), b("review-summary", "席位覆盖仪表", "dragon-tiger", "half"), b("data-audit", "席位来源与字段审计", "seat-source", "half"),
  ]),
  define("游资动向", "资金与席位", "seat-flow-map", "真实龙虎榜席位在股票间如何形成净买入与净卖出分布？", "先看方向分布和净额，再核对具体席位；没有席位记录时不使用热点或成交额代替。", seatTruth, ["dragon-tiger-seats"], [
    b("seat-direction", "席位买卖方向分布", "buy-sell-net", "wide"), b("review-summary", "龙虎榜资金概览", "dragon-tiger", "half"), b("data-audit", "动向证据边界", "seat-fields", "half"),
  ]),
  define("人气榜", "排名与统计", "popularity-rank", "哪些代表股票在涨幅、成交和资讯关联上获得更高关注？", "人气分只用于排序关注，不代表买入价值或全市场官方人气。", quoteTruth, ["realtime-quotes", "local-news"], [
    b("stock-ranking", "综合人气榜", "attention-score", "wide"), b("distribution", "人气构成分布", "score-parts", "half"), b("news-wire", "上榜资讯依据", "popular-evidence", "half"),
  ]),
  define("七大人气榜", "排名与统计", "seven-leaderboards", "涨幅、成交、振幅、开盘、涨停、题材和异动七种口径的榜首是谁？", "七榜用于交叉观察，重复上榜表示多维活跃，不等于确定性强势。", quoteTruth, ["realtime-quotes", "local-news"], [
    b("seven-rankings", "七大人气榜单", "seven-factors", "wide"), b("stock-matrix", "重复上榜矩阵", "cross-rank", "half"), b("data-audit", "榜单口径说明", "rank-method", "half"),
  ]),
  define("百日新高", "排名与统计", "hundred-day-audit", "哪些股票在完整 100 交易日日线中创出新高？", "必须先通过 100 日覆盖检查；仅凭今日涨幅不能判定百日新高。", historyTruth, ["daily-history-100"], [
    b("history-audit", "100 日历史覆盖审计", "new-high", "wide"), b("stock-ranking", "已验证新高清单", "verified-only", "half"), b("data-audit", "未验证原因", "history-gaps", "half"),
  ]),
  define("百日新高趋势", "排名与统计", "new-high-path", "已验证新高股票处于突破、回踩还是失效阶段？", "先确认新高事实，再分析距离高点和回撤；历史不足时不生成趋势标签。", historyTruth, ["daily-history-100"], [
    b("history-audit", "新高趋势阶段", "trend-stage", "half"), b("distribution", "距离高点分布", "distance-high", "half"), b("risk-board", "新高失效检查", "trend-failure", "wide"),
  ]),
  define("区间统计", "排名与统计", "interval-distribution", "在可验证区间内，股票收益、振幅和成交如何分布？", "区间统计必须说明起止日和覆盖样本，当前快照不能冒充历史区间。", historyTruth, ["daily-history-100"], [
    b("distribution", "区间收益分布", "selected-window", "wide"), b("history-audit", "区间样本覆盖", "interval", "third"), b("stock-ranking", "区间强弱榜", "interval-return", "third"), b("data-audit", "统计口径", "interval-method", "third"),
  ]),
  define("热点播报", "资讯与研究", "hot-news-stream", "最新 A 股关联热点按时间和重要性如何播报？", "先听摘要，再看原文来源、发生时间和关联股票，不把播报当建议。", newsTruth, ["local-news"], [
    b("news-wire", "A 股热点播报流", "chronological", "tall"), b("theme-atlas", "播报题材索引", "broadcast-tags", "half"), b("event-timeline", "热点时间轴", "broadcast-time", "wide"),
  ]),
  define("题材挖掘", "题材与板块", "theme-discovery", "哪些题材在多条新闻、异动和股票关联中正在扩散？", "多源重复出现比单条新闻更可靠，但共现仍不等于基本面兑现。", newsTruth, ["local-news", "realtime-quotes"], [
    b("evidence-map", "题材共现网络", "discovery", "wide"), b("theme-atlas", "扩散题材排行", "evidence-growth", "half"), b("stock-matrix", "题材股票共振", "discovery-stocks", "half"),
  ]),
  define("概念叠加", "题材与板块", "concept-overlap", "哪些股票同时关联多个已验证题材，叠加是否过度拥挤？", "叠加题材只说明信息关联数量，多标签不自动提高胜率。", newsTruth, ["local-news"], [
    b("theme-matrix", "股票-题材叠加矩阵", "overlap", "wide"), b("stock-ranking", "概念叠加榜", "theme-count", "half"), b("risk-board", "题材拥挤提示", "crowding", "half"),
  ]),
  define("龙头梯队", "涨停生态", "leader-swimlanes", "强势股票如何分为前排、容量中军、跟随和风险层？", "梯队按当前可验证状态分层，不把一次涨幅当成永久龙头身份。", quoteTruth, ["realtime-quotes", "sector-membership"], [
    b("leader-lanes", "龙头梯队泳道", "front-middle-follow", "wide"), b("sector-members", "同板块队列", "leader-sector", "half"), b("risk-board", "梯队降级信号", "lane-risk", "half"),
  ]),
  define("涨停复盘啦", "涨停生态", "limit-review", "收盘后涨停、炸板和跌停三类状态分别说明什么？", "先复盘事实，再归因板块，最后写次日纪律；涨停当日不追买。", quoteTruth, ["realtime-quotes", "sector-membership"], [
    b("review-columns", "涨停生态三栏复盘", "limit-broken-down", "wide"), b("sector-heatmap", "涨停板块归因", "review-sector", "half"), b("rule-gates", "次日观察纪律", "next-day", "half"),
  ]),
  define("复盘统计大全", "排名与统计", "market-review-book", "盘后市场广度、涨跌停、板块和数据质量如何汇总？", "总量指标用于认识市场结构，不直接生成个股买卖结论。", quoteTruth, ["realtime-quotes", "sector-membership", "local-news"], [
    b("statistics-pivot", "A 股复盘统计透视", "market-close", "wide"), b("distribution", "涨跌分布", "breadth-close", "half"), b("data-audit", "复盘数据完整度", "review-coverage", "half"),
  ]),
  define("异动统计大全", "排名与统计", "anomaly-pivot", "异动按方向、时段、题材和股票如何分布？", "统计只覆盖本地已保存异动，零记录不代表市场从未发生异动。", newsTruth, ["local-news"], [
    b("statistics-pivot", "异动统计透视", "direction-theme-time", "wide"), b("event-timeline", "异动时段分布", "session", "half"), b("theme-atlas", "异动题材排行", "anomaly-theme", "half"),
  ]),
  define("AI+选股", "资讯与研究", "ai-rule-selection", "确定性量价和题材规则能否形成可解释候选？", "规则先筛选，AI 后解释；没有触发和风险边界的股票不进入建议。", `${quoteTruth}AI 不补写缺失因子或承诺收益。`, ["realtime-quotes", "local-news"], [
    b("rule-gates", "AI 选股证据闸门", "ai-rules", "wide"), b("stock-ranking", "规则候选池", "evidence-score", "half"), b("strategy-route", "候选策略匹配", "stock-regime", "half"),
  ]),
  define("投资日历", "资讯与研究", "calendar-ledger", "未来和近期有哪些带时间戳、来源和 A 股关联的事件？", "当前只按已获取资讯时间归档，不把新闻发布时间伪装为官方事项日期。", newsTruth, ["local-news"], [
    b("event-calendar", "A 股事件日历", "date-groups", "wide"), b("news-wire", "当日事项明细", "calendar-detail", "half"), b("data-audit", "日期口径与来源", "calendar-source", "half"),
  ]),
  define("强度风口", "题材与板块", "strength-tunnel", "哪个板块的涨幅、广度和涨停扩散同时处于前列？", "风口看多因子共振，不追逐单只股票的瞬时拉升。", quoteTruth, ["realtime-quotes", "sector-membership"], [
    b("sector-heatmap", "强度风口排名", "multi-factor", "half"), b("sector-quadrant", "强度与扩散", "wind", "half"), b("sector-members", "风口领涨股", "wind-leaders", "wide"),
  ]),
  define("昨涨停", "涨停生态", "previous-limit-feedback", "上一交易日严格涨停的股票今天表现如何？", "必须读取前一交易日完整日线；当前涨停状态不能冒充昨涨停名单。", historyTruth, ["daily-history-previous"], [
    b("history-audit", "昨日涨停名单审计", "previous-limit", "wide"), b("distribution", "今日反馈分组", "feedback", "half"), b("stock-ranking", "可验证反馈明细", "previous-only", "half"),
  ]),
  define("跌停板", "涨停生态", "down-limit-risk", "当前跌停风险集中在哪些股票和板块？", "跌停页用于识别风险扩散，不提供抄底指令。", quoteTruth, ["realtime-quotes", "sector-membership"], [
    b("risk-board", "跌停风险清单", "strict-down", "tall"), b("sector-heatmap", "风险板块扩散", "down-sector", "half"), b("limit-ecology", "涨跌停风险对照", "risk-balance", "wide"),
  ]),
  define("个股详情", "资讯与研究", "stock-dossier", "所选股票当前量价、状态、题材和新闻证据是什么？", "先核对代码和时间，再看价格状态与关联资讯；代表列表不是完整股票目录。", `${quoteTruth}${newsTruth}`, ["realtime-quotes", "local-news"], [
    b("stock-inspector", "个股实时档案", "ohlc", "wide"), b("evidence-map", "个股证据链", "stock-news", "half"), b("risk-board", "个股状态提醒", "stock-risk", "half"),
  ]),
  define("主力大单监控", "资金与席位", "large-order-audit", "是否获得逐笔大单方向和真实净流入字段？", "大单净流入缺失时只展示数据审计，不能把高成交额称为主力买入。", flowTruth, ["large-order-flow"], [
    b("capital-audit", "主力大单字段审计", "large-order", "wide"), b("data-audit", "主力结论禁区", "no-proxy", "wide"),
  ]),
  define("问财选股", "资讯与研究", "local-rule-composer", "本地可复核规则筛出了哪些股票，和问财官方接口有何区别？", "这里是本地规则筛选器；每个条件都可见，不冒充问财官方语义结果。", `${quoteTruth}当前没有调用问财官方语义接口。`, ["realtime-quotes"], [
    b("rule-gates", "本地选股规则器", "iwencai-local", "tall"), b("stock-ranking", "条件命中结果", "rule-result", "half"), b("data-audit", "接口身份声明", "not-iwencai", "wide"),
  ]),
  define("异动提醒", "竞价与盘中", "alert-inbox", "哪些最新异动按方向、时间和影响股票需要优先处理？", "先处理风险方向和涉及多股的事件，再核对原始来源。", newsTruth, ["local-news"], [
    b("risk-board", "高优先级提醒", "alert-priority", "half"), b("event-timeline", "异动提醒收件箱", "latest-first", "half"), b("evidence-map", "提醒关联股票", "alert-links", "wide"),
  ]),
  define("板块资金动图", "资金与席位", "sector-flow-audit", "是否获得板块级真实净流入序列，能够描述资金迁移？", "只有取得连续净流入序列才展示资金迁移动图；缺失时直接列出待接字段。", "当前接口未提供板块真实净流入；板块成交额不能替代资金流向。", ["sector-capital-flow"], [
    b("capital-audit", "板块资金字段审计", "sector-flow", "wide"), b("data-audit", "资金动图口径", "flow-boundary", "wide"),
  ]),
  define("个股异动", "竞价与盘中", "stock-anomaly-scatter", "哪些代表股票出现显著振幅、开盘缺口或涨跌变化？", "异动用于发现需要核验的股票，不代表异常原因已经确认。", quoteTruth, ["realtime-quotes", "local-news"], [
    b("stock-matrix", "振幅-涨幅异动矩阵", "amplitude-change", "wide"), b("stock-ranking", "个股异动榜", "anomaly-score", "half"), b("news-wire", "个股异动解释线索", "stock-anomaly-news", "half"),
  ]),
  define("开盘啦", "竞价与盘中", "opening-checklist", "开盘阶段的指数、广度、竞价缺口和首批热点是否支持交易观察？", "按检查单逐项确认，不因单一指数上涨就扩大风险。", quoteTruth, ["realtime-quotes", "local-news"], [
    b("market-pulse", "开盘市场检查单", "opening", "wide"), b("auction-gap", "首批开盘异动", "opening-first", "third"), b("theme-atlas", "开盘热点", "opening-theme", "third"), b("risk-board", "开盘风险闸门", "opening-risk", "third"),
  ]),
  define("热点解读", "资讯与研究", "news-theme-market", "热点新闻、题材归因和股票行情是否形成一致证据链？", "依次看原文、题材和行情验证；任何一环缺失都标记为待核验。", newsTruth, ["local-news", "realtime-quotes"], [
    b("news-wire", "热点原始资讯", "interpret", "third"), b("theme-atlas", "热点题材归因", "interpret", "third"), b("stock-matrix", "行情一致性验证", "interpret", "third"), b("evidence-map", "热点证据链", "full-chain", "wide"),
  ]),
  define("非研产业库", "资讯与研究", "industry-research-map", "公开产业信息如何沿主题和公司关系关联到 A 股？", "产业库是公开资料索引，不代表券商研报评级，也不补写上下游关系。", newsTruth, ["local-news", "sector-membership"], [
    b("industry-map", "A 股产业主题地图", "taxonomy", "wide"), b("theme-atlas", "产业资料目录", "industry-docs", "half"), b("stock-matrix", "产业关联公司", "industry-stocks", "half"),
  ]),
  define("连板梯队", "盘后复盘", "review-limit-ladder", "最新交易日有哪些股票形成真实连续涨停，高度结构是否集中？", "先看最高板和各高度数量，再核对每只股票的连续涨停统计；封板资金等盘中字段缺失时保持空值。", historyTruth, ["daily-history-previous"], [
    b("limit-ladder", "连板高度与明细", "consecutive-limit", "wide"), b("review-summary", "连板结构仪表", "limit-ladder", "half"), b("data-audit", "日线覆盖与字段边界", "review-history", "half"),
  ]),
  define("首板梯队", "盘后复盘", "review-first-board", "最新交易日哪些股票首次收盘封板，且上一交易日并未涨停？", "首板只说明当天首次进入涨停状态，涨停当日不追买；按成交额查看活跃度并核对数据日期。", historyTruth, ["daily-history-previous"], [
    b("first-board-table", "首板梯队完整清单", "first-limit", "wide"), b("review-summary", "首板分布仪表", "first-board", "half"), b("data-audit", "首板判定口径", "first-board-rule", "half"),
  ]),
  define("放量突破", "量价筛选", "review-volume-breakout", "哪些股票同时创 60 日收盘新高并出现明确放量？", "先看量能倍数，再看突破参考高点和成交额；命中规则是观察线索，不是追涨指令。", historyTruth, ["daily-history-100"], [
    b("breakout-table", "60 日放量突破清单", "volume-breakout", "wide"), b("review-summary", "突破强度仪表", "volume-breakout", "half"), b("data-audit", "放量突破规则", "volume-breakout-rule", "half"),
  ]),
  define("突破前高", "量价筛选", "review-previous-high", "哪些股票收盘突破前 20 日最高价，并得到成交量确认？", "参考高点只使用当前交易日前的数据，避免前视偏差；没有量能确认不进入清单。", historyTruth, ["daily-history-100"], [
    b("breakout-table", "突破前高清单", "previous-high", "wide"), b("review-summary", "前高突破仪表", "previous-high", "half"), b("data-audit", "前高窗口与量能口径", "previous-high-rule", "half"),
  ]),
  define("低位放量", "量价筛选", "review-low-volume", "哪些股票处于 120 日价格区间下部，同时出现成交量放大？", "低位只按历史区间位置定义，不等于低估或见底；必须结合趋势和风险继续核验。", historyTruth, ["daily-history-100"], [
    b("breakout-table", "低位放量观察清单", "low-position", "wide"), b("review-summary", "位置与量能仪表", "low-position", "half"), b("data-audit", "低位放量判定口径", "low-position-rule", "half"),
  ]),
  define("龙虎榜", "资金与席位", "review-dragon-tiger", "最新公开龙虎榜中哪些股票出现显著净买卖，具体席位如何构成？", "只展示东方财富公开龙虎榜及席位金额；缓存过期或席位缺失时明确标记，不使用成交额代替净买入。", seatTruth, ["dragon-tiger-seats"], [
    b("dragon-tiger-board", "龙虎榜股票与席位", "daily-seats", "wide"), b("review-summary", "龙虎榜资金仪表", "dragon-tiger", "half"), b("data-audit", "榜单来源与缓存时效", "dragon-tiger-source", "half"),
  ]),
];

const workspaceByLabel = new Map(WORKSPACE_DEFINITIONS.map((item) => [item.label, item]));

export function getWorkspaceDefinition(label: string): WorkspaceDefinition {
  const definition = workspaceByLabel.get(label);
  if (!definition) throw new Error(`信息总览菜单未登记：${label}`);
  return definition;
}
