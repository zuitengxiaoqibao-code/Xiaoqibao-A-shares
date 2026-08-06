export const chartTheme = {
  backgroundColor: "transparent",
  textColor: "var(--text-primary, #dce7ee)",
  mutedTextColor: "var(--text-muted, #667987)",
  gridColor: "var(--border-subtle, #22313d)",
  upColor: "var(--market-up, #f04f5f)",
  downColor: "var(--market-down, #2fcf91)",
  warningColor: "var(--status-warning, #e5b84b)",
  liveColor: "var(--status-live, #39c8dd)",
  unavailableColor: "var(--status-unavailable, #7d8993)",
  fontFamily: "var(--font-data, 'JetBrains Mono', monospace)",
} as const;

export type ChartTheme = typeof chartTheme;

export function chartToneColor(tone: "up" | "down" | "warning" | "live" | "neutral" | "unavailable"): string {
  switch (tone) {
    case "up": return chartTheme.upColor;
    case "down": return chartTheme.downColor;
    case "warning": return chartTheme.warningColor;
    case "live": return chartTheme.liveColor;
    case "unavailable": return chartTheme.unavailableColor;
    default: return chartTheme.textColor;
  }
}
