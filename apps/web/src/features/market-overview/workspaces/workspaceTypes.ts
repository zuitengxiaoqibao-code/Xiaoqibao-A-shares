export type WorkspaceEvidence =
  | "realtime-quotes"
  | "order-book"
  | "daily-history-100"
  | "daily-history-previous"
  | "dragon-tiger-seats"
  | "large-order-flow"
  | "sector-capital-flow"
  | "local-news"
  | "sector-membership";

export type WorkspaceBlockKind =
  | "market-pulse"
  | "event-timeline"
  | "news-wire"
  | "auction-gap"
  | "auction-gates"
  | "stock-ranking"
  | "stock-matrix"
  | "stock-inspector"
  | "sector-heatmap"
  | "sector-quadrant"
  | "sector-members"
  | "theme-atlas"
  | "theme-matrix"
  | "industry-map"
  | "limit-ecology"
  | "limit-board"
  | "failure-board"
  | "height-pyramid"
  | "promotion-funnel"
  | "leader-lanes"
  | "risk-board"
  | "distribution"
  | "seven-rankings"
  | "statistics-pivot"
  | "event-calendar"
  | "review-columns"
  | "rule-gates"
  | "evidence-map"
  | "capital-audit"
  | "history-audit"
  | "data-audit"
  | "strategy-route"
  | "review-summary"
  | "limit-ladder"
  | "first-board-table"
  | "sector-performance"
  | "breakout-table"
  | "dragon-tiger-board"
  | "seat-tracker"
  | "seat-direction";

export type WorkspaceBlock = {
  kind: WorkspaceBlockKind;
  title: string;
  variant: string;
  size: "wide" | "half" | "third" | "tall";
};

export type WorkspaceDefinition = {
  label: string;
  family: string;
  layout: string;
  question: string;
  beginnerGuide: string;
  truthBoundary: string;
  requiredEvidence: WorkspaceEvidence[];
  blocks: WorkspaceBlock[];
};
