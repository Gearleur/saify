import { StatusLabel } from "@/components/StatusDot";
import { useReconciliation } from "@/hooks/useReconciliation";

/** Santé de l'API en pied de barre latérale : version, base de gestion, LLM. */
export function ApiHealth() {
  const { sante, santeError } = useReconciliation();
  if (santeError) return <StatusLabel tone="red">API injoignable</StatusLabel>;
  if (!sante)
    return (
      <StatusLabel tone="gray" pulse>
        Connexion à l'API…
      </StatusLabel>
    );
  return (
    <div className="flex flex-col gap-1">
      <StatusLabel tone={sante.base_disponible ? "green" : "amber"}>
        {sante.base_disponible ? `API ${sante.version}` : "Base de gestion indisponible"}
      </StatusLabel>
      <StatusLabel tone={sante.llm.actif ? "green" : "gray"} className="text-muted-foreground">
        {sante.llm.actif
          ? `LLM ${sante.llm.appels_aujourdhui} / ${sante.llm.budget_jour} appels`
          : "LLM coupé (mots-clés)"}
      </StatusLabel>
    </div>
  );
}
