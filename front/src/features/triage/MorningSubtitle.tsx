import { useReconciliation } from "@/hooks/useReconciliation";
import { asOfLabel, formatTime } from "@/lib/dates";

/** Phrase d'état : quel arrêté, lancé quand, et ce qu'il reste à faire. */
export function MorningSubtitle() {
  const { current, loading } = useReconciliation();
  if (loading === "startup") return "Chargement du dernier rapprochement…";
  if (!current)
    return "Aucun rapprochement aujourd'hui. Déposez les 4 fichiers du jour ou lancez l'exemple.";
  const quand = `${asOfLabel(current.as_of_date)}, lancé à ${formatTime(current.created_at)}.`;
  if (current.status === "BLOQUE")
    return `${quand} Bloqué : corrigez le fichier refusé puis relancez.`;
  const { critique, a_relever } = current.summary.by_priority;
  if (critique > 0)
    return `${quand} Commencez par les ${critique} suspens critiques (risque CSDR).`;
  if (a_relever > 0) return `${quand} Aucun critique : ${a_relever} suspens à relever.`;
  return `${quand} Rien à relever.`;
}
