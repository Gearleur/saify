import { useMemo, useState } from "react";
import type { FilterOption } from "@/components/FilterMenu";
import { useReferenceData } from "@/hooks/useReferenceData";
import { PRIORITY_ORDER, TYPE_ORDER, PRIORITIES, SHORT_TYPES } from "@/lib/domain";
import type { WorkStatus, Break } from "@/types/api";
import { WORK_STATUSES, STATUS_ORDER } from "./workStatuses";

export type FilterKey = "priority" | "fund" | "custodian" | "type" | "status";
export type Filters = Record<FilterKey, string[]>;

export const FILTER_KEYS: FilterKey[] = ["priority", "fund", "custodian", "type", "status"];

function initialValues(params: URLSearchParams): Filters {
  const read = (k: FilterKey) => params.get(k)?.split(",").filter(Boolean) ?? [];
  return {
    priority: read("priority"),
    fund: read("fund"),
    custodian: read("custodian"),
    type: read("type"),
    status: read("status"),
  };
}

function count(values: string[]): Map<string, number> {
  const m = new Map<string, number>();
  values.forEach((v) => m.set(v, (m.get(v) ?? 0) + 1));
  return m;
}

/** Recherche (titre, ISIN, action) et filtres cumulables ; les effectifs portent sur toute la liste. */
export function useBreakFilters(
  breaks: Break[],
  getStatus: (s: Break) => WorkStatus,
  params: URLSearchParams,
) {
  const [query, setQuery] = useState(() => params.get("q") ?? "");
  const [filters, setFilters] = useState<Filters>(() => initialValues(params));
  const { custodianName } = useReferenceData();

  const readValue = useMemo(
    () =>
      ({
        priority: (s: Break) => s.priority,
        fund: (s: Break) => s.fund,
        custodian: (s: Break) => s.custodian,
        type: (s: Break) => s.type,
        status: (s: Break) => getStatus(s),
      }) satisfies Record<FilterKey, (s: Break) => string>,
    [getStatus],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return breaks.filter((s) => {
      if (
        q &&
        ![s.security_name, s.isin, s.action, s.entity].some((t) => t.toLowerCase().includes(q))
      )
        return false;
      return FILTER_KEYS.every(
        (k) => filters[k].length === 0 || filters[k].includes(readValue[k](s)),
      );
    });
  }, [breaks, query, filters, readValue]);

  const options = useMemo((): Record<FilterKey, FilterOption[]> => {
    const n = (k: FilterKey) => count(breaks.map(readValue[k]));
    const distinct = (k: FilterKey) => [...n(k).keys()].sort();
    return {
      priority: PRIORITY_ORDER.map((p) => ({
        value: p,
        label: PRIORITIES[p].label,
        tone: PRIORITIES[p].tone,
        count: n("priority").get(p) ?? 0,
      })),
      fund: distinct("fund").map((f) => ({ value: f, label: f, count: n("fund").get(f) })),
      custodian: distinct("custodian").map((c) => ({
        value: c,
        label: custodianName(c),
        hint: c,
        count: n("custodian").get(c),
      })),
      type: TYPE_ORDER.map((t) => ({
        value: t,
        label: SHORT_TYPES[t],
        hint: t,
        count: n("type").get(t) ?? 0,
      })),
      status: STATUS_ORDER.map((s) => ({
        value: s,
        label: WORK_STATUSES[s].label,
        tone: WORK_STATUSES[s].tone,
        count: n("status").get(s) ?? 0,
      })),
    };
  }, [breaks, readValue, custodianName]);

  const setFilter = (k: FilterKey, values: string[]) => setFilters((f) => ({ ...f, [k]: values }));
  const reset = () => {
    setFilters(initialValues(new URLSearchParams()));
    setQuery("");
  };
  const active = query.trim() !== "" || FILTER_KEYS.some((k) => filters[k].length > 0);

  return { query, setQuery, filters, setFilter, options, filtered, reset, active };
}
