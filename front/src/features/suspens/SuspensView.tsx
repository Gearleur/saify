import { DataTable } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useListNavigation } from "@/hooks/useListNavigation";
import { useReconciliation } from "@/hooks/useReconciliation";
import { useSort } from "@/hooks/useSort";
import { rapprochementsApi } from "@/lib/api";
import { rapprochementLabel } from "@/lib/dates";
import { NoReconciliation } from "@/features/files/NoReconciliation";
import { useLocalStatus } from "./localStatus";
import { SuspensToolbar } from "./SuspensToolbar";
import { useSuspensColumns } from "./useSuspensColumns";
import { useSuspensFilters } from "./useSuspensFilters";
import { useSuspensSheet } from "./useSuspensSheet";

/** Analyse : tous les suspens, triables et filtrables. */
export function SuspensView() {
  const { courant } = useReconciliation();
  const { route, navigate } = useHashRoute();
  const { get } = useLocalStatus(courant?.date_arrete ?? null);
  const columns = useSuspensColumns("analyse");
  const state = useSuspensFilters(courant?.suspens ?? [], get, route.params);
  const { sort, toggle, sorted } = useSort(state.filtered, columns);
  const sheet = useSuspensSheet();
  const ids = sorted.map((s) => s.id);
  const ouvrir = (id: string) => sheet.open(id, ids);
  const { cursorId } = useListNavigation({ ids, openId: sheet.openId, onOpen: ouvrir });

  if (!courant) return <NoReconciliation what="les suspens" />;
  const bloque = courant.statut === "BLOQUE";

  return (
    <>
      <PageHeader
        title="Suspens"
        description={`${rapprochementLabel(courant.date_arrete)}, trié par priorité. ↑ ↓ pour parcourir, Entrée pour ouvrir.`}
      />
      {bloque ? (
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
          <SuspensToolbar
            state={state}
            total={courant.suspens.length}
            csvUrl={rapprochementsApi.csvUrl(courant.id)}
          />
          <DataTable
            label="Suspens"
            rows={sorted}
            columns={columns}
            getRowId={(s) => s.id}
            onRowClick={(s) => ouvrir(s.id)}
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
