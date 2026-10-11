import { ChevronRight, Copy } from "lucide-react";
import { useState } from "react";
import { Mono } from "@/components/Mono";
import { Button } from "@/components/ui/button";
import { useCopy } from "@/hooks/useCopy";
import { cn } from "@/lib/utils";

interface SqlDisclosureProps {
  sql: string;
  params: Record<string, string | null>;
}

/** La requête exacte exécutée et ses paramètres, rejouable telle quelle ; repliée par défaut. */
export function SqlDisclosure({ sql, params }: SqlDisclosureProps) {
  const [isOpen, setIsOpen] = useState(false);
  const copy = useCopy();
  if (!sql) return null;
  const entries = Object.entries(params);
  return (
    <div>
      <button
        onClick={() => setIsOpen((o) => !o)}
        aria-expanded={isOpen}
        className="flex items-center gap-1.5 rounded text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ChevronRight
          className={cn("size-3.5 transition-transform duration-150", isOpen && "rotate-90")}
        />
        Requête SQL en lecture seule
        <span className="font-normal text-subtle">
          {entries.length} paramètre{entries.length > 1 ? "s" : ""}
        </span>
      </button>
      {isOpen && (
        <div className="mt-2 overflow-hidden rounded-lg border border-border animate-fade-in">
          <div className="flex items-center justify-between border-b border-border bg-surface px-3 py-1.5">
            <span className="flex flex-wrap gap-x-4 gap-y-1">
              {entries.map(([k, v]) => (
                <Mono key={k} className="text-muted-foreground">
                  :{k} = <span className="text-foreground">{v ?? "NULL"}</span>
                </Mono>
              ))}
            </span>
            <Button variant="ghost" size="sm" onClick={() => copy(sql, "Requête SQL")}>
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
