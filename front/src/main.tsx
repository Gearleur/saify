import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app/App";
import "./index.css";

const racine = document.getElementById("root");
if (!racine) throw new Error("#root absent de index.html");

createRoot(racine).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
