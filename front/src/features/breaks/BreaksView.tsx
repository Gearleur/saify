import { DataTable } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useListNavigation } from "@/hooks/useListNavigation";
import { useReconciliation } from "@/hooks/useReconciliation";
import { useSort } from "@/hooks/useSort";
import { reconciliationsApi } from "@/lib/api";
import { reconciliationLabel } from "@/lib/dates";
import { NoReconciliation } from "@/features/files/NoReconciliation";
import { useWorkStatuses } from "./workStatuses";
import { BreakToolbar } from "./BreakToolbar";
import { useBreakColumns } from "./useBreakColumns";
import { useBreakFilters } from "./useBreakFilters";
import { useBreakSheet } from "./useBreakSheet";

/** Analyse : tous les suspens, triables et filtrables. */
export function BreaksView() {
  const { current } = useReconciliation();
  const { route, navigate } = useHashRoute();
  const { get } = useWorkStatuses(current);
  const columns = useBreakColumns("analyse");
  const state = useBreakFilters(current?.breaks ?? [], get, route.params);
  const { sort, toggle, sorted } = useSort(state.filtered, columns);
  const sheet = useBreakSheet();
  const ids = sorted.map((s) => s.id);
  const openReconciliation = (id: string) => sheet.open(id, ids);
  const { cursorId } = useListNavigation({ ids, openId: sheet.openId, onOpen: openReconciliation });

  if (!current) return <NoReconciliation what="les suspens" />;
  const blocked = current.status === "BLOQUE";

  return (
    <>
      <PageHeader
        title="Suspens"
        description={`${reconciliationLabel(current.as_of_date)}, trié par priorité. ↑ ↓ pour parcourir, Entrée pour ouvrir.`}
      />
      {blocked ? (
        <EmptyState
          title="Rapprochement bloqué : aucun suspens calculé"
          description="Un fichier est refusé. Corrigez-le puis relancez le rapprochement."
          action={
            <Button variant="outline" onClick={() => navigate("a-traiter")}>
              Voir le blocage
            </Button>
          }
        />
      ) : (
        <>
          <BreakToolbar
            state={state}
            total={current.breaks.length}
            csvUrl={reconciliationsApi.csvUrl(current.id)}
          />
          <DataTable
            label="Suspens"
            rows={sorted}
            columns={columns}
            getRowId={(s) => s.id}
            onRowClick={(s) => openReconciliation(s.id)}
            activeId={sheet.openId}
            cursorId={cursorId}
            sort={sort}
            onSort={toggle}
            empty={
              <EmptyState
                title="Aucun suspens ne correspond"
                description="Élargissez la recherche ou retirez un filtre."
                action={
                  <Button variant="outline" onClick={state.reset}>
                    Réinitialiser
                  </Button>
                }
              />
            }
          />
        </>
      )}
    </>
  );
}
