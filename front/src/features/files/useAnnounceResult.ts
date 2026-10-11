import { useCallback } from "react";
import { useToast } from "@/hooks/useToast";
import { reconciliationLabel } from "@/lib/dates";
import type { Reconciliation } from "@/types/api";

/** Message de toast de fin de rapprochement, identique pour l'exemple et le dépôt. */
export function useAnnounceResult() {
  const { toast } = useToast();
  return useCallback(
    (r: Reconciliation) => {
      if (r.status === "BLOQUE") {
        toast({
          title: "Rapprochement bloqué",
          description: "Un fichier est refusé : voir le bandeau.",
          tone: "red",
        });
      } else {
        toast({
          title: `${reconciliationLabel(r.as_of_date)} terminé`,
          description: `${r.summary.break_count} suspens, dont ${r.summary.by_priority.critique} critique(s).`,
        });
      }
    },
    [toast],
  );
}
