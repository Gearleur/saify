import { StatusDot } from "@/components/StatusDot";
import { cn } from "@/lib/utils";
import { STATUTS_TRAITEMENT, ORDRE_STATUTS } from "./statutsTraitement";
import type { StatutTraitement } from "@/types/api";

interface StatutControlProps {
  value: StatutTraitement;
  onChange: (value: StatutTraitement) => void;
}

/** Contrôle segmenté À traiter / En cours / Traité (partagé avec l'équipe, chaque changement tracé). */
export function StatutControl({ value, onChange }: StatutControlProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Statut de traitement"
      className="inline-flex rounded-md border border-border-strong p-0.5"
    >
      {ORDRE_STATUTS.map((s) => (
        <button
          key={s}
          role="radio"
          aria-checked={value === s}
          onClick={() => onChange(s)}
          className={cn(
            "flex h-6 items-center gap-2 rounded-[5px] px-2.5 text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground",
            value === s &&
              "bg-hover font-medium text-foreground shadow-[inset_0_0_0_1px_var(--border-strong)]",
          )}
        >
          <StatusDot tone={STATUTS_TRAITEMENT[s].tone} />
          {STATUTS_TRAITEMENT[s].label}
        </button>
      ))}
    </div>
  );
}
