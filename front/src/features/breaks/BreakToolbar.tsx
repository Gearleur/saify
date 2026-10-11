import { Download } from "lucide-react";
import { FilterMenu } from "@/components/FilterMenu";
import { SearchInput } from "@/components/SearchInput";
import { Button } from "@/components/ui/button";
import { useSlashFocus } from "@/hooks/useSlashFocus";
import type { useBreakFilters, FilterKey } from "./useBreakFilters";

const LABELS: Record<FilterKey, string> = {
  priority: "Priorité",
  fund: "Fonds",
  custodian: "Conservateur",
  type: "Type",
  status: "Statut",
};

interface BreakToolbarProps {
  state: ReturnType<typeof useBreakFilters>;
  total: number;
  csvUrl: string | null;
}

/** Barre d'outils façon Supabase : recherche, filtres en menus déroulants, effectif, export. */
export function BreakToolbar({ state, total, csvUrl }: BreakToolbarProps) {
  const search = useSlashFocus<HTMLInputElement>();
  return (
    <div className="flex flex-wrap items-center gap-2 pb-3">
      <SearchInput
        ref={search}
        value={state.query}
        onChange={state.setQuery}
        placeholder="Titre, ISIN ou action"
      />
      {(Object.keys(LABELS) as FilterKey[]).map((k) => (
        <FilterMenu
          key={k}
          label={LABELS[k]}
          options={state.options[k]}
          selected={state.filters[k]}
          onChange={(v) => state.setFilter(k, v)}
          description={k === "status" ? "Statut partagé avec l'équipe" : undefined}
        />
      ))}
      {state.active && (
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
