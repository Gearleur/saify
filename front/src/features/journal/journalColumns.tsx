import type { Column } from "@/components/DataTable";
import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { LEVELS, LEVEL_ORDER } from "@/lib/domain";
import type { Anomaly } from "@/types/api";

export const anomalyId = (a: Anomaly) => `${a.file}:${a.line}:${a.rule}:${a.level}`;

function Reason({ a }: { a: Anomaly }) {
  return (
    <div className="py-0.5">
      <p>{a.reason}</p>
      {a.remedy && (
        <p className="text-muted-foreground">
          <span className="font-medium text-foreground">Que faire : </span>
          {a.remedy}
        </p>
      )}
    </div>
  );
}

/** Colonnes du journal de nettoyage (vue Journal et anomalies hors suspens de la matinée). */
export const LOG_COLUMNS: Column<Anomaly>[] = [
  {
    id: "level",
    header: "Niveau",
    className: "w-[112px] whitespace-nowrap",
    cell: (a) => <StatusLabel tone={LEVELS[a.level].tone}>{LEVELS[a.level].label}</StatusLabel>,
    compare: (a, b) => LEVEL_ORDER.indexOf(a.level) - LEVEL_ORDER.indexOf(b.level),
  },
  {
    id: "source",
    header: "Fichier et ligne",
    className: "whitespace-nowrap",
    cell: (a) => (
      <Mono className="block max-w-[260px] truncate">
        {a.file}
        <span className="text-subtle">:{a.line}</span>
      </Mono>
    ),
    compare: (a, b) => a.file.localeCompare(b.file) || a.line - b.line,
  },
  {
    id: "rule",
    header: "Règle",
    className: "hidden whitespace-nowrap @3xl:table-cell",
    cell: (a) => (
      <Mono className="block max-w-[200px] truncate text-muted-foreground">{a.rule}</Mono>
    ),
    compare: (a, b) => a.rule.localeCompare(b.rule),
  },
  {
    id: "reason",
    header: "Motif",
    className: "w-full min-w-[260px]",
    cell: (a) => <Reason a={a} />,
  },
  {
    id: "raw",
    header: "Valeur brute → retenue",
    className: "hidden whitespace-nowrap @5xl:table-cell",
    cell: (a) => (
      <Mono className="block max-w-[280px] truncate text-muted-foreground" title={a.raw}>
        {a.raw || "∅"}
        {a.kept && <span className="text-foreground"> → {a.kept}</span>}
      </Mono>
    ),
  },
];
