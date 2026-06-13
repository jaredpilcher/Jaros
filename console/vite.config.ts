import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the local bridge (server/index.ts). In
// production, `npm run build` emits dist/ and the bridge serves it directly.
const API_PORT = process.env.JAROS_CONSOLE_API_PORT ?? "7373";

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.JAROS_CONSOLE_WEB_PORT ?? 5500),
    proxy: {
      "/api": `http://localhost:${API_PORT}`,
    },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
