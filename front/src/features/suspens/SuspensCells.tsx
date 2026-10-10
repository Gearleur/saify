import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { isCsdr, TYPES_COURTS } from "@/lib/metier";
import type { Suspens } from "@/types/api";
import { LOCAL_STATUS, type LocalStatus } from "./localStatus";

/** Titre et ISIN sur une ligne ; le type d'écart en infobulle. */
export function TitleCell({ s }: { s: Suspens }) {
  const csdr = s.signalements.some(isCsdr);
  return (
    <Tooltip delayDuration={500}>
      <TooltipTrigger asChild>
        <span className="flex min-w-0 items-baseline gap-2">
          <span className="truncate font-medium">{s.libelle_titre}</span>
          <Mono className="shrink-0 text-subtle">{s.isin}</Mono>
          {csdr && <span className="shrink-0 text-xs text-dot-red">CSDR</span>}
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

export function StatusCell({ status }: { status: LocalStatus }) {
  const info = LOCAL_STATUS[status];
  return (
    <StatusLabel
      tone={info.tone}
      className={status === "a_traiter" ? "text-muted-foreground" : undefined}
    >
      {info.label}
    </StatusLabel>
  );
}
