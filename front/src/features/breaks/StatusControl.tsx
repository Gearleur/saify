import { StatusDot } from "@/components/StatusDot";
import { cn } from "@/lib/utils";
import { WORK_STATUSES, STATUS_ORDER } from "./workStatuses";
import type { WorkStatus } from "@/types/api";

interface StatusControlProps {
  value: WorkStatus;
  onChange: (value: WorkStatus) => void;
}

/** Contrôle segmenté À traiter / En cours / Traité (partagé avec l'équipe, chaque changement tracé). */
export function StatusControl({ value, onChange }: StatusControlProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Statut de traitement"
      className="inline-flex rounded-md border border-border-strong p-0.5"
    >
      {STATUS_ORDER.map((s) => (
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
          <StatusDot tone={WORK_STATUSES[s].tone} />
          {WORK_STATUSES[s].label}
        </button>
      ))}
    </div>
  );
}
