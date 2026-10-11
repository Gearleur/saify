import { DataTable } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { FilterMenu } from "@/components/FilterMenu";
import { SearchInput } from "@/components/SearchInput";
import { useSlashFocus } from "@/hooks/useSlashFocus";
import { useSort } from "@/hooks/useSort";
import type { Anomaly } from "@/types/api";
import { anomalyId, LOG_COLUMNS } from "./journalColumns";
import { useJournalFilters } from "./useJournalFilters";

export function JournalTab({ cleaning_log }: { cleaning_log: Anomaly[] }) {
  const f = useJournalFilters(cleaning_log);
  const { sort, toggle, sorted } = useSort(f.filtered, LOG_COLUMNS);
  const search = useSlashFocus<HTMLInputElement>();
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 pb-3">
        <SearchInput
          ref={search}
          value={f.query}
          onChange={f.setQuery}
          placeholder="Fichier, règle, valeur"
        />
        <FilterMenu label="Niveau" options={f.options} selected={f.levels} onChange={f.setLevels} />
        <span className="ml-auto text-xs text-muted-foreground">
          {f.filtered.length} sur {cleaning_log.length} lignes
          {f.normalizationsHidden > 0 && `, ${f.normalizationsHidden} normalisations masquées`}
        </span>
      </div>
      <DataTable
        label="Journal de nettoyage"
        rows={sorted}
        columns={LOG_COLUMNS}
        getRowId={anomalyId}
        sort={sort}
        onSort={toggle}
        empty={
          <EmptyState
            title="Aucune ligne pour ce filtre"
            description="Ajoutez un niveau dans le menu Niveau."
          />
        }
      />
    </>
  );
}
