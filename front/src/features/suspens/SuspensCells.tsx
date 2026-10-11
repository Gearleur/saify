import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { TYPES_COURTS } from "@/lib/metier";
import type { StatutTraitement, Suspens } from "@/types/api";
import { STATUTS_TRAITEMENT } from "./statutsTraitement";

/** Largeur de table (requête de conteneur) à partir de laquelle l'action a sa propre colonne. */
export const ACTION_EN_COLONNE = "@5xl:table-cell";

/**
 * Titre (texte principal) et ISIN (secondaire) ; le type d'écart en infobulle.
 * `withAction` : sous `@5xl`, l'action attendue passe sous le titre plutôt que d'être tronquée.
 */
export function TitleCell({ s, withAction = false }: { s: Suspens; withAction?: boolean }) {
  const csdr = s.alertes.includes("CSDR");
  return (
    <Tooltip delayDuration={500}>
      <TooltipTrigger asChild>
        <span className="block min-w-0">
          <span className="flex min-w-0 items-baseline gap-2">
            <span className="truncate font-medium">{s.libelle_titre}</span>
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
        {s.type} : {s.libelle_type}
      </TooltipContent>
    </Tooltip>
  );
}

export function TypeCell({ s }: { s: Suspens }) {
  return <span className="text-muted-foreground">{TYPES_COURTS[s.type] ?? s.type}</span>;
}

export function StatusCell({ status }: { status: StatutTraitement }) {
  const info = STATUTS_TRAITEMENT[status];
  return (
    <StatusLabel
      tone={info.tone}
      className={status === "a_traiter" ? "text-muted-foreground" : undefined}
    >
      {info.label}
    </StatusLabel>
  );
}
