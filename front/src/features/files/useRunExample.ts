import { useCallback } from "react";
import { useErrorToast } from "@/hooks/useErrorToast";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { formatDateShort } from "@/lib/dates";
import { useAnnounceResult } from "./useAnnounceResult";

/** Lancer sur les fichiers d'exemple ; le libellé porte la date de la base, jamais une date en dur. */
export function useRunExample() {
  const { sante, lancerExemple, chargement } = useReconciliation();
  const { navigate } = useHashRoute();
  const annoncer = useAnnounceResult();
  const signalerErreur = useErrorToast();

  const run = useCallback(async () => {
    try {
      const r = await lancerExemple();
      annoncer(r);
      navigate("a-traiter");
    } catch (e) {
      signalerErreur(e);
    }
  }, [lancerExemple, annoncer, signalerErreur, navigate]);

  const label = sante
    ? `Lancer sur les fichiers d'exemple (${formatDateShort(sante.date_arrete)})`
    : "Lancer sur les fichiers d'exemple";
  return { run, label, busy: chargement === "exemple" };
}
