import type { ApiError } from "@/lib/api";
import type { Understanding, QuestionAnswer } from "@/types/api";

export type RunPhase = "understanding" | "computing" | "done" | "error";

/** Une question posée pendant la session, et ce que le flux en a dit au fil de l'eau. */
export interface QuestionRun {
  id: number;
  question: string;
  phase: RunPhase;
  /** Message de l'étape en cours, tel qu'envoyé par l'API. */
  message: string;
  understanding: Understanding | null;
  answer: QuestionAnswer | null;
  error: ApiError | null;
  /** Horodatages navigateur (ms) : début, intention reçue, réponse reçue. */
  t0: number;
  tUnderstanding: number | null;
  tAnswer: number | null;
}
