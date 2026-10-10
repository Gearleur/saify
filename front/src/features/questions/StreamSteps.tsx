import { Check, Circle, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { describeIntent, formatConfidence, formatDuration, sourceLabel } from "./catalogue";
import type { QuestionRun } from "./types";

type StepState = "fait" | "actif" | "attente";

function Step({ state, title, detail }: { state: StepState; title: string; detail?: ReactNode }) {
  return (
    <li className="flex gap-2.5">
      <span className="mt-[3px] flex size-4 shrink-0 items-center justify-center">
        {state === "fait" && <Check className="size-3.5 text-dot-green" strokeWidth={2.5} />}
        {state === "actif" && <Loader2 className="size-3.5 animate-spin text-muted-foreground" />}
        {state === "attente" && <Circle className="size-2.5 text-border-strong" />}
      </span>
      <div className={cn("min-w-0 text-sm", state === "attente" && "text-subtle")}>
        <p className={cn(state === "actif" && "font-medium")}>{title}</p>
        {detail && <p className="text-xs text-muted-foreground animate-fade-in">{detail}</p>}
      </div>
    </li>
  );
}

/** Les étapes du flux, au fil de l'eau : analyse, intention comprise, requête, réponse. */
export function StreamSteps({ run }: { run: QuestionRun }) {
  const { comprehension: c, phase, t0, tComprehension, tReponse } = run;
  if (phase === "erreur" && !c) return null;
  if ((phase === "termine" || phase === "erreur") && c) {
    return (
      <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Check className="size-3.5 text-dot-green" strokeWidth={2.5} />
          Comprise par {sourceLabel(c.source)}
          {tComprehension ? ` en ${formatDuration(tComprehension - t0)}` : ""}
        </span>
        {run.reponse && (
          <span className="flex items-center gap-1.5">
            <Check className="size-3.5 text-dot-green" strokeWidth={2.5} />
            Requête en lecture seule
            {tReponse && tComprehension ? ` en ${formatDuration(tReponse - tComprehension)}` : ""}
          </span>
        )}
      </p>
    );
  }
  const analyse: StepState = c ? "fait" : "actif";
  const calcul: StepState = run.reponse ? "fait" : phase === "calcul" ? "actif" : "attente";
  const reponse: StepState = run.reponse ? "fait" : "attente";
  return (
    <ol className="space-y-2.5" aria-live="polite">
      <Step
        state={analyse}
        title={c ? "Question analysée" : "Analyse de la question…"}
        detail={
          c &&
          `${describeIntent(c)}, par ${sourceLabel(c.source)}, confiance ${formatConfidence(c.confiance)}${tComprehension ? `, en ${formatDuration(tComprehension - t0)}` : ""}`
        }
      />
      <Step
        state={calcul}
        title={
          calcul === "fait"
            ? "Requête en lecture seule exécutée"
            : "Requête en lecture seule sur la base de gestion…"
        }
        detail={
          calcul === "fait" && tReponse && tComprehension
            ? `en ${formatDuration(tReponse - tComprehension)}`
            : undefined
        }
      />
      <Step state={reponse} title="Réponse" />
    </ol>
  );
}
