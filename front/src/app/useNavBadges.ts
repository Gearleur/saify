import { useReconciliation } from "@/hooks/useReconciliation";
import type { DotTone } from "@/lib/domain";
import type { RouteId } from "@/hooks/useHashRoute";

export interface NavBadge {
  count?: number;
  /** Point rouge seulement s'il y a du critique ou un blocage. */
  tone?: DotTone;
}

/** Compteurs gris de la barre latérale, tirés du rapprochement courant. */
export function useNavBadges(): Partial<Record<RouteId, NavBadge>> {
  const { current } = useReconciliation();
  if (!current) return {};
  const { critique, a_relever } = current.summary.by_priority;
  const alert = current.status === "BLOQUE" || critique > 0;
  return {
    "a-traiter": {
      count: current.status === "BLOQUE" ? undefined : critique + a_relever,
      tone: alert ? "red" : undefined,
    },
    suspens: { count: current.status === "BLOQUE" ? undefined : current.summary.break_count },
  };
}
