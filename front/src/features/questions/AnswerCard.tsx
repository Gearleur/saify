import type { ReactNode } from "react";
import { StatusLabel } from "@/components/StatusDot";
import type { ReponseQuestion } from "@/types/api";
import { AnswerFigures } from "./AnswerFigures";
import { AnswerNotices } from "./AnswerNotices";
import { AttentionState } from "./AttentionState";
import { isAttention } from "./catalogue";
import { SourceRowsTable } from "./SourceRowsTable";
import { SqlDisclosure } from "./SqlDisclosure";
import { TraceLine } from "./TraceLine";

function Bloc({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="border-t border-border px-5 py-4">
      {title && <h3 className="pb-2 text-xs font-medium text-muted-foreground">{title}</h3>}
      {children}
    </div>
  );
}

/** La réponse : phrase, chiffres, vigilances, preuves (lignes sources, SQL) et traçabilité. */
export function AnswerCard({
  reponse,
  onAsk,
}: {
  reponse: ReponseQuestion;
  onAsk: (q: string) => void;
}) {
  const attention = isAttention(reponse);
  return (
    <article className="rounded-lg border border-border bg-background animate-fade-in">
      <div className="space-y-5 px-5 py-5">
        {attention ? (
          <AttentionState reponse={reponse} onAsk={onAsk} />
        ) : (
          <>
            <div className="flex items-start justify-between gap-6">
              <p className="max-w-[68ch] text-[15px] leading-6">{reponse.reponse}</p>
              <StatusLabel
                tone={reponse.confiance === "haute" ? "green" : "amber"}
                className="shrink-0 text-xs text-muted-foreground"
              >
                {reponse.confiance === "haute"
                  ? "Confiance haute"
                  : "Confiance basse, à faire valider"}
              </StatusLabel>
            </div>
            <AnswerFigures chiffres={reponse.chiffres} />
            <AnswerNotices
              vigilances={reponse.vigilances}
              avertissements={reponse.avertissements}
            />
          </>
        )}
      </div>
      {reponse.lignes_sources.length > 0 && (
        <Bloc title={`Lignes sources (${reponse.lignes_sources.length})`}>
          <SourceRowsTable lignes={reponse.lignes_sources} />
        </Bloc>
      )}
      {reponse.requete_sql && (
        <Bloc>
          <SqlDisclosure sql={reponse.requete_sql} parametres={reponse.parametres_sql} />
        </Bloc>
      )}
      <div className="rounded-b-lg border-t border-border bg-surface px-5 py-2.5">
        <TraceLine c={reponse.comprehension} />
      </div>
    </article>
  );
}
