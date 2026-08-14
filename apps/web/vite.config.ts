import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { manualChunks } from "./viteChunks";

export { manualChunks } from "./viteChunks";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: { manualChunks },
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000"
    }
  }
});
