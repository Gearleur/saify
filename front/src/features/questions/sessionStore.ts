import { useSyncExternalStore } from "react";
import type { QuestionRun } from "./types";

/** Historique des questions de la session (mémoire de l'onglet, perdu au rechargement, comme une session). */
let runs: QuestionRun[] = [];
let selectedId: number | null = null;
const listeners = new Set<() => void>();
let currentSnapshot: { runs: QuestionRun[]; selectedId: number | null } = { runs, selectedId };

function emit() {
  currentSnapshot = { runs, selectedId };
  listeners.forEach((r) => r());
}

export const sessionStore = {
  subscribe(callback: () => void) {
    listeners.add(callback);
    return () => listeners.delete(callback);
  },
  snapshot: () => currentSnapshot,
  add(run: QuestionRun) {
    runs = [run, ...runs].slice(0, 30);
    selectedId = run.id;
    emit();
  },
  update(id: number, patch: Partial<QuestionRun>) {
    runs = runs.map((r) => (r.id === id ? { ...r, ...patch } : r));
    emit();
  },
  select(id: number) {
    selectedId = id;
    emit();
  },
};

export function useQuestionSession() {
  const { runs: list, selectedId: id } = useSyncExternalStore(
    sessionStore.subscribe,
    sessionStore.snapshot,
  );
  return { runs: list, selected: list.find((r) => r.id === id) ?? null };
}
