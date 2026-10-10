import { StatusDot } from "@/components/StatusDot";
import { cn } from "@/lib/utils";
import { LOCAL_STATUS, ORDRE_STATUTS, type LocalStatus } from "./localStatus";

interface LocalStatusControlProps {
  value: LocalStatus;
  onChange: (value: LocalStatus) => void;
}

/** Contrôle segmenté À traiter / En cours / Traité (enregistré sur ce poste). */
export function LocalStatusControl({ value, onChange }: LocalStatusControlProps) {
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
            "flex h-7 items-center gap-2 rounded-[5px] px-2.5 text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground",
            value === s &&
              "bg-hover font-medium text-foreground shadow-[inset_0_0_0_1px_var(--border-strong)]",
          )}
        >
          <StatusDot tone={LOCAL_STATUS[s].tone} />
          {LOCAL_STATUS[s].label}
        </button>
      ))}
    </div>
  );
}
