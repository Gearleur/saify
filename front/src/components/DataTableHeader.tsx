import { ArrowDown, ArrowUp } from "lucide-react";
import type { SortState } from "@/hooks/useSort";
import { cn } from "@/lib/utils";
import type { Column } from "./DataTable";

interface DataTableHeaderProps<T> {
  columns: Column<T>[];
  sort?: SortState | null;
  onSort?: (columnId: string) => void;
  /** Table groupée : même retrait que les lignes. */
  inset?: boolean;
}

/** En-têtes gris de 12 px ; un clic trie la colonne (aria-sort pour les lecteurs d'écran). */
export function DataTableHeader<T>({ columns, sort, onSort, inset }: DataTableHeaderProps<T>) {
  return (
    <thead>
      <tr className="border-b border-border">
        {columns.map((c) => {
          const actif = sort?.columnId === c.id;
          const classes = cn(
            "h-8 whitespace-nowrap px-3 text-xs font-medium text-muted-foreground",
            inset ? "first:pl-3 last:pr-3" : "first:pl-1 last:pr-1",
            c.align === "right" ? "text-right" : "text-left",
            c.className,
          );
          if (!c.compare || !onSort) {
            return (
              <th key={c.id} className={classes}>
                {c.header}
              </th>
            );
          }
          return (
            <th
              key={c.id}
              className={classes}
              aria-sort={actif ? (sort?.direction === 1 ? "ascending" : "descending") : "none"}
            >
              <button
                onClick={() => onSort(c.id)}
                className={cn(
                  "inline-flex items-center gap-1 rounded-sm hover:text-foreground",
                  actif && "text-foreground",
                )}
              >
                {c.header}
                {actif &&
                  (sort?.direction === 1 ? (
                    <ArrowUp className="size-3" />
                  ) : (
                    <ArrowDown className="size-3" />
                  ))}
              </button>
            </th>
          );
        })}
      </tr>
    </thead>
  );
}
