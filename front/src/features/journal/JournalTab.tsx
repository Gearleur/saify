import { DataTable } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { FilterMenu } from "@/components/FilterMenu";
import { SearchInput } from "@/components/SearchInput";
import { useSlashFocus } from "@/hooks/useSlashFocus";
import { useSort } from "@/hooks/useSort";
import type { Anomalie } from "@/types/api";
import { anomalieId, JOURNAL_COLUMNS } from "./journalColumns";
import { useJournalFilters } from "./useJournalFilters";

export function JournalTab({ journal }: { journal: Anomalie[] }) {
  const f = useJournalFilters(journal);
  const { sort, toggle, sorted } = useSort(f.filtered, JOURNAL_COLUMNS);
  const recherche = useSlashFocus<HTMLInputElement>();
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 pb-3">
        <SearchInput
          ref={recherche}
          value={f.query}
          onChange={f.setQuery}
          placeholder="Fichier, règle, valeur"
        />
        <FilterMenu
          label="Niveau"
          options={f.options}
          selected={f.niveaux}
          onChange={f.setNiveaux}
        />
        <span className="ml-auto text-xs text-muted-foreground">
          {f.filtered.length} sur {journal.length} lignes
          {f.normalisationsMasquees > 0 && `, ${f.normalisationsMasquees} normalisations masquées`}
        </span>
      </div>
      <DataTable
        label="Journal de nettoyage"
        rows={sorted}
        columns={JOURNAL_COLUMNS}
        getRowId={anomalieId}
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
