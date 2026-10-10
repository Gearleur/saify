import { useReconciliation } from "@/hooks/useReconciliation";
import type { DotTone } from "@/lib/metier";
import type { RouteId } from "@/hooks/useHashRoute";

export interface NavBadge {
  count?: number;
  /** Point rouge seulement s'il y a du critique ou un blocage. */
  tone?: DotTone;
}

/** Compteurs gris de la barre latérale, tirés du rapprochement courant. */
export function useNavBadges(): Partial<Record<RouteId, NavBadge>> {
  const { courant } = useReconciliation();
  if (!courant) return {};
  const { critique, a_relever } = courant.synthese.par_priorite;
  const alerte = courant.statut === "BLOQUE" || critique > 0;
  return {
    "a-traiter": {
      count: courant.statut === "BLOQUE" ? undefined : critique + a_relever,
      tone: alerte ? "red" : undefined,
    },
    suspens: { count: courant.statut === "BLOQUE" ? undefined : courant.synthese.nb_suspens },
  };
}
