import type { DotTone } from "@/lib/metier";
import { cn } from "@/lib/utils";
import { StatusDot } from "./StatusDot";

export interface Kpi {
  id: string;
  label: string;
  value: string | number;
  tone?: DotTone;
  hint?: string;
  onSelect?: () => void;
}

/** Chiffres nus séparés par un filet : aucune boîte, aucune couleur de fond. */
export function KpiRow({ items, className }: { items: Kpi[]; className?: string }) {
  return (
    <div className={cn("flex flex-wrap divide-x divide-border", className)}>
      {items.map((kpi) => {
        const contenu = (
          <>
            <span className="flex items-center gap-2 text-xs text-muted-foreground">
              {kpi.tone && <StatusDot tone={kpi.tone} />}
              {kpi.label}
            </span>
            <span className="mt-0.5 block text-figure">
              {kpi.value}
            </span>
            {kpi.hint && <span className="block text-xs text-subtle">{kpi.hint}</span>}
          </>
        );
        const classes = "min-w-[120px] px-5 py-0.5 text-left first:pl-0";
        return kpi.onSelect ? (
          <button
            key={kpi.id}
            onClick={kpi.onSelect}
            className={cn(
              classes,
              "rounded-sm transition-colors duration-150 hover:[&>span:nth-child(2)]:text-link",
            )}
          >
            {contenu}
          </button>
        ) : (
          <div key={kpi.id} className={classes}>
            {contenu}
          </div>
        );
      })}
    </div>
  );
}
