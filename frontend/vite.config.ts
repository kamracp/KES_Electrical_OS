import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8012",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
    strictPort: true,
  },
  build: {
    sourcemap: true,
  },
  test: {
    // jsdom + React Testing Library files can exceed the 5 s default on a loaded machine;
    // the gate was failing intermittently on CableSizingResultPanel.test.tsx.
    testTimeout: 20_000,
  },
});
