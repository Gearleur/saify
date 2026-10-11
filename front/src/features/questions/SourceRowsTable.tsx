import { useState } from "react";
import { Mono } from "@/components/Mono";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SourceRow } from "@/types/api";
import { formatSourceValue, headerLabel, isNumericKey, sourceColumns } from "./sourceRows";

const PREVIEW = 8;

/** Lignes sources de la réponse : chaque chiffre se retrouve, ligne par ligne. */
export function SourceRowsTable({ lines }: { lines: SourceRow[] }) {
  const [showAll, setShowAll] = useState(false);
  if (lines.length === 0) return null;
  const { keys, withTable } = sourceColumns(lines);
  const shown = showAll ? lines : lines.slice(0, PREVIEW);
  const th = "h-8 whitespace-nowrap px-3 text-xs font-medium text-muted-foreground first:pl-1";
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border">
              {withTable && <th className={cn(th, "text-left")}>Source</th>}
              {keys.map((k) => (
                <th key={k} className={cn(th, isNumericKey(k) ? "text-right" : "text-left")}>
                  {headerLabel(k)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((l, i) => (
              <tr key={i} className="h-9 border-b border-border">
                {withTable && (
                  <td className="whitespace-nowrap px-3 pl-1">
                    <Mono className="text-muted-foreground">{l.table}</Mono>
                  </td>
                )}
                {keys.map((k) => (
                  <td
                    key={k}
                    className={cn(
                      "whitespace-nowrap px-3 first:pl-1",
                      isNumericKey(k) && "text-right",
                    )}
                  >
                    {k === "isin" ? <Mono>{l.values[k]}</Mono> : formatSourceValue(k, l.values[k])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3 pt-2 text-xs text-subtle">
        {!withTable && (
          <span>
            Table <Mono>{lines[0]?.table}</Mono>
          </span>
        )}
        {lines.length > PREVIEW && (
          <Button variant="link" size="sm" onClick={() => setShowAll((t) => !t)}>
            {showAll ? "Réduire" : `Afficher les ${lines.length} lignes`}
          </Button>
        )}
      </div>
    </div>
  );
}
