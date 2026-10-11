import { Mono } from "@/components/Mono";
import type { Understanding } from "@/types/api";
import { formatConfidence, sourceLabel } from "./catalogue";

/** Traçabilité de la compréhension : ce que le LLM (ou le repli) a retenu, et pourquoi. */
export function TraceLine({ c }: { c: Understanding }) {
  const pairs: [string, string][] = [
    ["intention", c.intent],
    ["source", sourceLabel(c.source)],
    ["confiance", formatConfidence(c.confidence)],
  ];
  if (c.fund) pairs.push(["fonds", c.fund]);
  if (c.horizon_months) pairs.push(["horizon", `${c.horizon_months} mois`]);
  if (c.isin) pairs.push(["isin", c.isin]);
  return (
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-subtle">
      {pairs.map(([k, v]) => (
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
