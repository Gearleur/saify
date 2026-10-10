import { useState } from "react";
import { Mono } from "@/components/Mono";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { LigneSource } from "@/types/api";
import { formatSourceValue, headerLabel, isNumericKey, sourceColumns } from "./sourceRows";

const APERCU = 8;

/** Lignes sources de la réponse : chaque chiffre se retrouve, ligne par ligne. */
export function SourceRowsTable({ lignes }: { lignes: LigneSource[] }) {
  const [tout, setTout] = useState(false);
  if (lignes.length === 0) return null;
  const { cles, avecTable } = sourceColumns(lignes);
  const visibles = tout ? lignes : lignes.slice(0, APERCU);
  const th = "h-8 whitespace-nowrap px-3 text-xs font-medium text-muted-foreground first:pl-1";
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border">
              {avecTable && <th className={cn(th, "text-left")}>Source</th>}
              {cles.map((k) => (
                <th key={k} className={cn(th, isNumericKey(k) ? "text-right" : "text-left")}>
                  {headerLabel(k)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibles.map((l, i) => (
              <tr key={i} className="h-9 border-b border-border">
                {avecTable && (
                  <td className="whitespace-nowrap px-3 pl-1">
                    <Mono className="text-muted-foreground">{l.table}</Mono>
                  </td>
                )}
                {cles.map((k) => (
                  <td
                    key={k}
                    className={cn(
                      "whitespace-nowrap px-3 first:pl-1",
                      isNumericKey(k) && "text-right",
                    )}
                  >
                    {k === "isin" ? (
                      <Mono>{l.valeurs[k]}</Mono>
                    ) : (
                      formatSourceValue(k, l.valeurs[k])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3 pt-2 text-xs text-subtle">
        {!avecTable && (
          <span>
            Table <Mono>{lignes[0]?.table}</Mono>
          </span>
        )}
        {lignes.length > APERCU && (
          <Button variant="link" size="sm" onClick={() => setTout((t) => !t)}>
            {tout ? "Réduire" : `Afficher les ${lignes.length} lignes`}
          </Button>
        )}
      </div>
    </div>
  );
}
