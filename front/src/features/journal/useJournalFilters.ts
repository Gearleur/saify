import { useMemo, useState } from "react";
import type { FilterOption } from "@/components/FilterMenu";
import { NIVEAUX, ORDRE_NIVEAUX } from "@/lib/metier";
import type { Anomalie, Niveau } from "@/types/api";

/** NORMALISE est masqué par défaut : c'est de l'audit, pas de l'action. */
const PAR_DEFAUT: Niveau[] = ["BLOQUANT", "SIGNALE", "EXCLU"];

export function useJournalFilters(journal: Anomalie[]) {
  const [niveaux, setNiveaux] = useState<string[]>(PAR_DEFAUT);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return journal.filter(
      (a) =>
        niveaux.includes(a.niveau) &&
        (!q ||
          [a.fichier, a.regle, a.motif, a.brut, a.retenu, a.remede].some((t) =>
            t.toLowerCase().includes(q),
          )),
    );
  }, [journal, niveaux, query]);

  const options: FilterOption[] = ORDRE_NIVEAUX.map((n) => ({
    value: n,
    label: NIVEAUX[n].label,
    hint: NIVEAUX[n].description,
    tone: NIVEAUX[n].tone,
    count: journal.filter((a) => a.niveau === n).length,
  }));

  const normalisationsMasquees = niveaux.includes("NORMALISE")
    ? 0
    : journal.filter((a) => a.niveau === "NORMALISE").length;

  return { niveaux, setNiveaux, query, setQuery, filtered, options, normalisationsMasquees };
}
