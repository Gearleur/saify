import { PageHeader } from "@/components/PageHeader";
import { Section } from "@/components/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { DailyFiles } from "@/features/files/DailyFiles";
import { RunExampleButton } from "@/features/files/RunExampleButton";
import { useSuspensColumns } from "@/features/suspens/useSuspensColumns";
import { useReconciliation } from "@/hooks/useReconciliation";
import { BlockingBanner } from "./BlockingBanner";
import { MorningSubtitle } from "./MorningSubtitle";
import { OffQueueAnomalies } from "./OffQueueAnomalies";
import { SummaryKpis } from "./SummaryKpis";
import { TriageQueue } from "./TriageQueue";
import { useTriage } from "./useTriage";

/** La matinée de l'opérateur, dans l'ordre du geste : blocage, fichiers, synthèse, file, anomalies. */
export function MorningView() {
  const { courant, chargement } = useReconciliation();
  const triage = useTriage(courant);
  const columns = useSuspensColumns("triage");
  const ok = courant?.statut === "OK";

  return (
    <div className="space-y-7">
      <PageHeader
        title="Aujourd'hui"
        description={<MorningSubtitle />}
        actions={<RunExampleButton variant={courant ? "outline" : "default"} />}
      />
      {triage.blocages.length > 0 && (
        <BlockingBanner key={courant?.id} blocages={triage.blocages} />
      )}
      <DailyFiles />
      {!courant && chargement !== "demarrage" && (
        <Section title="File de traitement">
          <p className="border-y border-border py-3 pl-1 text-sm text-muted-foreground">
            La file apparaîtra ici, groupée par priorité, dès que les 4 fichiers seront rapprochés.
          </p>
        </Section>
      )}
      {chargement === "demarrage" ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        courant &&
        ok && (
          <>
            <SummaryKpis synthese={courant.synthese} traites={triage.traites} />
            <Section title="File de traitement" count={triage.total}>
              <TriageQueue groups={triage.groups} ids={triage.ids} columns={columns} />
            </Section>
          </>
        )
      )}
      {courant && <OffQueueAnomalies items={triage.horsSuspens} />}
    </div>
  );
}
