import { Check } from "lucide-react";
import { useState } from "react";
import { Mono } from "@/components/Mono";
import { StatusDot } from "@/components/StatusDot";
import { cn } from "@/lib/utils";
import type { Anomalie } from "@/types/api";
import { anomalieId } from "@/features/journal/journalColumns";

/** Rapprochement bloqué : chaque fichier refusé, et quoi faire, en liste à cocher pour suivre la relance. */
export function BlockingBanner({ blocages }: { blocages: Anomalie[] }) {
  const [corriges, setCorriges] = useState<Set<string>>(new Set());
  const basculer = (id: string) =>
    setCorriges((s) => {
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
          {blocages.length === 1 ? "1 fichier refusé" : `${blocages.length} refus`}, aucun suspens
          n'est calculé tant qu'il n'est pas corrigé.
        </span>
      </header>
      <ul className="px-2 pb-2 pt-1">
        {blocages.map((a) => {
          const id = anomalieId(a);
          const fait = corriges.has(id);
          return (
            <li key={id} className="flex gap-3 rounded-md px-2 py-2">
              <button
                role="checkbox"
                aria-checked={fait}
                aria-label="Marquer comme corrigé"
                onClick={() => basculer(id)}
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
                    {a.fichier}
                    {a.ligne > 0 && `:${a.ligne}`}
                  </Mono>
                  <Mono className="ml-2 text-muted-foreground">{a.regle}</Mono>
                </p>
                <p className="mt-0.5">
                  {a.motif}
                  {a.brut && <Mono className="ml-1.5 text-muted-foreground">« {a.brut} »</Mono>}
                </p>
                <p className="mt-0.5">
                  <span className="font-medium">Que faire : </span>
                  {a.remede}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
