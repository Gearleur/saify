import { EXPECTED_SOURCES, sourceOf, type ExpectedSource } from "@/lib/files";
import type { Anomaly, ReceivedFile, Reconciliation } from "@/types/api";

export type ReceivedState = "accepted" | "rejected" | "absent";

export interface ReceivedSlot {
  expected: ExpectedSource;
  file: ReceivedFile | null;
  state: ReceivedState;
  /** BLOQUANT qui refuse ce fichier (le contrat n'a pas d'état par fichier : déduit du journal). */
  blocking: Anomaly | null;
}

/** Les 4 sources attendues et ce qu'en dit le dernier rapprochement. */
export function receivedSlots(r: Reconciliation | null): ReceivedSlot[] {
  return EXPECTED_SOURCES.map((expected) => {
    const file = r?.files.find((f) => (sourceOf(f.name) ?? f.source) === expected.source) ?? null;
    const blocking =
      r?.cleaning_log.find((a) => a.level === "BLOQUANT" && sourceOf(a.file) === expected.source) ??
      null;
    const state: ReceivedState = blocking ? "rejected" : file ? "accepted" : "absent";
    return { expected, file, state, blocking };
  });
}
