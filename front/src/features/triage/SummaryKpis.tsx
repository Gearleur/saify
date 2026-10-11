import { KpiRow } from "@/components/KpiRow";
import { ORDRE_PRIORITES, PRIORITES } from "@/lib/metier";
import type { Synthese } from "@/types/api";

interface SummaryKpisProps {
  synthese: Synthese;
  traites: number;
}

/** Synthèse : un compteur par priorité (un clic fait défiler jusqu'au groupe), et l'avancement local. */
export function SummaryKpis({ synthese, traites }: SummaryKpisProps) {
  const defiler = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  return (
    <KpiRow
      items={[
        ...ORDRE_PRIORITES.map((p) => ({
          id: p,
          label: PRIORITES[p].label,
          value: synthese.par_priorite[p] ?? 0,
          tone: PRIORITES[p].tone,
          onSelect: () => defiler(`groupe-${p}`),
        })),
        {
          id: "traites",
          label: "Traités",
          value: `${traites} / ${synthese.nb_suspens}`,
          tone: "green" as const,
        },
      ]}
    />
  );
}
