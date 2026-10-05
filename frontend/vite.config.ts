/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  test: {
    environment: "jsdom",
    globals: true,
    exclude: ["e2e/**", "node_modules/**"],
    setupFiles: ["./src/test-setup.ts"],
    coverage: { provider: "v8", include: ["src/**/*.{ts,tsx}"], exclude: ["src/main.tsx", "src/test-setup.ts", "src/vite-env.d.ts"] },
  },
});
