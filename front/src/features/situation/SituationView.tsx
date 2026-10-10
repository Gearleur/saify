import { Copy, Download } from "lucide-react";
import { ErrorNotice } from "@/components/ErrorNotice";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { NoReconciliation } from "@/features/files/NoReconciliation";
import { useReconciliation } from "@/hooks/useReconciliation";
import { rapprochementsApi } from "@/lib/api";
import { rapprochementLabel } from "@/lib/dates";
import { SituationAside } from "./SituationAside";
import { useCopy } from "@/hooks/useCopy";
import { usePointDeSituation } from "./usePointDeSituation";

/** Le point de situation pour le responsable : le texte du back tel quel, prêt à coller. */
export function SituationView() {
  const { courant } = useReconciliation();
  const { texte, error, loading } = usePointDeSituation(courant?.id ?? null);
  const copier = useCopy();
  if (!courant) return <NoReconciliation what="le point de situation" />;

  return (
    <>
      <PageHeader
        title="Point de situation"
        description={`${rapprochementLabel(courant.date_arrete)}, texte figé à sa création, prêt à coller dans un mail.`}
        actions={
          <>
            <Button variant="outline" asChild>
              <a href={rapprochementsApi.csvUrl(courant.id)} download>
                <Download />
                Exporter CSV
              </a>
            </Button>
            <Button onClick={() => texte && copier(texte, "Point de situation")} disabled={!texte}>
              <Copy />
              Copier le texte
            </Button>
          </>
        }
      />
      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_340px]">
        <article className="min-w-0 rounded-lg border border-border">
          <div className="border-b border-border px-5 py-2.5 text-xs text-muted-foreground">
            Aperçu du message
          </div>
          {loading && (
            <div className="space-y-2 p-5">
              {["w-4/5", "w-2/3", "w-3/4", "w-1/2", "w-2/3"].map((w, i) => (
                <Skeleton key={i} className={`h-3.5 ${w}`} />
              ))}
            </div>
          )}
          {error && <ErrorNotice error={error} className="m-5" />}
          {texte && (
            <pre className="max-w-[80ch] whitespace-pre-wrap px-5 py-4 font-sans text-sm leading-6">
              {texte}
            </pre>
          )}
        </article>
        <SituationAside r={courant} />
      </div>
    </>
  );
}
