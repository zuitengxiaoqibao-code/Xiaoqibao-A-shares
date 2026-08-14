export function manualChunks(id: string): string | undefined {
  const normalized = id.replace(/\\/g, "/");
  if (normalized.includes("/node_modules/react/") || normalized.includes("/node_modules/react-dom/") || normalized.includes("/node_modules/scheduler/")) return "react-vendor";
  if (normalized.includes("/node_modules/echarts/") || normalized.includes("/node_modules/zrender/")) return "chart-vendor";
  if (normalized.includes("/node_modules/lucide-react/")) return "ui-vendor";
  if (normalized.includes("/node_modules/@fontsource/")) return "font-vendor";
  return undefined;
}
