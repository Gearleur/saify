import { Download } from "lucide-react";
import { FilterMenu } from "@/components/FilterMenu";
import { SearchInput } from "@/components/SearchInput";
import { Button } from "@/components/ui/button";
import { useSlashFocus } from "@/hooks/useSlashFocus";
import type { useSuspensFilters, FilterKey } from "./useSuspensFilters";

const LIBELLES: Record<FilterKey, string> = {
  priorite: "Priorité",
  fonds: "Fonds",
  conservateur: "Conservateur",
  type: "Type",
  statut: "Statut",
};

interface SuspensToolbarProps {
  state: ReturnType<typeof useSuspensFilters>;
  total: number;
  csvUrl: string | null;
}

/** Barre d'outils façon Supabase : recherche, filtres en menus déroulants, effectif, export. */
export function SuspensToolbar({ state, total, csvUrl }: SuspensToolbarProps) {
  const recherche = useSlashFocus<HTMLInputElement>();
  return (
    <div className="flex flex-wrap items-center gap-2 pb-3">
      <SearchInput
        ref={recherche}
        value={state.query}
        onChange={state.setQuery}
        placeholder="Titre, ISIN ou action"
      />
      {(Object.keys(LIBELLES) as FilterKey[]).map((k) => (
        <FilterMenu
          key={k}
          label={LIBELLES[k]}
          options={state.options[k]}
          selected={state.filters[k]}
          onChange={(v) => state.setFilter(k, v)}
          description={k === "statut" ? "Statut partagé avec l'équipe" : undefined}
        />
      ))}
      {state.actifs && (
        <Button variant="ghost" size="sm" onClick={state.reset}>
          Réinitialiser
        </Button>
      )}
      <span className="ml-auto text-xs text-muted-foreground">
        {state.filtered.length === total
          ? `${total} suspens`
          : `${state.filtered.length} sur ${total} suspens`}
      </span>
      {csvUrl && (
        <Button variant="outline" size="sm" asChild>
          <a href={csvUrl} download>
            <Download />
            Exporter CSV
          </a>
        </Button>
      )}
    </div>
  );
}
