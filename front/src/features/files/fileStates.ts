import { SOURCES_ATTENDUES, sourceOf, type SourceAttendue } from "@/lib/files";
import type { Anomalie, FichierRecu, Rapprochement } from "@/types/api";

export type ReceivedState = "accepte" | "refuse" | "absent";

export interface ReceivedSlot {
  attendu: SourceAttendue;
  fichier: FichierRecu | null;
  etat: ReceivedState;
  /** BLOQUANT qui refuse ce fichier (le contrat n'a pas d'état par fichier : déduit du journal). */
  blocage: Anomalie | null;
}

/** Les 4 sources attendues et ce qu'en dit le dernier rapprochement. */
export function receivedSlots(r: Rapprochement | null): ReceivedSlot[] {
  return SOURCES_ATTENDUES.map((attendu) => {
    const fichier =
      r?.fichiers.find((f) => (sourceOf(f.nom) ?? f.source) === attendu.source) ?? null;
    const blocage =
      r?.journal.find((a) => a.niveau === "BLOQUANT" && sourceOf(a.fichier) === attendu.source) ??
      null;
    const etat: ReceivedState = blocage ? "refuse" : fichier ? "accepte" : "absent";
    return { attendu, fichier, etat, blocage };
  });
}
