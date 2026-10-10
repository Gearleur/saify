import type { DotTone } from "@/lib/metier";
import { isAttention } from "./catalogue";
import type { QuestionRun } from "./types";

/** Point d'une question de l'historique : vert si chiffrée, ambre si « Attention » ou erreur, gris en cours. */
export function runTone(r: QuestionRun): DotTone {
  if (r.phase === "erreur") return "amber";
  if (!r.reponse) return "gray";
  return isAttention(r.reponse) ? "amber" : "green";
}
