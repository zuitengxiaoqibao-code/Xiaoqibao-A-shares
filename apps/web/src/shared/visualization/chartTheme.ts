export const chartTheme = {
  backgroundColor: "transparent",
  // ECharts renders onto canvas/SVG and cannot reliably resolve CSS custom properties.
  // Keep the palette literal here; the matching CSS tokens remain in tokens.css.
  textColor: "#dce7ee",
  mutedTextColor: "#667987",
  gridColor: "#22313d",
  upColor: "#f04f5f",
  downColor: "#2fcf91",
  warningColor: "#e5b84b",
  liveColor: "#39c8dd",
  unavailableColor: "#7d8993",
  fontFamily: "JetBrains Mono, monospace",
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
