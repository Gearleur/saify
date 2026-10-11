import { Check } from "lucide-react";
import { useState } from "react";
import { Mono } from "@/components/Mono";
import { StatusDot } from "@/components/StatusDot";
import { cn } from "@/lib/utils";
import type { Anomaly } from "@/types/api";
import { anomalyId } from "@/features/journal/journalColumns";

/** Rapprochement bloqué : chaque fichier refusé, et quoi faire, en liste à cocher pour suivre la relance. */
export function BlockingBanner({ blockers }: { blockers: Anomaly[] }) {
  const [fixed, setFixed] = useState<Set<string>>(new Set());
  const toggleOpen = (id: string) =>
    setFixed((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <section role="alert" className="rounded-lg border border-danger-line bg-danger-wash">
      <header className="flex items-center gap-2 px-4 pt-3">
        <StatusDot tone="red" />
        <h2 className="text-sm font-semibold">Rapprochement bloqué</h2>
        <span className="text-sm text-muted-foreground">
          {blockers.length === 1 ? "1 fichier refusé" : `${blockers.length} refus`}, aucun suspens
          n'est calculé tant qu'il n'est pas corrigé.
        </span>
      </header>
      <ul className="px-2 pb-2 pt-1">
        {blockers.map((a) => {
          const id = anomalyId(a);
          const fait = fixed.has(id);
          return (
            <li key={id} className="flex gap-3 rounded-md px-2 py-2">
              <button
                role="checkbox"
                aria-checked={fait}
                aria-label="Marquer comme corrigé"
                onClick={() => toggleOpen(id)}
                className={cn(
                  "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-[4px] border border-border-strong bg-background",
                  fait && "border-foreground bg-foreground text-background",
                )}
              >
                {fait && <Check className="size-3" strokeWidth={3} />}
              </button>
              <div
                className={cn(
                  "min-w-0 text-sm",
                  fait && "text-muted-foreground line-through decoration-subtle",
                )}
              >
                <p>
                  <Mono>
                    {a.file}
                    {a.line > 0 && `:${a.line}`}
                  </Mono>
                  <Mono className="ml-2 text-muted-foreground">{a.rule}</Mono>
                </p>
                <p className="mt-0.5">
                  {a.reason}
                  {a.raw && <Mono className="ml-1.5 text-muted-foreground">« {a.raw} »</Mono>}
                </p>
                <p className="mt-0.5">
                  <span className="font-medium">Que faire : </span>
                  {a.remedy}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
