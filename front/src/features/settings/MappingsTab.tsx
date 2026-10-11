import { DataTable } from "@/components/DataTable";
import { Section } from "@/components/Section";
import type { Mapping } from "@/types/api";
import { MAPPING_COLUMNS } from "./settingsColumns";

/** Tables de transcodification : clé source (sous-compte, compte, desk) → fonds. */
export function MappingsTab({ mappings }: { mappings: Record<string, Mapping[]> }) {
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      {Object.entries(mappings).map(([name, lines]) => (
        <Section
          key={name}
          title={<span className="font-mono text-xs font-medium">{name}</span>}
          count={lines.length}
        >
          <DataTable
            label={name}
            rows={lines}
            columns={MAPPING_COLUMNS}
            getRowId={(t) => t.key}
            empty={<p className="py-3 pl-1 text-sm text-muted-foreground">Table vide.</p>}
          />
        </Section>
      ))}
    </div>
  );
}
