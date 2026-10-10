import { useCallback } from "react";
import { useToast } from "@/hooks/useToast";
import { rapprochementLabel } from "@/lib/dates";
import type { Rapprochement } from "@/types/api";

/** Message de toast de fin de rapprochement, identique pour l'exemple et le dépôt. */
export function useAnnounceResult() {
  const { toast } = useToast();
  return useCallback(
    (r: Rapprochement) => {
      if (r.statut === "BLOQUE") {
        toast({
          title: "Rapprochement bloqué",
          description: "Un fichier est refusé : voir le bandeau.",
          tone: "red",
        });
      } else {
        toast({
          title: `${rapprochementLabel(r.date_arrete)} terminé`,
          description: `${r.synthese.nb_suspens} suspens, dont ${r.synthese.par_priorite.critique} critique(s).`,
        });
      }
    },
    [toast],
  );
}
