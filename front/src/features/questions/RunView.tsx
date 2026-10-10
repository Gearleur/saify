import { ErrorNotice } from "@/components/ErrorNotice";
import { AnswerCard } from "./AnswerCard";
import { StreamSteps } from "./StreamSteps";
import type { QuestionRun } from "./types";

/** Une question de la session : les étapes du flux, puis la réponse (ou l'erreur). */
export function RunView({ run, onAsk }: { run: QuestionRun; onAsk: (q: string) => void }) {
  return (
    <div className="space-y-4">
      <h2 className="text-heading">{run.question}</h2>
      <StreamSteps run={run} />
      {run.error && <ErrorNotice key={run.error.at} error={run.error} />}
      {run.reponse && <AnswerCard reponse={run.reponse} onAsk={onAsk} />}
    </div>
  );
}
