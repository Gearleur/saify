import { useMemo } from "react";
import { useStatuts } from "@/features/suspens/statutsTraitement";
import { ORDRE_PRIORITES } from "@/lib/metier";
import type { Priorite, Rapprochement, Suspens } from "@/types/api";

export interface TriageGroup {
  priorite: Priorite;
  rows: Suspens[];
}

/** File du matin : suspens groupés par priorité (ordre du back), anomalies hors suspens, avancement local. */
export function useTriage(r: Rapprochement | null) {
  const { get } = useStatuts(r);
  return useMemo(() => {
    const suspens = r?.suspens ?? [];
    const groups: TriageGroup[] = ORDRE_PRIORITES.map((priorite) => ({
      priorite,
      rows: suspens.filter((s) => s.priorite === priorite),
    }));
    const horsSuspens = (r?.journal ?? []).filter(
      (a) => a.niveau === "EXCLU" || a.niveau === "SIGNALE",
    );
    const blocages = (r?.journal ?? []).filter((a) => a.niveau === "BLOQUANT");
    const traites = suspens.filter((s) => get(s) === "traite").length;
    const ids = groups.flatMap((g) => g.rows.map((s) => s.id));
    return { groups, horsSuspens, blocages, traites, ids, total: suspens.length };
  }, [r, get]);
}
