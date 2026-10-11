import { useCallback, useEffect, useSyncExternalStore } from "react";
import { useErrorToast } from "@/hooks/useErrorToast";
import { rapprochementsApi } from "@/lib/api";
import type { DotTone } from "@/lib/metier";
import type { Rapprochement, StatutTraitement, Suspens } from "@/types/api";

export const STATUTS_TRAITEMENT: Record<StatutTraitement, { label: string; tone: DotTone }> = {
  a_traiter: { label: "À traiter", tone: "ring" },
  en_cours: { label: "En cours", tone: "blue" },
  traite: { label: "Traité", tone: "green" },
};
export const ORDRE_STATUTS: StatutTraitement[] = ["a_traiter", "en_cours", "traite"];

type Statuts = Record<string, StatutTraitement>;

/**
 * Statuts par rapprochement (id → suspens → statut), partagés par toutes les vues.
 * Le serveur est la source de vérité : statuts communs à l'équipe, chaque changement y est tracé.
 */
let parRapprochement: Record<string, Statuts> = {};
const chargements = new Set<string>();
const abonnes = new Set<() => void>();

function abonner(rappel: () => void) {
  abonnes.add(rappel);
  return () => abonnes.delete(rappel);
}

function publier(id: string, statuts: Statuts) {
  parRapprochement = { ...parRapprochement, [id]: statuts };
  abonnes.forEach((r) => r());
}

function charger(id: string, surErreur: (e: unknown) => void) {
  if (id in parRapprochement || chargements.has(id)) return;
  chargements.add(id);
  rapprochementsApi
    .statuts(id)
    .then((r) => publier(id, r.statuts))
    .catch(surErreur)
    .finally(() => chargements.delete(id));
}

/** Statut de traitement des suspens du rapprochement `r` ; `set` est optimiste et annulé en cas d'échec. */
export function useStatuts(r: Rapprochement | null) {
  const tous = useSyncExternalStore(abonner, () => parRapprochement);
  const signaler = useErrorToast();
  const id = r?.id ?? null;
  useEffect(() => {
    if (id) charger(id, signaler);
  }, [id, signaler]);

  const statuts = id ? tous[id] : undefined;
  const get = useCallback(
    (s: Suspens): StatutTraitement => statuts?.[s.id] ?? "a_traiter",
    [statuts],
  );
  const set = useCallback(
    async (s: Suspens, valeur: StatutTraitement) => {
      if (!id) return;
      const avant = parRapprochement[id] ?? {};
      const suivant = { ...avant };
      if (valeur === "a_traiter") delete suivant[s.id];
      else suivant[s.id] = valeur;
      publier(id, suivant);
      try {
        await rapprochementsApi.changerStatut(id, s.id, valeur);
      } catch (e) {
        publier(id, avant);
        signaler(e);
      }
    },
    [id, signaler],
  );
  return { get, set };
}
