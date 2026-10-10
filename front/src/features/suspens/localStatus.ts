import { useCallback, useSyncExternalStore } from "react";
import type { DotTone } from "@/lib/metier";
import { readJson, writeJson } from "@/lib/storage";
import type { Suspens } from "@/types/api";

/** Statut de traitement local au poste (pas de route back pour le partager). */
export type LocalStatus = "a_traiter" | "en_cours" | "traite";

export const LOCAL_STATUS: Record<LocalStatus, { label: string; tone: DotTone }> = {
  a_traiter: { label: "À traiter", tone: "ring" },
  en_cours: { label: "En cours", tone: "blue" },
  traite: { label: "Traité", tone: "green" },
};
export const ORDRE_STATUTS: LocalStatus[] = ["a_traiter", "en_cours", "traite"];

const CLE = "mo.statuts";
type Statuts = Record<string, LocalStatus>;

let statuts: Statuts = readJson<Statuts>(CLE, {});
const abonnes = new Set<() => void>();

function abonner(rappel: () => void) {
  abonnes.add(rappel);
  return () => abonnes.delete(rappel);
}

/** Clé : date d'arrêté + fonds + ISIN + conservateur + type (stable d'un rapprochement à l'autre du même jour). */
export function statusKey(dateArrete: string | null, s: Suspens): string {
  return [dateArrete ?? "inconnue", s.fonds, s.isin, s.conservateur, s.type].join("|");
}

export function useLocalStatus(dateArrete: string | null) {
  const courant = useSyncExternalStore(abonner, () => statuts);

  const get = useCallback(
    (s: Suspens): LocalStatus => courant[statusKey(dateArrete, s)] ?? "a_traiter",
    [courant, dateArrete],
  );

  const set = useCallback(
    (s: Suspens, valeur: LocalStatus) => {
      const suivant = { ...statuts };
      const cle = statusKey(dateArrete, s);
      if (valeur === "a_traiter") delete suivant[cle];
      else suivant[cle] = valeur;
      statuts = suivant;
      writeJson(CLE, statuts);
      abonnes.forEach((r) => r());
    },
    [dateArrete],
  );

  return { get, set };
}
