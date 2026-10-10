import { useCallback } from "react";
import { CONSERVATEURS_REPLI } from "@/lib/metier";
import { useReconciliation } from "./useReconciliation";

/** Libellés lus dans le paramétrage (repli local si `/api/parametrage` est indisponible). */
export function useReferentiel() {
  const { parametrage } = useReconciliation();

  const nomConservateur = useCallback(
    (code: string): string => {
      const un = (c: string) =>
        parametrage?.conservateurs.find((x) => x.code === c)?.nom ?? CONSERVATEURS_REPLI[c] ?? c;
      return code.includes("→") ? code.split("→").map(un).join(" → ") : un(code);
    },
    [parametrage],
  );

  const nomFonds = useCallback(
    (code: string): string => parametrage?.fonds.find((f) => f.code === code)?.entite ?? code,
    [parametrage],
  );

  return { nomConservateur, nomFonds };
}
