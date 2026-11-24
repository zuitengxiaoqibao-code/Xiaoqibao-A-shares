import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { DATA_INTEGRITY_DIALOG_EVENT } from "../../shared/dataIntegrityDialog";

const websites = {
  intelligence: { title: "易数智算", subtitle: "发现专区 · ysclaw.hk", url: "https://ysclaw.hk/discover/", frameTitle: "易数智算发现专区", iframeRestricted: true },
  market_cloud: { title: "大盘云图", subtitle: "全市场行情热力图 · a.9009009.com", url: "https://a.9009009.com/", frameTitle: "大盘云图网页", iframeRestricted: false },
} as const;
type Website = keyof typeof websites;
type PanelBounds = { left: number; top: number; width: number; height: number };
type PanelResult = { available: boolean; error?: string | null };
type ReviewBridge = { set_review_panel: (bounds: PanelBounds | null, reload: boolean, site: Website) => Promise<PanelResult> };

function desktopBridge(): ReviewBridge | undefined {
  return (window as Window & { pywebview?: { api?: ReviewBridge } }).pywebview?.api;
}

// Serialize show/layout/hide operations, including rapid route changes.
let panelQueue: Promise<unknown> = Promise.resolve();
function updatePanel(bridge: ReviewBridge, bounds: PanelBounds | null, site: Website, reload = false): Promise<PanelResult> {
  const next = panelQueue.catch(() => undefined).then(() => bridge.set_review_panel(bounds, reload, site));
  panelQueue = next;
  return next;
}

export function YishuIntelligenceView() {
  return <EmbeddedWebsiteView site="intelligence" />;
}

export function MarketCloudView() {
  return <EmbeddedWebsiteView site="market_cloud" />;
}

function EmbeddedWebsiteView({ site }: { site: Website }) {
  const website = websites[site];
  const panel = useRef<HTMLDivElement>(null);
  const [revision, setRevision] = useState(0);
  const [mode, setMode] = useState<"connecting" | "desktop" | "browser" | "error">("connecting");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    let connectedBridge: ReviewBridge | undefined;
    let observer: ResizeObserver | undefined;
    let frame = 0;
    let timer: ReturnType<typeof setTimeout>;

    const layout = (reload = false) => {
      if (!panel.current || !connectedBridge || disposed) return;
      const rect = panel.current.getBoundingClientRect();
      if (document.querySelector(".startup-integrity-backdrop")) {
        void updatePanel(connectedBridge, null, site).catch(() => undefined);
        return;
      }
      const bounds = { left: Math.max(0, rect.left / window.innerWidth), top: Math.max(0, rect.top / window.innerHeight), width: rect.width / window.innerWidth, height: rect.height / window.innerHeight };
      void updatePanel(connectedBridge, bounds, site, reload).then((result) => {
        if (disposed) return;
        setError(result.error ?? null);
        setMode(result.available ? "desktop" : "error");
      }).catch(() => {
        if (!disposed) { setError("桌面网页容器连接失败，请重试"); setMode("error"); }
      });
    };
    const scheduleLayout = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(() => layout()); };
    const connect = () => {
      const bridge = desktopBridge();
      if (!bridge?.set_review_panel || connectedBridge || disposed) return;
      connectedBridge = bridge;
      clearTimeout(timer);
      setMode("desktop");
      layout(revision > 0);
      if (typeof ResizeObserver !== "undefined" && panel.current) {
        observer = new ResizeObserver(scheduleLayout);
        observer.observe(panel.current);
      }
    };
    window.addEventListener("pywebviewready", connect);
    window.addEventListener("resize", scheduleLayout);
    window.addEventListener("scroll", scheduleLayout, { passive: true });
    window.addEventListener(DATA_INTEGRITY_DIALOG_EVENT, scheduleLayout);
    timer = setTimeout(() => { if (!connectedBridge && !disposed) setMode("browser"); }, 1200);
    connect();
    return () => {
      disposed = true;
      clearTimeout(timer);
      cancelAnimationFrame(frame);
      observer?.disconnect();
      window.removeEventListener("pywebviewready", connect);
      window.removeEventListener("resize", scheduleLayout);
      window.removeEventListener("scroll", scheduleLayout);
      window.removeEventListener(DATA_INTEGRITY_DIALOG_EVENT, scheduleLayout);
      if (connectedBridge) void updatePanel(connectedBridge, null, site).catch(() => undefined);
    };
  }, [revision, site]);

  return <main className="yishu-intelligence-page">
    <header className="yishu-intelligence-header">
      <div><h1>{website.title}</h1><p>{website.subtitle}</p></div>
      <button type="button" onClick={() => { setError(null); setMode("connecting"); setRevision((value) => value + 1); }}><RefreshCw size={15} />刷新网页</button>
    </header>
    {mode === "browser" && website.iframeRestricted && <p className="yishu-review-message" role="status">该站点当前禁止 iframe 内嵌，请使用桌面便携版的内嵌网页功能；浏览器版本需由站点管理员开放内嵌权限。</p>}
    {error && <p className="yishu-review-message" role="alert">{error}</p>}
    <div className="yishu-review-panel" ref={panel}>
      {mode === "connecting" && <div className="yishu-review-loading" role="status">正在连接{website.title}…</div>}
      {mode === "browser" && <iframe key={revision} title={website.frameTitle} src={website.url} referrerPolicy="no-referrer" />}
    </div>
  </main>;
}
