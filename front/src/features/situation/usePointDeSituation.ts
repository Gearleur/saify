import { useEffect, useState } from "react";
import { ApiError, rapprochementsApi } from "@/lib/api";

type Etat = { id: string; texte: string | null; error: ApiError | null };

/** Texte du point de situation, figé à la création du rapprochement (relu à chaque changement). */
export function usePointDeSituation(id: string | null) {
  const [etat, setEtat] = useState<Etat | null>(null);
  useEffect(() => {
    if (!id) return;
    const ctrl = new AbortController();
    rapprochementsApi
      .pointDeSituation(id, ctrl.signal)
      .then((p) => setEtat({ id, texte: p.texte, error: null }))
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted)
          setEtat({
            id,
            texte: null,
            error:
              e instanceof ApiError
                ? e
                : new ApiError(0, "INCONNU", "Point de situation indisponible."),
          });
      });
    return () => ctrl.abort();
  }, [id]);
  const courant = etat && etat.id === id ? etat : null;
  return {
    texte: courant?.texte ?? null,
    error: courant?.error ?? null,
    loading: !!id && !courant,
  };
}
