import { createContext, useContext } from "react";
import type { ApiError } from "@/lib/api";
import type {
  FichierEnvoye,
  Parametrage,
  Rapprochement,
  RapprochementResume,
  Sante,
} from "@/types/api";

export type Chargement = "demarrage" | "exemple" | "envoi" | "lecture" | null;

export interface ReconciliationContextValue {
  sante: Sante | null;
  santeError: ApiError | null;
  parametrage: Parametrage | null;
  parametrageError: ApiError | null;
  historique: RapprochementResume[];
  /** Rapprochement affiché (le dernier ouvert, ou celui choisi dans l'historique). */
  courant: Rapprochement | null;
  chargement: Chargement;
  /** Lève une `ApiError` (429, 413, 422…) : à l'appelant de l'afficher. */
  lancerExemple: () => Promise<Rapprochement>;
  envoyer: (fichiers: FichierEnvoye[]) => Promise<Rapprochement>;
  ouvrir: (id: string) => Promise<void>;
  rafraichirSante: () => void;
}

export const ReconciliationContext = createContext<ReconciliationContextValue | null>(null);

/** Données partagées par toutes les vues : santé, paramétrage, historique, rapprochement courant. */
export function useReconciliation(): ReconciliationContextValue {
  const ctx = useContext(ReconciliationContext);
  if (!ctx) throw new Error("useReconciliation doit être utilisé sous <ReconciliationProvider>");
  return ctx;
}
