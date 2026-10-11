/**
 * Thème clair, sombre ou système, sans React : `data-theme` (light | dark) sur <html>.
 * Le choix est gardé dans localStorage (try/catch via storage.ts), « Système » par défaut.
 * `initTheme()` est appelé dans main.tsx avant le premier rendu.
 */

import { readJson, writeJson } from "./storage";

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "mo.theme";
const PREFERENCES: ThemePreference[] = ["light", "dark", "system"];

function read(): ThemePreference {
  const raw = readJson<unknown>(STORAGE_KEY, "system");
  return PREFERENCES.find((p) => p === raw) ?? "system";
}

const media = () => window.matchMedia("(prefers-color-scheme: dark)");

let preference: ThemePreference = "system";
const listeners = new Set<() => void>();

function resolve(p: ThemePreference): ResolvedTheme {
  if (p !== "system") return p;
  return media().matches ? "dark" : "light";
}

function apply(): void {
  document.documentElement.dataset.theme = resolve(preference);
  listeners.forEach((f) => f());
}

let initialized = false;

/** Pose `data-theme` et suit le système tant que la préférence est « Système ». */
export function initTheme(): void {
  if (initialized) return;
  initialized = true;
  preference = read();
  apply();
  media().addEventListener("change", () => {
    if (preference === "system") apply();
  });
}

export function getThemePreference(): ThemePreference {
  return preference;
}

export function getResolvedTheme(): ResolvedTheme {
  return resolve(preference);
}

export function setThemePreference(p: ThemePreference): void {
  preference = p;
  writeJson(STORAGE_KEY, p);
  apply();
}

export function subscribeTheme(f: () => void): () => void {
  listeners.add(f);
  return () => listeners.delete(f);
}
