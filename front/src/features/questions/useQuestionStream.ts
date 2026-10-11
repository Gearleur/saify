import { useCallback, useRef } from "react";
import { useReconciliation } from "@/hooks/useReconciliation";
import { ApiError, questionsApi } from "@/lib/api";
import { sessionStore, useQuestionSession } from "./sessionStore";

export const QUESTION_MIN = 3;
export const QUESTION_MAX = 500;

let suivant = 0;

/** Pose une question via le flux SSE et range chaque événement dans la session. */
export function useQuestionStream() {
  const { rafraichirSante } = useReconciliation();
  const { selected } = useQuestionSession();
  const enCours = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (brute: string) => {
      const question = brute.trim();
      if (question.length < QUESTION_MIN || question.length > QUESTION_MAX) return;
      enCours.current?.abort();
      const ctrl = new AbortController();
      enCours.current = ctrl;
      const id = ++suivant;
      sessionStore.add({
        id,
        question,
        phase: "comprehension",
        message: "Analyse de la question…",
        comprehension: null,
        reponse: null,
        error: null,
        t0: performance.now(),
        tComprehension: null,
        tReponse: null,
      });
      // Une question doit toujours finir (réponse, erreur ou annulation) : sinon elle reste « en cours »
      // pour toujours dans le rail. Un abandon fait sortir la boucle sans exception, d'où ce suivi.
      let fini = false;
      const terminer = (code: string, message: string) =>
        sessionStore.update(id, { phase: "erreur", error: new ApiError(0, code, message) });
      try {
        for await (const ev of questionsApi.flux(question, ctrl.signal)) {
          if (ev.type === "etape")
            sessionStore.update(id, {
              message: ev.data.message,
              phase: ev.data.etape === "calcul" ? "calcul" : "comprehension",
            });
          else if (ev.type === "comprehension")
            sessionStore.update(id, { comprehension: ev.data, tComprehension: performance.now() });
          else if (ev.type === "reponse") {
            fini = true;
            sessionStore.update(id, {
              reponse: ev.data,
              phase: "termine",
              tReponse: performance.now(),
            });
          } else if (ev.type === "erreur") {
            fini = true;
            sessionStore.update(id, {
              phase: "erreur",
              error: new ApiError(200, ev.data.code, ev.data.message),
            });
          }
        }
        if (!fini && ctrl.signal.aborted)
          terminer("ANNULEE", "Remplacée par la question suivante.");
        else if (!fini) terminer("INCOMPLET", "Le flux s'est interrompu avant la réponse.");
      } catch (e) {
        if (ctrl.signal.aborted) terminer("ANNULEE", "Remplacée par la question suivante.");
        else
          sessionStore.update(id, {
            phase: "erreur",
            error:
              e instanceof ApiError ? e : new ApiError(0, "INCONNU", "Le flux s'est interrompu."),
          });
      } finally {
        if (enCours.current === ctrl) enCours.current = null;
        rafraichirSante();
      }
    },
    [rafraichirSante],
  );

  const busy = selected?.phase === "comprehension" || selected?.phase === "calcul";
  return { ask, busy };
}
