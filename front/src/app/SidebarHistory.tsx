import { StatusDot } from "@/components/StatusDot";
import { useReconciliation } from "@/hooks/useReconciliation";
import { formatDateShort, formatStamp } from "@/lib/dates";
import { cn } from "@/lib/utils";

/** Historique des rapprochements (20 plus récents), rechargeable d'un clic. */
export function SidebarHistory() {
  const { historique, courant, ouvrir } = useReconciliation();
  if (historique.length === 0)
    return <p className="px-2 text-xs text-subtle">Aucun rapprochement enregistré.</p>;
  return (
    <ul className="space-y-px">
      {historique.map((r) => (
        <li key={r.id}>
          <button
            onClick={() => void ouvrir(r.id).catch(() => undefined)}
            className={cn(
              "flex h-control w-full items-center gap-2 rounded-md px-2 text-left text-xs text-muted-foreground transition-colors duration-150 hover:bg-hover hover:text-foreground",
              courant?.id === r.id && "bg-hover text-foreground",
            )}
            title={`Lancé le ${formatStamp(r.cree_le)}`}
          >
            <StatusDot tone={r.statut === "BLOQUE" ? "red" : "gray"} />
            <span className="truncate whitespace-nowrap font-medium">
              {r.date_arrete ? `Arrêté ${formatDateShort(r.date_arrete)}` : "Date inconnue"}
            </span>
            <span className="shrink-0 text-subtle">{formatStamp(r.cree_le).split(" ")[1]}</span>
            <span className="ml-auto shrink-0 tabular-nums">
              {r.statut === "BLOQUE" ? "bloqué" : r.nb_suspens}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
