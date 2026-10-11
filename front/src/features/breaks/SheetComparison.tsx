import { Quantity } from "@/components/Quantity";
import { useReferenceData } from "@/hooks/useReferenceData";
import type { Break } from "@/types/api";

/** PMS, conservateur, écart : trois chiffres nus, l'écart signé (PMS moins conservateur). */
export function SheetComparison({ s }: { s: Break }) {
  const { custodianName } = useReferenceData();
  const cells = [
    { label: "PMS", value: <Quantity value={s.pms_qty} /> },
    { label: custodianName(s.custodian), value: <Quantity value={s.custodian_qty} /> },
    { label: "Écart", value: <Quantity value={s.difference} signed /> },
  ];
  return (
    <div className="grid grid-cols-3 divide-x divide-border rounded-lg border border-border">
      {cells.map((c) => (
        <div key={c.label} className="min-w-0 px-3 py-2">
          <p className="truncate text-xs text-muted-foreground">{c.label}</p>
          <p className="mt-0.5 text-heading">{c.value}</p>
        </div>
      ))}
    </div>
  );
}
