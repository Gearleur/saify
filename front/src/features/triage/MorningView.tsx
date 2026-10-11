import { PageHeader } from "@/components/PageHeader";
import { Section } from "@/components/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { DailyFiles } from "@/features/files/DailyFiles";
import { RunExampleButton } from "@/features/files/RunExampleButton";
import { useBreakColumns } from "@/features/breaks/useBreakColumns";
import { useReconciliation } from "@/hooks/useReconciliation";
import { BlockingBanner } from "./BlockingBanner";
import { MorningSubtitle } from "./MorningSubtitle";
import { OffQueueAnomalies } from "./OffQueueAnomalies";
import { SummaryKpis } from "./SummaryKpis";
import { TriageQueue } from "./TriageQueue";
import { useTriage } from "./useTriage";

/** La matinée de l'opérateur, dans l'ordre du geste : blocage, fichiers, synthèse, file, anomalies. */
export function MorningView() {
  const { current, loading } = useReconciliation();
  const triage = useTriage(current);
  const columns = useBreakColumns("triage");
  const ok = current?.status === "OK";

  return (
    <div className="space-y-7">
      <PageHeader
        title="Aujourd'hui"
        description={<MorningSubtitle />}
        actions={<RunExampleButton variant={current ? "outline" : "default"} />}
      />
      {triage.blockers.length > 0 && (
        <BlockingBanner key={current?.id} blockers={triage.blockers} />
      )}
      <DailyFiles />
      {!current && loading !== "startup" && (
        <Section title="File de traitement">
          <p className="border-y border-border py-3 pl-1 text-sm text-muted-foreground">
            La file apparaîtra ici, groupée par priorité, dès que les 4 fichiers seront rapprochés.
          </p>
        </Section>
      )}
      {loading === "startup" ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        current &&
        ok && (
          <>
            <SummaryKpis summary={current.summary} treated={triage.treated} />
            <Section title="File de traitement" count={triage.total}>
              <TriageQueue groups={triage.groups} ids={triage.ids} columns={columns} />
            </Section>
          </>
        )
      )}
      {current && <OffQueueAnomalies items={triage.offQueue} />}
    </div>
  );
}
