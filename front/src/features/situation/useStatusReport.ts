import { useEffect, useState } from "react";
import { ApiError, reconciliationsApi } from "@/lib/api";

type ReportState = { id: string; text: string | null; error: ApiError | null };

/** Texte du point de situation, figé à la création du rapprochement (relu à chaque changement). */
export function useStatusReport(id: string | null) {
  const [state, setState] = useState<ReportState | null>(null);
  useEffect(() => {
    if (!id) return;
    const ctrl = new AbortController();
    reconciliationsApi
      .statusReport(id, ctrl.signal)
      .then((p) => setState({ id, text: p.text, error: null }))
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted)
          setState({
            id,
            text: null,
            error:
              e instanceof ApiError
                ? e
                : new ApiError(0, "INCONNU", "Point de situation indisponible."),
          });
      });
    return () => ctrl.abort();
  }, [id]);
  const current = state && state.id === id ? state : null;
  return {
    text: current?.text ?? null,
    error: current?.error ?? null,
    loading: !!id && !current,
  };
}
