import { useReconciliation } from "@/hooks/useReconciliation";
import { useReferentiel } from "@/hooks/useReferentiel";
import { formatSize } from "@/lib/dates";
import { FileSlot } from "./FileSlot";
import { receivedSlots, type ReceivedState } from "./fileStates";

const ETATS: Record<ReceivedState, { label: string; tone: "green" | "red" | "ring" }> = {
  accepte: { label: "Accepté", tone: "green" },
  refuse: { label: "Refusé", tone: "red" },
  absent: { label: "Non reçu", tone: "ring" },
};

/** Les 4 fichiers du dernier rapprochement : reçu, accepté ou refusé. */
export function ReceivedStrip() {
  const { courant } = useReconciliation();
  const { nomConservateur } = useReferentiel();
  return (
    <>
      {receivedSlots(courant).map(({ attendu, fichier, etat, blocage }) => (
        <FileSlot
          key={attendu.source}
          code={attendu.label}
          nom={attendu.source === "PMS" ? "Inventaire interne" : nomConservateur(attendu.source)}
          format={attendu.format}
          fichier={fichier?.nom ?? null}
          tone={ETATS[etat].tone}
          etat={blocage ? `${ETATS[etat].label}, règle ${blocage.regle}` : ETATS[etat].label}
          meta={fichier ? formatSize(fichier.taille) : undefined}
          refuse={etat === "refuse"}
        />
      ))}
    </>
  );
}
