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
const DEFAUT: RouteId = "a-traiter";
/** Anciennes adresses du front HTML, conservées. */
const ALIAS: Record<string, string> = { fichiers: "journal?onglet=fichiers" };

export interface Route {
  id: RouteId;
  params: URLSearchParams;
}

function lire(): Route {
  const brut = window.location.hash.replace(/^#\/?/, "");
  const resolu = ALIAS[brut] ?? brut;
  const [chemin = "", requete = ""] = resolu.split("?");
  const id = (ROUTES as string[]).includes(chemin) ? (chemin as RouteId) : DEFAUT;
  return { id, params: new URLSearchParams(requete) };
}

let courante = lire();
function abonner(rappel: () => void) {
  const surChangement = () => {
    courante = lire();
    rappel();
  };
  window.addEventListener("hashchange", surChangement);
  return () => window.removeEventListener("hashchange", surChangement);
}

export function routeHref(id: RouteId, params?: Record<string, string>): string {
  const requete = params ? new URLSearchParams(params).toString() : "";
  return `#/${id}${requete ? `?${requete}` : ""}`;
}

/** Navigation par hash (aucun routeur) : `#/suspens?fonds=OBL`. */
export function useHashRoute() {
  const route = useSyncExternalStore(abonner, () => courante);
  const navigate = useCallback((id: RouteId, params?: Record<string, string>) => {
    window.location.hash = routeHref(id, params);
  }, []);
  return { route, navigate };
}
