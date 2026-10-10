import { Mono } from "@/components/Mono";
import type { Comprehension } from "@/types/api";
import { formatConfidence, sourceLabel } from "./catalogue";

/** Traçabilité de la compréhension : ce que le LLM (ou le repli) a retenu, et pourquoi. */
export function TraceLine({ c }: { c: Comprehension }) {
  const paires: [string, string][] = [
    ["intention", c.intention],
    ["source", sourceLabel(c.source)],
    ["confiance", formatConfidence(c.confiance)],
  ];
  if (c.fonds) paires.push(["fonds", c.fonds]);
  if (c.horizon_mois) paires.push(["horizon", `${c.horizon_mois} mois`]);
  if (c.isin) paires.push(["isin", c.isin]);
  return (
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-subtle">
      {paires.map(([k, v]) => (
        <Mono key={k}>
          {k} <span className="text-muted-foreground">{v}</span>
        </Mono>
      ))}
      {c.detail && (
        <Mono>
          détail <span className="text-muted-foreground">{c.detail}</span>
        </Mono>
      )}
    </p>
  );
}
