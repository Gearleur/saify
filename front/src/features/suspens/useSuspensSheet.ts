import { createContext, useContext } from "react";

export interface SuspensSheetValue {
  openId: string | null;
  /** Ordre de la liste d'où la fiche a été ouverte (pour précédent / suivant). */
  sequence: string[];
  open: (id: string, sequence?: string[]) => void;
  close: () => void;
}

export const SuspensSheetContext = createContext<SuspensSheetValue | null>(null);

/** Fiche de détail ouverte à droite (un suspens à la fois). */
export function useSuspensSheet(): SuspensSheetValue {
  const ctx = useContext(SuspensSheetContext);
  if (!ctx) throw new Error("useSuspensSheet doit être utilisé sous <SuspensSheetProvider>");
  return ctx;
}
