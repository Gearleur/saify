import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ReconciliationContext, type Chargement } from "@/hooks/useReconciliation";
import { ApiError, rapprochementsApi, systemeApi } from "@/lib/api";
import { readJson, writeJson } from "@/lib/storage";
import type {
  FichierEnvoye,
  Parametrage,
  Rapprochement,
  RapprochementResume,
  Sante,
} from "@/types/api";

const CLE_DERNIER = "mo.rapprochement";

function enApiError(e: unknown): ApiError {
  return e instanceof ApiError ? e : new ApiError(0, "INCONNU", "Erreur inattendue.");
}

export function ReconciliationProvider({ children }: { children: ReactNode }) {
  const [sante, setSante] = useState<Sante | null>(null);
  const [santeError, setSanteError] = useState<ApiError | null>(null);
  const [parametrage, setParametrage] = useState<Parametrage | null>(null);
  const [parametrageError, setParametrageError] = useState<ApiError | null>(null);
  const [historique, setHistorique] = useState<RapprochementResume[]>([]);
  const [courant, setCourant] = useState<Rapprochement | null>(null);
  const [chargement, setChargement] = useState<Chargement>("demarrage");

  const rafraichirSante = useCallback(() => {
    systemeApi
      .sante()
      .then((s) => (setSante(s), setSanteError(null)))
      .catch((e: unknown) => setSanteError(enApiError(e)));
  }, []);

  const rafraichirHistorique = useCallback(async () => {
    const liste = await rapprochementsApi.liste();
    setHistorique(liste);
    return liste;
  }, []);

  const afficher = useCallback((r: Rapprochement) => {
    setCourant(r);
    writeJson(CLE_DERNIER, r.id);
  }, []);

  useEffect(() => {
    rafraichirSante();
    systemeApi
      .parametrage()
      .then(setParametrage)
      .catch((e: unknown) => setParametrageError(enApiError(e)));
    const dernier = readJson<string | null>(CLE_DERNIER, null);
    rapprochementsApi
      .liste()
      .then((liste) => (setHistorique(liste), liste))
      .then((liste) =>
        dernier && liste.some((r) => r.id === dernier) ? rapprochementsApi.lire(dernier) : null,
      )
      .then((r) => r && setCourant(r))
      .catch(() => undefined)
      .finally(() => setChargement(null));
  }, [rafraichirSante]);

  const executer = useCallback(
    async (etat: Chargement, appel: () => Promise<Rapprochement>) => {
      setChargement(etat);
      try {
        const r = await appel();
        afficher(r);
        void rafraichirHistorique().catch(() => undefined);
        return r;
      } catch (e) {
        throw enApiError(e);
      } finally {
        setChargement(null);
      }
    },
    [afficher, rafraichirHistorique],
  );

  const lancerExemple = useCallback(
    () => executer("exemple", rapprochementsApi.exemple),
    [executer],
  );
  const envoyer = useCallback(
    (fichiers: FichierEnvoye[]) => executer("envoi", () => rapprochementsApi.creer(fichiers)),
    [executer],
  );
  const ouvrir = useCallback(
    async (id: string) => {
      await executer("lecture", () => rapprochementsApi.lire(id));
    },
    [executer],
  );

  const valeur = useMemo(
    () => ({
      sante,
      santeError,
      parametrage,
      parametrageError,
      historique,
      courant,
      chargement,
      lancerExemple,
      envoyer,
      ouvrir,
      rafraichirSante,
    }),
    [
      sante,
      santeError,
      parametrage,
      parametrageError,
      historique,
      courant,
      chargement,
      lancerExemple,
      envoyer,
      ouvrir,
      rafraichirSante,
    ],
  );

  return <ReconciliationContext.Provider value={valeur}>{children}</ReconciliationContext.Provider>;
}
