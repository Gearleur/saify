import { useCallback, useSyncExternalStore } from "react";

export type RouteId = "a-traiter" | "suspens" | "point" | "questions" | "journal" | "parametrage";

export const ROUTES: RouteId[] = [
  "a-traiter",
  "suspens",
  "point",
  "questions",
  "journal",
  "parametrage",
];
const DEFAULT: RouteId = "a-traiter";
/** Anciennes adresses du front HTML, conservées. */
const ALIAS: Record<string, string> = { files: "journal?onglet=fichiers" };

export interface Route {
  id: RouteId;
  params: URLSearchParams;
}

function read(): Route {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const resolvedHash = ALIAS[raw] ?? raw;
  const [path = "", queryString = ""] = resolvedHash.split("?");
  const id = (ROUTES as string[]).includes(path) ? (path as RouteId) : DEFAULT;
  return { id, params: new URLSearchParams(queryString) };
}

let currentValue = read();
function subscribeLocal(callback: () => void) {
  const onChangeHandler = () => {
    currentValue = read();
    callback();
  };
  window.addEventListener("hashchange", onChangeHandler);
  return () => window.removeEventListener("hashchange", onChangeHandler);
}

export function routeHref(id: RouteId, params?: Record<string, string>): string {
  const queryString = params ? new URLSearchParams(params).toString() : "";
  return `#/${id}${queryString ? `?${queryString}` : ""}`;
}

/** Navigation par hash (aucun routeur) : `#/suspens?fonds=OBL`. */
export function useHashRoute() {
  const route = useSyncExternalStore(subscribeLocal, () => currentValue);
  const navigate = useCallback((id: RouteId, params?: Record<string, string>) => {
    window.location.hash = routeHref(id, params);
  }, []);
  return { route, navigate };
}
