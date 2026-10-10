import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app/App";
import { initTheme } from "@/lib/theme";
import "./index.css";

// Avant le premier rendu : data-theme est posé avant que React ne peigne quoi que ce soit.
initTheme();

const racine = document.getElementById("root");
if (!racine) throw new Error("#root absent de index.html");

createRoot(racine).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
