import { useCallback } from "react";
import { useErrorToast } from "@/hooks/useErrorToast";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { formatDateShort } from "@/lib/dates";
import { useAnnounceResult } from "./useAnnounceResult";

/** Lancer sur les fichiers d'exemple ; le libellé porte la date de la base, jamais une date en dur. */
export function useRunExample() {
  const { health, runSample, loading } = useReconciliation();
  const { navigate } = useHashRoute();
  const announce = useAnnounceResult();
  const reportError = useErrorToast();

  const run = useCallback(async () => {
    try {
      const r = await runSample();
      announce(r);
      navigate("a-traiter");
    } catch (e) {
      reportError(e);
    }
  }, [runSample, announce, reportError, navigate]);

  const label = health
    ? `Lancer sur les fichiers d'exemple (${formatDateShort(health.as_of_date)})`
    : "Lancer sur les fichiers d'exemple";
  return { run, label, busy: loading === "sample" };
}
