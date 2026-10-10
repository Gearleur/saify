import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Le build est servi par FastAPI : la page sur `/`, les fichiers sous `/static/`.
// En développement, Vite sert l'application sur `/` et relaie `/api` vers FastAPI (`API_URL`).
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/" : "/",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: {
    outDir: "../middle_office/web",
    emptyOutDir: true,
    // Pas de script inline (CSP `script-src 'self'`).
    modulePreload: { polyfill: false },
    assetsInlineLimit: 0,
  },
  server: { port: 5173, proxy: { "/api": API_URL } },
}));
