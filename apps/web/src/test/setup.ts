import "@testing-library/jest-dom/vitest";
import { cleanup, configure } from "@testing-library/react";
import { afterAll, afterEach, vi } from "vitest";

configure({ asyncUtilTimeout: 5_000 });

function resetTestEnvironment(): void {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
}

afterEach(resetTestEnvironment);
afterAll(resetTestEnvironment);
