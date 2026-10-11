import type { DotTone } from "@/lib/domain";
import { isAttention } from "./catalogue";
import type { QuestionRun } from "./types";

/** Point d'une question de l'historique : vert si chiffrée, ambre si « Attention » ou erreur, gris en cours. */
export function runTone(r: QuestionRun): DotTone {
  if (r.phase === "error") return "amber";
  if (!r.answer) return "gray";
  return isAttention(r.answer) ? "amber" : "green";
}
