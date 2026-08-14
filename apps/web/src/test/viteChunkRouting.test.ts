import { describe, expect, it } from "vitest";

import { manualChunks } from "../../viteChunks";

describe("Vite vendor chunk routing", () => {
  it("keeps heavyweight dependencies out of the application entry chunk", () => {
    expect(manualChunks("/node_modules/react/index.js")).toBe("react-vendor");
    expect(manualChunks("/node_modules/echarts/index.js")).toBe("chart-vendor");
    expect(manualChunks("/node_modules/lucide-react/dist/index.js")).toBe("ui-vendor");
    expect(manualChunks("/node_modules/@fontsource/orbitron/index.css")).toBe("font-vendor");
    expect(manualChunks("/src/features/dashboard/Dashboard.tsx")).toBeUndefined();
  });
});
