import { StatusLabel } from "@/components/StatusDot";
import { useReconciliation } from "@/hooks/useReconciliation";
import { formatDate } from "@/lib/dates";
import { useQuestionSession } from "./sessionStore";

/** État de la compréhension (LLM ou repli mots-clés), budget du jour, date de référence de la base. */
export function LlmIndicator() {
  const { sante } = useReconciliation();
  const { runs } = useQuestionSession();
  if (!sante) return null;
  const { llm } = sante;
  // Le LLM peut être actif mais avoir échoué (clé, réseau, budget) : on le dit, d'après la dernière question.
  const derniere = runs.find((r) => r.comprehension)?.comprehension;
  const repli = llm.actif && derniere?.source === "mots_cles" && derniere.detail;
  return (
    <div className="space-y-1.5 text-sm">
      <StatusLabel tone={!llm.actif ? "gray" : repli ? "amber" : "green"} className="font-medium">
        {!llm.actif
          ? "LLM coupé : compréhension par mots-clés"
          : repli
            ? "LLM actif, dernière question en repli"
            : "Compréhension par LLM"}
      </StatusLabel>
      <p className="pl-[15px] text-xs text-muted-foreground">
        {llm.actif
          ? `${llm.modele}, ${llm.appels_aujourdhui} appels sur ${llm.budget_jour} aujourd'hui.`
          : "Les réponses restent exactes ; seules les questions libres sont moins bien comprises."}
        {repli && ` Raison : ${derniere.detail}.`}
      </p>
      <p className="pl-[15px] text-xs text-muted-foreground">
        Base de gestion au {formatDate(sante.date_arrete)}. Le LLM ne voit jamais les données.
      </p>
    </div>
  );
}
