import { StatusLabel } from "@/components/StatusDot";
import { useReconciliation } from "@/hooks/useReconciliation";
import { formatDate } from "@/lib/dates";
import { useQuestionSession } from "./sessionStore";

/** État de la compréhension (LLM ou repli mots-clés), budget du jour, date de référence de la base. */
export function LlmIndicator() {
  const { health } = useReconciliation();
  const { runs } = useQuestionSession();
  if (!health) return null;
  const { llm } = health;
  // Le LLM peut être actif mais avoir échoué (clé, réseau, budget) : on le dit, d'après la dernière question.
  const latest = runs.find((r) => r.understanding)?.understanding;
  const fallback = llm.enabled && latest?.source === "mots_cles" && latest.detail;
  return (
    <div className="space-y-1.5 text-sm">
      <StatusLabel
        tone={!llm.enabled ? "gray" : fallback ? "amber" : "green"}
        className="font-medium"
      >
        {!llm.enabled
          ? "LLM coupé : compréhension par mots-clés"
          : fallback
            ? "LLM actif, dernière question en repli"
            : "Compréhension par LLM"}
      </StatusLabel>
      <p className="pl-[15px] text-xs text-muted-foreground">
        {llm.enabled
          ? `${llm.model}, ${llm.calls_today} appels sur ${llm.daily_budget} aujourd'hui.`
          : "Les réponses restent exactes ; seules les questions libres sont moins bien comprises."}
        {fallback && ` Raison : ${latest.detail}.`}
      </p>
      <p className="pl-[15px] text-xs text-muted-foreground">
        Base de gestion au {formatDate(health.as_of_date)}. Le LLM ne voit jamais les données.
      </p>
    </div>
  );
}
