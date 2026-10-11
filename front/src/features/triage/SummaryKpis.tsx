import { KpiRow } from "@/components/KpiRow";
import { PRIORITY_ORDER, PRIORITIES } from "@/lib/domain";
import type { Summary } from "@/types/api";

interface SummaryKpisProps {
  summary: Summary;
  treated: number;
}

/** Synthèse : un compteur par priorité (un clic fait défiler jusqu'au groupe), et l'avancement local. */
export function SummaryKpis({ summary, treated }: SummaryKpisProps) {
  const scrollToGroup = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  return (
    <KpiRow
      items={[
        ...PRIORITY_ORDER.map((p) => ({
          id: p,
          label: PRIORITIES[p].label,
          value: summary.by_priority[p] ?? 0,
          tone: PRIORITIES[p].tone,
          onSelect: () => scrollToGroup(`groupe-${p}`),
        })),
        {
          id: "treated",
          label: "Traités",
          value: `${treated} / ${summary.break_count}`,
          tone: "green" as const,
        },
      ]}
    />
  );
}
