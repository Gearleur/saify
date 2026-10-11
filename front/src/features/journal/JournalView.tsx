import { PageHeader } from "@/components/PageHeader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { NoReconciliation } from "@/features/files/NoReconciliation";
import { ReceivedFilesTable } from "@/features/files/ReceivedFilesTable";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { asOfLabel } from "@/lib/dates";
import { JournalTab } from "./JournalTab";

/** Audit : pourquoi une valeur a changé, quel fichier a été rapproché. */
export function JournalView() {
  const { current } = useReconciliation();
  const { route, navigate } = useHashRoute();
  if (!current) return <NoReconciliation what="le journal de nettoyage" />;
  const tab = route.params.get("onglet") === "fichiers" ? "fichiers" : "journal";

  return (
    <>
      <PageHeader
        title="Journal et fichiers"
        description={`Chaque transformation des fichiers reçus (${asOfLabel(current.as_of_date).toLowerCase()}), et la preuve des fichiers rapprochés.`}
      />
      <Tabs
        value={tab}
        onValueChange={(v) => navigate("journal", v === "fichiers" ? { tab: v } : undefined)}
      >
        <TabsList>
          <TabsTrigger value="journal">Journal de nettoyage</TabsTrigger>
          <TabsTrigger value="fichiers">Fichiers reçus</TabsTrigger>
        </TabsList>
        <TabsContent value="journal">
          <JournalTab cleaning_log={current.cleaning_log} />
        </TabsContent>
        <TabsContent value="fichiers">
          <ReceivedFilesTable reconciliation={current} />
        </TabsContent>
      </Tabs>
    </>
  );
}
