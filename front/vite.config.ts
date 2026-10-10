import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Le build est servi par FastAPI : la page sur `/`, les fichiers sous `/static/`.
export default defineConfig({
  base: "/static/",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: {
    outDir: "../middle_office/web",
    emptyOutDir: true,
    // Pas de script inline (CSP `script-src 'self'`).
    modulePreload: { polyfill: false },
    assetsInlineLimit: 0,
  },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
