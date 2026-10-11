import { useCallback } from "react";
import { FALLBACK_CUSTODIANS } from "@/lib/domain";
import { useReconciliation } from "./useReconciliation";

/** Libellés lus dans le paramétrage (repli local si `/api/parametrage` est indisponible). */
export function useReferenceData() {
  const { clientConfig } = useReconciliation();

  const custodianName = useCallback(
    (code: string): string => {
      const single = (c: string) =>
        clientConfig?.custodians.find((x) => x.code === c)?.name ?? FALLBACK_CUSTODIANS[c] ?? c;
      return code.includes("→") ? code.split("→").map(single).join(" → ") : single(code);
    },
    [clientConfig],
  );

  const fundName = useCallback(
    (code: string): string => clientConfig?.fund.find((f) => f.code === code)?.entity ?? code,
    [clientConfig],
  );

  return { custodianName, fundName };
}
