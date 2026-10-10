import { useReconciliation } from "@/hooks/useReconciliation";
import { arreteLabel, formatTime } from "@/lib/dates";

/** Phrase d'état : quel arrêté, lancé quand, et ce qu'il reste à faire. */
export function MorningSubtitle() {
  const { courant, chargement } = useReconciliation();
  if (chargement === "demarrage") return "Chargement du dernier rapprochement…";
  if (!courant)
    return "Aucun rapprochement aujourd'hui. Déposez les 4 fichiers du jour ou lancez l'exemple.";
  const quand = `${arreteLabel(courant.date_arrete)}, lancé à ${formatTime(courant.cree_le)}.`;
  if (courant.statut === "BLOQUE")
    return `${quand} Bloqué : corrigez le fichier refusé puis relancez.`;
  const { critique, a_relever } = courant.synthese.par_priorite;
  if (critique > 0)
    return `${quand} Commencez par les ${critique} suspens critiques (risque CSDR).`;
  if (a_relever > 0) return `${quand} Aucun critique : ${a_relever} suspens à relever.`;
  return `${quand} Rien à relever.`;
}
