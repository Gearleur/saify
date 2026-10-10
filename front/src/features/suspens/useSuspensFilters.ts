import { useMemo, useState } from "react";
import type { FilterOption } from "@/components/FilterMenu";
import { useReferentiel } from "@/hooks/useReferentiel";
import { ORDRE_PRIORITES, ORDRE_TYPES, PRIORITES, TYPES_COURTS } from "@/lib/metier";
import type { Suspens } from "@/types/api";
import { LOCAL_STATUS, ORDRE_STATUTS, type LocalStatus } from "./localStatus";

export type FilterKey = "priorite" | "fonds" | "conservateur" | "type" | "statut";
export type Filters = Record<FilterKey, string[]>;

export const FILTER_KEYS: FilterKey[] = ["priorite", "fonds", "conservateur", "type", "statut"];

function initiaux(params: URLSearchParams): Filters {
  const lire = (k: FilterKey) => params.get(k)?.split(",").filter(Boolean) ?? [];
  return {
    priorite: lire("priorite"),
    fonds: lire("fonds"),
    conservateur: lire("conservateur"),
    type: lire("type"),
    statut: lire("statut"),
  };
}

function compter(valeurs: string[]): Map<string, number> {
  const m = new Map<string, number>();
  valeurs.forEach((v) => m.set(v, (m.get(v) ?? 0) + 1));
  return m;
}

/** Recherche (titre, ISIN, action) et filtres cumulables ; les effectifs portent sur toute la liste. */
export function useSuspensFilters(
  suspens: Suspens[],
  getStatus: (s: Suspens) => LocalStatus,
  params: URLSearchParams,
) {
  const [query, setQuery] = useState(() => params.get("q") ?? "");
  const [filters, setFilters] = useState<Filters>(() => initiaux(params));
  const { nomConservateur } = useReferentiel();

  const valeurDe = useMemo(
    () =>
      ({
        priorite: (s: Suspens) => s.priorite,
        fonds: (s: Suspens) => s.fonds,
        conservateur: (s: Suspens) => s.conservateur,
        type: (s: Suspens) => s.type,
        statut: (s: Suspens) => getStatus(s),
      }) satisfies Record<FilterKey, (s: Suspens) => string>,
    [getStatus],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return suspens.filter((s) => {
      if (
        q &&
        ![s.libelle_titre, s.isin, s.action, s.entite].some((t) => t.toLowerCase().includes(q))
      )
        return false;
      return FILTER_KEYS.every(
        (k) => filters[k].length === 0 || filters[k].includes(valeurDe[k](s)),
      );
    });
  }, [suspens, query, filters, valeurDe]);

  const options = useMemo((): Record<FilterKey, FilterOption[]> => {
    const n = (k: FilterKey) => compter(suspens.map(valeurDe[k]));
    const distincts = (k: FilterKey) => [...n(k).keys()].sort();
    return {
      priorite: ORDRE_PRIORITES.map((p) => ({
        value: p,
        label: PRIORITES[p].label,
        tone: PRIORITES[p].tone,
        count: n("priorite").get(p) ?? 0,
      })),
      fonds: distincts("fonds").map((f) => ({ value: f, label: f, count: n("fonds").get(f) })),
      conservateur: distincts("conservateur").map((c) => ({
        value: c,
        label: nomConservateur(c),
        hint: c,
        count: n("conservateur").get(c),
      })),
      type: ORDRE_TYPES.map((t) => ({
        value: t,
        label: TYPES_COURTS[t],
        hint: t,
        count: n("type").get(t) ?? 0,
      })),
      statut: ORDRE_STATUTS.map((s) => ({
        value: s,
        label: LOCAL_STATUS[s].label,
        tone: LOCAL_STATUS[s].tone,
        count: n("statut").get(s) ?? 0,
      })),
    };
  }, [suspens, valeurDe, nomConservateur]);

  const setFilter = (k: FilterKey, valeurs: string[]) =>
    setFilters((f) => ({ ...f, [k]: valeurs }));
  const reset = () => {
    setFilters(initiaux(new URLSearchParams()));
    setQuery("");
  };
  const actifs = query.trim() !== "" || FILTER_KEYS.some((k) => filters[k].length > 0);

  return { query, setQuery, filters, setFilter, options, filtered, reset, actifs };
}
