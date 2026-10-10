import { PageHeader } from "@/components/PageHeader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { NoReconciliation } from "@/features/files/NoReconciliation";
import { ReceivedFilesTable } from "@/features/files/ReceivedFilesTable";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { arreteLabel } from "@/lib/dates";
import { JournalTab } from "./JournalTab";

/** Audit : pourquoi une valeur a changé, quel fichier a été rapproché. */
export function JournalView() {
  const { courant } = useReconciliation();
  const { route, navigate } = useHashRoute();
  if (!courant) return <NoReconciliation what="le journal de nettoyage" />;
  const onglet = route.params.get("onglet") === "fichiers" ? "fichiers" : "journal";

  return (
    <>
      <PageHeader
        title="Journal et fichiers"
        description={`Chaque transformation des fichiers reçus (${arreteLabel(courant.date_arrete).toLowerCase()}), et la preuve des fichiers rapprochés.`}
      />
      <Tabs
        value={onglet}
        onValueChange={(v) => navigate("journal", v === "fichiers" ? { onglet: v } : undefined)}
      >
        <TabsList>
          <TabsTrigger value="journal">Journal de nettoyage</TabsTrigger>
          <TabsTrigger value="fichiers">Fichiers reçus</TabsTrigger>
        </TabsList>
        <TabsContent value="journal">
          <JournalTab journal={courant.journal} />
        </TabsContent>
        <TabsContent value="fichiers">
          <ReceivedFilesTable rapprochement={courant} />
        </TabsContent>
      </Tabs>
    </>
  );
}
