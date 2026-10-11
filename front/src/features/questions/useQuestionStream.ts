import { useCallback, useRef } from "react";
import { useReconciliation } from "@/hooks/useReconciliation";
import { ApiError, questionsApi } from "@/lib/api";
import { sessionStore, useQuestionSession } from "./sessionStore";

export const QUESTION_MIN = 3;
export const QUESTION_MAX = 500;

let next = 0;

/** Pose une question via le flux SSE et range chaque événement dans la session. */
export function useQuestionStream() {
  const { refreshHealth } = useReconciliation();
  const { selected } = useQuestionSession();
  const inFlight = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (rawText: string) => {
      const question = rawText.trim();
      if (question.length < QUESTION_MIN || question.length > QUESTION_MAX) return;
      inFlight.current?.abort();
      const ctrl = new AbortController();
      inFlight.current = ctrl;
      const id = ++next;
      sessionStore.add({
        id,
        question,
        phase: "understanding",
        message: "Analyse de la question…",
        understanding: null,
        answer: null,
        error: null,
        t0: performance.now(),
        tUnderstanding: null,
        tAnswer: null,
      });
      // Une question doit toujours finir (réponse, erreur ou annulation) : sinon elle reste « en cours »
      // pour toujours dans le rail. Un abandon fait sortir la boucle sans exception, d'où ce suivi.
      let finished = false;
      const finish = (code: string, message: string) =>
        sessionStore.update(id, { phase: "error", error: new ApiError(0, code, message) });
      try {
        for await (const ev of questionsApi.stream(question, ctrl.signal)) {
          if (ev.type === "step")
            sessionStore.update(id, {
              message: ev.data.message,
              phase: ev.data.step === "computing" ? "computing" : "understanding",
            });
          else if (ev.type === "understanding")
            sessionStore.update(id, { understanding: ev.data, tUnderstanding: performance.now() });
          else if (ev.type === "answer") {
            finished = true;
            sessionStore.update(id, {
              answer: ev.data,
              phase: "done",
              tAnswer: performance.now(),
            });
          } else if (ev.type === "error") {
            finished = true;
            sessionStore.update(id, {
              phase: "error",
              error: new ApiError(200, ev.data.code, ev.data.message),
            });
          }
        }
        if (!finished && ctrl.signal.aborted)
          finish("ANNULEE", "Remplacée par la question suivante.");
        else if (!finished) finish("INCOMPLET", "Le flux s'est interrompu avant la réponse.");
      } catch (e) {
        if (ctrl.signal.aborted) finish("ANNULEE", "Remplacée par la question suivante.");
        else
          sessionStore.update(id, {
            phase: "error",
            error:
              e instanceof ApiError ? e : new ApiError(0, "INCONNU", "Le flux s'est interrompu."),
          });
      } finally {
        if (inFlight.current === ctrl) inFlight.current = null;
        refreshHealth();
      }
    },
    [refreshHealth],
  );

  const busy = selected?.phase === "understanding" || selected?.phase === "computing";
  return { ask, busy };
}
