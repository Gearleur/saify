import { DataTable } from "@/components/DataTable";
import { Section } from "@/components/Section";
import { Button } from "@/components/ui/button";
import { anomalyId, LOG_COLUMNS } from "@/features/journal/journalColumns";
import { useHashRoute } from "@/hooks/useHashRoute";
import type { Anomaly } from "@/types/api";

/** Écarté ou signalé au nettoyage : les seules lignes du journal qui méritent l'œil de l'opérateur. */
export function OffQueueAnomalies({ items }: { items: Anomaly[] }) {
  const { navigate } = useHashRoute();
  return (
    <Section
      title="Écarté ou signalé au nettoyage"
      count={items.length}
      aside={
        <Button variant="ghost" size="sm" onClick={() => navigate("journal")}>
          Journal complet
        </Button>
      }
    >
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Aucune ligne exclue ni signalée.</p>
      ) : (
        <DataTable
          label="Anomalies hors suspens"
          rows={items}
          columns={LOG_COLUMNS}
          getRowId={anomalyId}
        />
      )}
    </Section>
  );
}
