/**
 * Thème clair, sombre ou système, sans React : `data-theme` (light | dark) sur <html>.
 * Le choix est gardé dans localStorage (try/catch via storage.ts), « Système » par défaut.
 * `initTheme()` est appelé dans main.tsx avant le premier rendu.
 */

import { readJson, writeJson } from "./storage";

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const CLE = "mo.theme";
const PREFERENCES: ThemePreference[] = ["light", "dark", "system"];

function lire(): ThemePreference {
  const brut = readJson<unknown>(CLE, "system");
  return PREFERENCES.find((p) => p === brut) ?? "system";
}

const media = () => window.matchMedia("(prefers-color-scheme: dark)");

let preference: ThemePreference = "system";
const abonnes = new Set<() => void>();

function resoudre(p: ThemePreference): ResolvedTheme {
  if (p !== "system") return p;
  return media().matches ? "dark" : "light";
}

function appliquer(): void {
  document.documentElement.dataset.theme = resoudre(preference);
  abonnes.forEach((f) => f());
}

let initialise = false;

/** Pose `data-theme` et suit le système tant que la préférence est « Système ». */
export function initTheme(): void {
  if (initialise) return;
  initialise = true;
  preference = lire();
  appliquer();
  media().addEventListener("change", () => {
    if (preference === "system") appliquer();
  });
}

export function getThemePreference(): ThemePreference {
  return preference;
}

export function getResolvedTheme(): ResolvedTheme {
  return resoudre(preference);
}

export function setThemePreference(p: ThemePreference): void {
  preference = p;
  writeJson(CLE, p);
  appliquer();
}

export function subscribeTheme(f: () => void): () => void {
  abonnes.add(f);
  return () => abonnes.delete(f);
}
