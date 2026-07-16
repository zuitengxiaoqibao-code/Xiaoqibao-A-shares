import { Database, LoaderCircle, ShieldAlert } from "lucide-react";

import type { DataStatusState } from "./types";

const sourceNames: Record<string, string> = {
  baidu: "百度股市通",
  mootdx: "通达信 mootdx",
};

function attemptMessage(message: string): string {
  if (message.includes("no daily bars")) return "未返回日线";
  if (message.toLowerCase().includes("timeout")) return "连接超时";
  if (message.toLowerCase().includes("server disconnected")) return "远端连接被关闭";
  return message;
}

export function DataStatusPanel({ state }: { state: DataStatusState }) {
  if (state.kind === "idle") {
    return <div className="data-status empty"><Database size={17} /><span>尚未同步历史日线</span></div>;
  }
  if (state.kind === "syncing") {
    return <div className="data-status syncing" aria-busy="true"><LoaderCircle size={17} /><span>正在同步主备数据源...</span></div>;
  }
  if (state.kind === "error") {
    return <div className="data-status error" role="alert"><ShieldAlert size={17} /><span>{state.message}</span></div>;
  }
  return (
    <div className="data-status ready">
      <Database size={17} />
      <div>
        <b>{state.report.written_rows} 条日线</b>
        <span>{sourceNames[state.report.source] ?? state.report.source}</span>
        <small>{state.report.message}</small>
        {state.report.attempts.length > 1 && <details>
          <summary>查看来源尝试</summary>
          <ul>{state.report.attempts.map((attempt, index) => <li key={`${attempt.source}-${index}`}>
            {sourceNames[attempt.source] ?? attempt.source}：{attemptMessage(attempt.message)}
          </li>)}</ul>
        </details>}
      </div>
    </div>
  );
}
