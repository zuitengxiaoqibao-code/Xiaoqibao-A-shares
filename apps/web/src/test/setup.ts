import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, vi } from "vitest";

function resetTestEnvironment(): void {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
}

afterEach(resetTestEnvironment);
afterAll(resetTestEnvironment);
