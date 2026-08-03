import { Search } from "lucide-react";
import { useState } from "react";

import { DecisionWorkbench } from "./DecisionWorkbench";
import type { DecisionResponse } from "./types";
import { MarketSentimentDashboard } from "../market-sentiment/MarketSentimentDashboard";
import type { MarketSentimentResponse, MarketSentimentSnapshot } from "../market-sentiment/types";
import {
  TerminalPageHeader,
  TerminalPanel,
  TerminalStatusStrip,
} from "../../shared/terminal/TerminalPrimitives";
import { BreakingNewsStrip } from "../news-alerts/BreakingNewsStrip";
import type { BreakingNewsAlertLoader } from "../news-alerts/types";
import { useBreakingNewsAlerts } from "../news-alerts/useBreakingNewsAlerts";

type Props = {
  loadCurrent: () => Promise<DecisionResponse>;
  loadDate?: (date: string) => Promise<DecisionResponse>;
  selectedSymbol?: string | null;
  onOpenAShares?: (symbol?: string) => void;
  loadSentiment?: () => Promise<MarketSentimentResponse>;
  refreshSentiment?: () => Promise<MarketSentimentSnapshot>;
  loadAlerts?: BreakingNewsAlertLoader;
};

export function TodayDecisionView({ loadCurrent, loadDate, selectedSymbol, onOpenAShares, loadSentiment, refreshSentiment, loadAlerts }: Props) {
  const [scope, setScope] = useState<"market" | "selected">("market");
  const selectedScope = scope === "selected" && Boolean(selectedSymbol);
  const alertState = useBreakingNewsAlerts(loadAlerts, selectedScope ? selectedSymbol : undefined, 4);

  return <section className="terminal-page today-decision-view console-home" aria-label="A 股监控首页">
    <TerminalPageHeader
      className="console-home-bar"
      eyebrow="A-SHARE / DECISION MONITOR"
      title="A 股决策监控"
      description="盘前研判 · 盘中检测 · 盘后复盘"
      actions={<div className="console-home-readouts" aria-label="首页状态">
        <span><i className="console-status-dot" aria-hidden="true" />公开数据链路</span>
        <span>只读观察模式</span>
        <strong>{selectedScope ? `焦点 ${selectedSymbol}` : "全市场"}</strong>
      </div>}
    />

    <TerminalStatusStrip ariaLabel="研判运行状态" className="decision-runtime-strip">
      <span><i className="console-status-dot" aria-hidden="true" />数据链路监测中</span>
      <span>研判阶段 盘前 / 盘中 / 盘后</span>
      <strong>{selectedScope ? `当前股票 ${selectedSymbol}` : "全市场"}</strong>
    </TerminalStatusStrip>

    <TerminalPanel
      title="研判范围"
      subtitle="CONTROL / SCOPE · 当前首页视角"
      ariaLabel="研判控制台"
      className="console-window console-window-scope"
      bodyClassName="console-window-body"
    >
        <section className="decision-scope" aria-label="研判范围">
          <div>
            <span>研判范围</span>
            <strong>{selectedScope ? `A 股 ${selectedSymbol}` : "全部 A 股建议"}</strong>
            <p>{selectedScope ? "只显示当前股票已有的可验证结论" : "汇总今日已生成的盘前、盘中与盘后记录"}</p>
          </div>
          <div className="decision-scope-switch" role="group" aria-label="切换研判范围">
            <button type="button" aria-pressed={!selectedScope} onClick={() => setScope("market")}>全市场</button>
            {selectedSymbol
              ? <button type="button" aria-pressed={selectedScope} onClick={() => setScope("selected")}>只看 {selectedSymbol}</button>
              : onOpenAShares && <button type="button" onClick={() => onOpenAShares()}><Search size={15} />选择股票</button>}
          </div>
        </section>
    </TerminalPanel>

    {loadAlerts && <BreakingNewsStrip
      {...alertState}
      onOpenAShare={onOpenAShares ? (symbol) => onOpenAShares(symbol) : undefined}
    />}

    {loadSentiment && <TerminalPanel
      title="市场情绪"
      subtitle="WINDOW 01 / MARKET PULSE · 全市场状态"
      ariaLabel="市场情绪监视窗"
      className="console-window console-window-sentiment"
      bodyClassName="console-window-body"
    ><MarketSentimentDashboard load={loadSentiment} refresh={refreshSentiment} /></TerminalPanel>}

    <TerminalPanel
      title="三阶段决策"
      subtitle="WINDOW 02 / DECISION FLOW · 证据优先 · 不构成交易指令"
      ariaLabel="三阶段决策监视窗"
      className="console-window console-window-decision"
      bodyClassName="console-window-body"
    ><DecisionWorkbench loadCurrent={loadCurrent} loadDate={loadDate} selectedSymbol={selectedScope ? selectedSymbol : undefined} /></TerminalPanel>
  </section>;
}
