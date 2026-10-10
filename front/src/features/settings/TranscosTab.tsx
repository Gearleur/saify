import { DataTable } from "@/components/DataTable";
import { Section } from "@/components/Section";
import type { Transco } from "@/types/api";
import { TRANSCO_COLUMNS } from "./settingsColumns";

/** Tables de transcodification : clé source (sous-compte, compte, desk) → fonds. */
export function TranscosTab({ transcos }: { transcos: Record<string, Transco[]> }) {
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      {Object.entries(transcos).map(([nom, lignes]) => (
        <Section
          key={nom}
          title={<span className="font-mono text-xs font-medium">{nom}</span>}
          count={lignes.length}
        >
          <DataTable
            label={nom}
            rows={lignes}
            columns={TRANSCO_COLUMNS}
            getRowId={(t) => t.cle}
            empty={<p className="py-3 pl-1 text-sm text-muted-foreground">Table vide.</p>}
          />
        </Section>
      ))}
    </div>
  );
}
