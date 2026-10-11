import { StatusLabel } from "@/components/StatusDot";
import { useReconciliation } from "@/hooks/useReconciliation";

/** Santé de l'API en pied de barre latérale : version, base de gestion, LLM. */
export function ApiHealth() {
  const { health, healthError } = useReconciliation();
  if (healthError) return <StatusLabel tone="red">API injoignable</StatusLabel>;
  if (!health)
    return (
      <StatusLabel tone="gray" pulse>
        Connexion à l'API…
      </StatusLabel>
    );
  return (
    <div className="flex flex-col gap-1">
      <StatusLabel tone={health.db_available ? "green" : "amber"}>
        {health.db_available ? `API ${health.version}` : "Base de gestion indisponible"}
      </StatusLabel>
      <StatusLabel tone={health.llm.enabled ? "green" : "gray"} className="text-muted-foreground">
        {health.llm.enabled
          ? `LLM ${health.llm.calls_today} / ${health.llm.daily_budget} appels`
          : "LLM coupé (mots-clés)"}
      </StatusLabel>
    </div>
  );
}
