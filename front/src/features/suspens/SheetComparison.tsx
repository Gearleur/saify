import { Quantity } from "@/components/Quantity";
import { useReferentiel } from "@/hooks/useReferentiel";
import type { Suspens } from "@/types/api";

/** PMS, conservateur, écart : trois chiffres nus, l'écart signé (PMS moins conservateur). */
export function SheetComparison({ s }: { s: Suspens }) {
  const { nomConservateur } = useReferentiel();
  const cellules = [
    { label: "PMS", value: <Quantity value={s.qte_pms} /> },
    { label: nomConservateur(s.conservateur), value: <Quantity value={s.qte_dep} /> },
    { label: "Écart", value: <Quantity value={s.ecart} signed /> },
  ];
  return (
    <div className="grid grid-cols-3 divide-x divide-border rounded-lg border border-border">
      {cellules.map((c) => (
        <div key={c.label} className="min-w-0 px-3 py-2.5">
          <p className="truncate text-xs text-muted-foreground">{c.label}</p>
          <p className="mt-0.5 text-[17px] font-semibold tracking-[-0.01em]">{c.value}</p>
        </div>
      ))}
    </div>
  );
}
