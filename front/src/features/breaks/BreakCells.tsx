import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { SHORT_TYPES } from "@/lib/domain";
import type { WorkStatus, Break } from "@/types/api";
import { WORK_STATUSES } from "./workStatuses";

/** Largeur de table (requête de conteneur) à partir de laquelle l'action a sa propre colonne. */
export const ACTION_AS_COLUMN = "@5xl:table-cell";

/**
 * Titre (texte principal) et ISIN (secondaire) ; le type d'écart en infobulle.
 * `withAction` : sous `@5xl`, l'action attendue passe sous le titre plutôt que d'être tronquée.
 */
export function TitleCell({ s, withAction = false }: { s: Break; withAction?: boolean }) {
  const csdr = s.alerts.includes("CSDR");
  return (
    <Tooltip delayDuration={500}>
      <TooltipTrigger asChild>
        <span className="block min-w-0">
          <span className="flex min-w-0 items-baseline gap-2">
            <span className="truncate font-medium">{s.security_name}</span>
            <Mono className="shrink-0 text-subtle">{s.isin}</Mono>
            {csdr && <span className="shrink-0 text-2xs font-medium text-dot-red">CSDR</span>}
          </span>
          {withAction && (
            <span className="block truncate text-xs text-muted-foreground @5xl:hidden">
              {s.action}
            </span>
          )}
        </span>
      </TooltipTrigger>
      <TooltipContent side="bottom" align="start">
        {s.type} : {s.break_type_label}
      </TooltipContent>
    </Tooltip>
  );
}

export function TypeCell({ s }: { s: Break }) {
  return <span className="text-muted-foreground">{SHORT_TYPES[s.type] ?? s.type}</span>;
}

export function StatusCell({ status }: { status: WorkStatus }) {
  const info = WORK_STATUSES[status];
  return (
    <StatusLabel
      tone={info.tone}
      className={status === "a_traiter" ? "text-muted-foreground" : undefined}
    >
      {info.label}
    </StatusLabel>
  );
}
