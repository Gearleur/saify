import { useMemo } from "react";
import { useWorkStatuses } from "@/features/breaks/workStatuses";
import { PRIORITY_ORDER } from "@/lib/domain";
import type { Priority, Reconciliation, Break } from "@/types/api";

export interface TriageGroup {
  priority: Priority;
  rows: Break[];
}

/** File du matin : suspens groupés par priorité (ordre du back), anomalies hors suspens, avancement local. */
export function useTriage(r: Reconciliation | null) {
  const { get } = useWorkStatuses(r);
  return useMemo(() => {
    const breaks = r?.breaks ?? [];
    const groups: TriageGroup[] = PRIORITY_ORDER.map((priority) => ({
      priority,
      rows: breaks.filter((s) => s.priority === priority),
    }));
    const offQueue = (r?.cleaning_log ?? []).filter(
      (a) => a.level === "EXCLU" || a.level === "SIGNALE",
    );
    const blockers = (r?.cleaning_log ?? []).filter((a) => a.level === "BLOQUANT");
    const treated = breaks.filter((s) => get(s) === "traite").length;
    const ids = groups.flatMap((g) => g.rows.map((s) => s.id));
    return { groups, offQueue, blockers, treated, ids, total: breaks.length };
  }, [r, get]);
}
