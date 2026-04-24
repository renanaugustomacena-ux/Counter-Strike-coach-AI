import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// Bundle as a static SPA at ``dist/index.html`` so Qt's QWebEngineView
// can ``load(QUrl.fromLocalFile(...))``. Relative base is critical —
// absolute paths break against Qt's local file:// loading.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: true,
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks: {
          three: ["three"],
          d3: ["d3"],
        },
      },
    },
  },
  resolve: {
    alias: {
      "@shared": resolve(__dirname, "../shared"),
    },
  },
});
