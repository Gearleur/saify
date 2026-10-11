import { Check, Circle, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { describeIntent, formatConfidence, formatDuration, sourceLabel } from "./catalogue";
import type { QuestionRun } from "./types";

type StepState = "done" | "active" | "waiting";

function Step({ state, title, detail }: { state: StepState; title: string; detail?: ReactNode }) {
  return (
    <li className="flex gap-2.5">
      <span className="mt-[3px] flex size-4 shrink-0 items-center justify-center">
        {state === "done" && <Check className="size-3.5 text-dot-green" strokeWidth={2.5} />}
        {state === "active" && <Loader2 className="size-3.5 animate-spin text-muted-foreground" />}
        {state === "waiting" && <Circle className="size-2.5 text-border-strong" />}
      </span>
      <div className={cn("min-w-0 text-sm", state === "waiting" && "text-subtle")}>
        <p className={cn(state === "active" && "font-medium")}>{title}</p>
        {detail && <p className="text-xs text-muted-foreground animate-fade-in">{detail}</p>}
      </div>
    </li>
  );
}

/** Les étapes du flux, au fil de l'eau : analyse, intention comprise, requête, réponse. */
export function StreamSteps({ run }: { run: QuestionRun }) {
  const { understanding: c, phase, t0, tUnderstanding, tAnswer } = run;
  if (phase === "error" && !c) return null;
  if ((phase === "done" || phase === "error") && c) {
    return (
      <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Check className="size-3.5 text-dot-green" strokeWidth={2.5} />
          Comprise par {sourceLabel(c.source)}
          {tUnderstanding ? ` en ${formatDuration(tUnderstanding - t0)}` : ""}
        </span>
        {run.answer && (
          <span className="flex items-center gap-1.5">
            <Check className="size-3.5 text-dot-green" strokeWidth={2.5} />
            Requête en lecture seule
            {tAnswer && tUnderstanding ? ` en ${formatDuration(tAnswer - tUnderstanding)}` : ""}
          </span>
        )}
      </p>
    );
  }
  const analyse: StepState = c ? "done" : "active";
  const computeState: StepState = run.answer
    ? "done"
    : phase === "computing"
      ? "active"
      : "waiting";
  const answer: StepState = run.answer ? "done" : "waiting";
  return (
    <ol className="space-y-2.5" aria-live="polite">
      <Step
        state={analyse}
        title={c ? "Question analysée" : "Analyse de la question…"}
        detail={
          c &&
          `${describeIntent(c)}, par ${sourceLabel(c.source)}, confiance ${formatConfidence(c.confidence)}${tUnderstanding ? `, en ${formatDuration(tUnderstanding - t0)}` : ""}`
        }
      />
      <Step
        state={computeState}
        title={
          computeState === "done"
            ? "Requête en lecture seule exécutée"
            : "Requête en lecture seule sur la base de gestion…"
        }
        detail={
          computeState === "done" && tAnswer && tUnderstanding
            ? `en ${formatDuration(tAnswer - tUnderstanding)}`
            : undefined
        }
      />
      <Step state={answer} title="Réponse" />
    </ol>
  );
}
