import { ChevronRight, Copy } from "lucide-react";
import { useState } from "react";
import { Mono } from "@/components/Mono";
import { Button } from "@/components/ui/button";
import { useCopy } from "@/hooks/useCopy";
import { cn } from "@/lib/utils";

interface SqlDisclosureProps {
  sql: string;
  parametres: Record<string, string | null>;
}

/** La requête exacte exécutée et ses paramètres, rejouable telle quelle ; repliée par défaut. */
export function SqlDisclosure({ sql, parametres }: SqlDisclosureProps) {
  const [ouvert, setOuvert] = useState(false);
  const copier = useCopy();
  if (!sql) return null;
  const params = Object.entries(parametres);
  return (
    <div>
      <button
        onClick={() => setOuvert((o) => !o)}
        aria-expanded={ouvert}
        className="flex items-center gap-1.5 rounded text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ChevronRight
          className={cn("size-3.5 transition-transform duration-150", ouvert && "rotate-90")}
        />
        Requête SQL en lecture seule
        <span className="font-normal text-subtle">
          {params.length} paramètre{params.length > 1 ? "s" : ""}
        </span>
      </button>
      {ouvert && (
        <div className="mt-2 overflow-hidden rounded-lg border border-border animate-fade-in">
          <div className="flex items-center justify-between border-b border-border bg-surface px-3 py-1.5">
            <span className="flex flex-wrap gap-x-4 gap-y-1">
              {params.map(([k, v]) => (
                <Mono key={k} className="text-muted-foreground">
                  :{k} = <span className="text-foreground">{v ?? "NULL"}</span>
                </Mono>
              ))}
            </span>
            <Button variant="ghost" size="sm" onClick={() => copier(sql, "Requête SQL")}>
              <Copy />
              Copier
            </Button>
          </div>
          <pre className="overflow-x-auto px-3 py-2.5 font-mono text-xs leading-5">{sql}</pre>
        </div>
      )}
    </div>
  );
}
