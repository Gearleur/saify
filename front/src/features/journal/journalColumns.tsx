import type { Column } from "@/components/DataTable";
import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { NIVEAUX, ORDRE_NIVEAUX } from "@/lib/metier";
import type { Anomalie } from "@/types/api";

export const anomalieId = (a: Anomalie) => `${a.fichier}:${a.ligne}:${a.regle}:${a.niveau}`;

function Motif({ a }: { a: Anomalie }) {
  return (
    <div className="py-0.5">
      <p>{a.motif}</p>
      {a.remede && (
        <p className="text-muted-foreground">
          <span className="font-medium text-foreground">Que faire : </span>
          {a.remede}
        </p>
      )}
    </div>
  );
}

/** Colonnes du journal de nettoyage (vue Journal et anomalies hors suspens de la matinée). */
export const JOURNAL_COLUMNS: Column<Anomalie>[] = [
  {
    id: "niveau",
    header: "Niveau",
    className: "w-[112px] whitespace-nowrap",
    cell: (a) => <StatusLabel tone={NIVEAUX[a.niveau].tone}>{NIVEAUX[a.niveau].label}</StatusLabel>,
    compare: (a, b) => ORDRE_NIVEAUX.indexOf(a.niveau) - ORDRE_NIVEAUX.indexOf(b.niveau),
  },
  {
    id: "source",
    header: "Fichier et ligne",
    className: "whitespace-nowrap",
    cell: (a) => (
      <Mono className="block max-w-[260px] truncate">
        {a.fichier}
        <span className="text-subtle">:{a.ligne}</span>
      </Mono>
    ),
    compare: (a, b) => a.fichier.localeCompare(b.fichier) || a.ligne - b.ligne,
  },
  {
    id: "regle",
    header: "Règle",
    className: "hidden whitespace-nowrap @3xl:table-cell",
    cell: (a) => (
      <Mono className="block max-w-[200px] truncate text-muted-foreground">{a.regle}</Mono>
    ),
    compare: (a, b) => a.regle.localeCompare(b.regle),
  },
  { id: "motif", header: "Motif", className: "w-full min-w-[260px]", cell: (a) => <Motif a={a} /> },
  {
    id: "brut",
    header: "Valeur brute → retenue",
    className: "hidden whitespace-nowrap @5xl:table-cell",
    cell: (a) => (
      <Mono className="block max-w-[280px] truncate text-muted-foreground" title={a.brut}>
        {a.brut || "∅"}
        {a.retenu && <span className="text-foreground"> → {a.retenu}</span>}
      </Mono>
    ),
  },
];
