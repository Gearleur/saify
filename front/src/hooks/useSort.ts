import { useCallback, useMemo, useState } from "react";
import type { Column } from "@/components/DataTable";

export interface SortState {
  columnId: string;
  direction: 1 | -1;
}

/** Tri contrôlé d'une DataTable : un clic trie, un second inverse, un troisième revient à l'ordre d'origine. */
export function useSort<T>(rows: T[], columns: Column<T>[], initial: SortState | null = null) {
  const [sort, setSort] = useState<SortState | null>(initial);

  const toggle = useCallback((columnId: string) => {
    setSort((s) => {
      if (!s || s.columnId !== columnId) return { columnId, direction: 1 };
      return s.direction === 1 ? { columnId, direction: -1 } : null;
    });
  }, []);

  const sorted = useMemo(() => {
    const colonne = sort && columns.find((c) => c.id === sort.columnId);
    if (!sort || !colonne?.compare) return rows;
    const compare = colonne.compare;
    return [...rows].sort((a, b) => compare(a, b) * sort.direction);
  }, [rows, columns, sort]);

  return { sort, toggle, sorted };
}
