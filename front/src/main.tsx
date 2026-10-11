import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app/App";
import { initTheme } from "@/lib/theme";
// Polices servies par l'application (sous-ensemble latin, graisses utilisées) : rien chez un tiers,
// et l'outil s'affiche pareil sur un poste sans accès à internet.
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/jetbrains-mono/latin-400.css";
import "@fontsource/jetbrains-mono/latin-500.css";
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
