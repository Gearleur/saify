import { useMemo, useState } from "react";
import type { FilterOption } from "@/components/FilterMenu";
import { LEVELS, LEVEL_ORDER } from "@/lib/domain";
import type { Anomaly, Level } from "@/types/api";

/** NORMALISE est masqué par défaut : c'est de l'audit, pas de l'action. */
const DEFAULTS: Level[] = ["BLOQUANT", "SIGNALE", "EXCLU"];

export function useJournalFilters(cleaning_log: Anomaly[]) {
  const [levels, setLevels] = useState<string[]>(DEFAULTS);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cleaning_log.filter(
      (a) =>
        levels.includes(a.level) &&
        (!q ||
          [a.file, a.rule, a.reason, a.raw, a.kept, a.remedy].some((t) =>
            t.toLowerCase().includes(q),
          )),
    );
  }, [cleaning_log, levels, query]);

  const options: FilterOption[] = LEVEL_ORDER.map((n) => ({
    value: n,
    label: LEVELS[n].label,
    hint: LEVELS[n].description,
    tone: LEVELS[n].tone,
    count: cleaning_log.filter((a) => a.level === n).length,
  }));

  const normalizationsHidden = levels.includes("NORMALISE")
    ? 0
    : cleaning_log.filter((a) => a.level === "NORMALISE").length;

  return { levels, setLevels, query, setQuery, filtered, options, normalizationsHidden };
}
