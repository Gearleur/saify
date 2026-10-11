import { createContext, useContext } from "react";
import type { ApiError } from "@/lib/api";
import type {
  UploadedFile,
  ClientConfig,
  Reconciliation,
  ReconciliationSummary,
  Health,
} from "@/types/api";

export type LoadingState = "startup" | "sample" | "upload" | "read" | null;

export interface ReconciliationContextValue {
  health: Health | null;
  healthError: ApiError | null;
  clientConfig: ClientConfig | null;
  clientConfigError: ApiError | null;
  history: ReconciliationSummary[];
  /** Rapprochement affiché (le dernier ouvert, ou celui choisi dans l'historique). */
  current: Reconciliation | null;
  loading: LoadingState;
  /** Lève une `ApiError` (429, 413, 422…) : à l'appelant de l'afficher. */
  runSample: () => Promise<Reconciliation>;
  upload: (files: UploadedFile[]) => Promise<Reconciliation>;
  openReconciliation: (id: string) => Promise<void>;
  refreshHealth: () => void;
}

export const ReconciliationContext = createContext<ReconciliationContextValue | null>(null);

/** Données partagées par toutes les vues : santé, paramétrage, historique, rapprochement courant. */
export function useReconciliation(): ReconciliationContextValue {
  const ctx = useContext(ReconciliationContext);
  if (!ctx) throw new Error("useReconciliation doit être utilisé sous <ReconciliationProvider>");
  return ctx;
}
