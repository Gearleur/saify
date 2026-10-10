import type { ApiError } from "@/lib/api";
import type { Comprehension, ReponseQuestion } from "@/types/api";

export type RunPhase = "comprehension" | "calcul" | "termine" | "erreur";

/** Une question posée pendant la session, et ce que le flux en a dit au fil de l'eau. */
export interface QuestionRun {
  id: number;
  question: string;
  phase: RunPhase;
  /** Message de l'étape en cours, tel qu'envoyé par l'API. */
  message: string;
  comprehension: Comprehension | null;
  reponse: ReponseQuestion | null;
  error: ApiError | null;
  /** Horodatages navigateur (ms) : début, intention reçue, réponse reçue. */
  t0: number;
  tComprehension: number | null;
  tReponse: number | null;
}
