/// <reference types="vite/client" />

import { describe, expect, it } from "vitest";


const productionSources = import.meta.glob("../**/*.{ts,tsx}", {
  eager: true,
  import: "default",
  query: "?raw",
}) as Record<string, string>;


describe("production copy", () => {
  it("does not expose internal previous-version terminology", () => {
    const violations = Object.entries(productionSources)
      .filter(([path]) => !path.includes(".test."))
      .filter(([, source]) => /旧版|老版|旧数据/.test(source))
      .map(([path]) => path);

    expect(violations).toEqual([]);
  });
});
