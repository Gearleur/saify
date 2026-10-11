import { StatusDot } from "@/components/StatusDot";
import { useReconciliation } from "@/hooks/useReconciliation";
import { formatDateShort, formatStamp } from "@/lib/dates";
import { cn } from "@/lib/utils";

/** Historique des rapprochements (20 plus récents), rechargeable d'un clic. */
export function SidebarHistory() {
  const { history, current, openReconciliation } = useReconciliation();
  if (history.length === 0)
    return <p className="px-2 text-xs text-subtle">Aucun rapprochement enregistré.</p>;
  return (
    <ul className="space-y-px">
      {history.map((r) => (
        <li key={r.id}>
          <button
            onClick={() => void openReconciliation(r.id).catch(() => undefined)}
            className={cn(
              "flex h-control w-full items-center gap-2 rounded-md px-2 text-left text-xs text-muted-foreground transition-colors duration-150 hover:bg-hover hover:text-foreground",
              current?.id === r.id && "bg-hover text-foreground",
            )}
            title={`Lancé le ${formatStamp(r.created_at)}`}
          >
            <StatusDot tone={r.status === "BLOQUE" ? "red" : "gray"} />
            <span className="truncate whitespace-nowrap font-medium">
              {r.as_of_date ? `Arrêté ${formatDateShort(r.as_of_date)}` : "Date inconnue"}
            </span>
            <span className="shrink-0 text-subtle">{formatStamp(r.created_at).split(" ")[1]}</span>
            <span className="ml-auto shrink-0 tabular-nums">
              {r.status === "BLOQUE" ? "bloqué" : r.break_count}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
