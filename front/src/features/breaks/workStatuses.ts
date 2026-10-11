import { useCallback, useEffect, useSyncExternalStore } from "react";
import { useErrorToast } from "@/hooks/useErrorToast";
import { reconciliationsApi } from "@/lib/api";
import type { DotTone } from "@/lib/domain";
import type { Reconciliation, WorkStatus, Break } from "@/types/api";

export const WORK_STATUSES: Record<WorkStatus, { label: string; tone: DotTone }> = {
  a_traiter: { label: "À traiter", tone: "ring" },
  en_cours: { label: "En cours", tone: "blue" },
  traite: { label: "Traité", tone: "green" },
};
export const STATUS_ORDER: WorkStatus[] = ["a_traiter", "en_cours", "traite"];

type StatusMap = Record<string, WorkStatus>;

/**
 * Statuts par rapprochement (id → suspens → statut), partagés par toutes les vues.
 * Le serveur est la source de vérité : statuts communs à l'équipe, chaque changement y est tracé.
 */
let byReconciliation: Record<string, StatusMap> = {};
const pending = new Set<string>();
const listeners = new Set<() => void>();

function subscribeLocal(callback: () => void) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function publish(id: string, statuses: StatusMap) {
  byReconciliation = { ...byReconciliation, [id]: statuses };
  listeners.forEach((r) => r());
}

function load(id: string, onError: (e: unknown) => void) {
  if (id in byReconciliation || pending.has(id)) return;
  pending.add(id);
  reconciliationsApi
    .statuses(id)
    .then((r) => publish(id, r.statuses))
    .catch(onError)
    .finally(() => pending.delete(id));
}

/** Statut de traitement des suspens du rapprochement `r` ; `set` est optimiste et annulé en cas d'échec. */
export function useWorkStatuses(r: Reconciliation | null) {
  const everything = useSyncExternalStore(subscribeLocal, () => byReconciliation);
  const report = useErrorToast();
  const id = r?.id ?? null;
  useEffect(() => {
    if (id) load(id, report);
  }, [id, report]);

  const statuses = id ? everything[id] : undefined;
  const get = useCallback((s: Break): WorkStatus => statuses?.[s.id] ?? "a_traiter", [statuses]);
  const set = useCallback(
    async (s: Break, value: WorkStatus) => {
      if (!id) return;
      const before = byReconciliation[id] ?? {};
      const next = { ...before };
      if (value === "a_traiter") delete next[s.id];
      else next[s.id] = value;
      publish(id, next);
      try {
        await reconciliationsApi.setWorkStatus(id, s.id, value);
      } catch (e) {
        publish(id, before);
        report(e);
      }
    },
    [id, report],
  );
  return { get, set };
}
