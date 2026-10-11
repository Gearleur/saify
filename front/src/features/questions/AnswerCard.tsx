import type { ReactNode } from "react";
import { StatusLabel } from "@/components/StatusDot";
import type { QuestionAnswer } from "@/types/api";
import { AnswerFigures } from "./AnswerFigures";
import { AnswerNotices } from "./AnswerNotices";
import { AttentionState } from "./AttentionState";
import { isAttention } from "./catalogue";
import { SourceRowsTable } from "./SourceRowsTable";
import { SqlDisclosure } from "./SqlDisclosure";
import { TraceLine } from "./TraceLine";

function Block({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="border-t border-border px-4 py-3.5">
      {title && <h3 className="pb-2 text-xs font-medium text-muted-foreground">{title}</h3>}
      {children}
    </div>
  );
}

/** La réponse : phrase, chiffres, vigilances, preuves (lignes sources, SQL) et traçabilité. */
export function AnswerCard({
  answer,
  onAsk,
}: {
  answer: QuestionAnswer;
  onAsk: (q: string) => void;
}) {
  const attention = isAttention(answer);
  return (
    <article className="rounded-lg border border-border bg-background animate-fade-in">
      <div className="space-y-4 px-4 py-4">
        {attention ? (
          <AttentionState answer={answer} onAsk={onAsk} />
        ) : (
          <>
            <div className="flex items-start justify-between gap-6">
              <p className="max-w-[68ch] text-base">{answer.answer}</p>
              <StatusLabel
                tone={answer.confidence === "haute" ? "green" : "amber"}
                className="shrink-0 text-xs text-muted-foreground"
              >
                {answer.confidence === "haute"
                  ? "Confiance haute"
                  : "Confiance basse, à faire valider"}
              </StatusLabel>
            </div>
            <AnswerFigures figures={answer.figures} />
            <AnswerNotices vigilances={answer.vigilances} warnings={answer.warnings} />
          </>
        )}
      </div>
      {answer.source_rows.length > 0 && (
        <Block title={`Lignes sources (${answer.source_rows.length})`}>
          <SourceRowsTable lines={answer.source_rows} />
        </Block>
      )}
      {answer.sql_query && (
        <Block>
          <SqlDisclosure sql={answer.sql_query} params={answer.sql_params} />
        </Block>
      )}
      <div className="rounded-b-lg border-t border-border bg-surface px-4 py-2">
        <TraceLine c={answer.understanding} />
      </div>
    </article>
  );
}
