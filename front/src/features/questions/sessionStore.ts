import { useSyncExternalStore } from "react";
import type { QuestionRun } from "./types";

/** Historique des questions de la session (mémoire de l'onglet, perdu au rechargement, comme une session). */
let runs: QuestionRun[] = [];
let selectedId: number | null = null;
const abonnes = new Set<() => void>();
let instantane: { runs: QuestionRun[]; selectedId: number | null } = { runs, selectedId };

function emettre() {
  instantane = { runs, selectedId };
  abonnes.forEach((r) => r());
}

export const sessionStore = {
  subscribe(rappel: () => void) {
    abonnes.add(rappel);
    return () => abonnes.delete(rappel);
  },
  snapshot: () => instantane,
  add(run: QuestionRun) {
    runs = [run, ...runs].slice(0, 30);
    selectedId = run.id;
    emettre();
  },
  update(id: number, patch: Partial<QuestionRun>) {
    runs = runs.map((r) => (r.id === id ? { ...r, ...patch } : r));
    emettre();
  },
  select(id: number) {
    selectedId = id;
    emettre();
  },
};

export function useQuestionSession() {
  const { runs: liste, selectedId: id } = useSyncExternalStore(
    sessionStore.subscribe,
    sessionStore.snapshot,
  );
  return { runs: liste, selected: liste.find((r) => r.id === id) ?? null };
}
