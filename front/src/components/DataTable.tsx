import type { ReactNode } from "react";
import type { SortState } from "@/hooks/useSort";
import { cn } from "@/lib/utils";
import { DataTableHeader } from "./DataTableHeader";

export interface Column<T> {
  id: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  /** Présent : la colonne est triable. */
  compare?: (a: T, b: T) => number;
  align?: "left" | "right";
  /** Largeur, visibilité selon la largeur du conteneur (`hidden @4xl:table-cell`), etc. */
  className?: string;
}

export interface RowGroup<T> {
  id: string;
  /** Ligne d'en-tête du groupe, sur toute la largeur. */
  header: ReactNode;
  rows: T[];
  /** Affiché à la place des lignes quand le groupe est vide. */
  empty?: ReactNode;
}

interface DataTableProps<T> {
  label: string;
  columns: Column<T>[];
  getRowId: (row: T) => string;
  /** Lignes à plat, ou `groups` pour une table groupée (une seule table : colonnes alignées). */
  rows?: T[];
  groups?: RowGroup<T>[];
  onRowClick?: (row: T) => void;
  /** Ligne ouverte dans la fiche. */
  activeId?: string | null;
  /** Ligne sous le curseur clavier. */
  cursorId?: string | null;
  sort?: SortState | null;
  onSort?: (columnId: string) => void;
  empty?: ReactNode;
}

/**
 * Table façon Supabase : en-têtes gris 12 px, lignes de 40 px (`h-row`), filets de 1 px, sans carte.
 * Groupée, elle garde une seule grille (colonnes alignées) et détache chaque groupe par un espace
 * et un bandeau d'en-tête, comme les sections d'Attio ; les cellules prennent alors un retrait.
 */
export function DataTable<T>(props: DataTableProps<T>) {
  const {
    label,
    columns,
    getRowId,
    rows,
    groups,
    onRowClick,
    activeId,
    cursorId,
    sort,
    onSort,
    empty,
  } = props;
  const sections: RowGroup<T>[] = groups ?? [{ id: "rows", header: null, rows: rows ?? [] }];
  const total = sections.reduce((n, s) => n + s.rows.length, 0);
  const indent = groups ? "first:pl-3 last:pr-3" : "first:pl-1 last:pr-1";

  const line = (row: T) => {
    const id = getRowId(row);
    return (
      <tr
        key={id}
        data-row-id={id}
        aria-selected={onRowClick ? activeId === id : undefined}
        onClick={onRowClick ? () => onRowClick(row) : undefined}
        className={cn(
          "h-row border-b border-border transition-colors duration-100",
          onRowClick && "cursor-pointer hover:bg-hover",
          cursorId === id && "bg-hover shadow-[inset_2px_0_0_var(--foreground)]",
          activeId === id && "bg-selected hover:bg-selected",
        )}
      >
        {columns.map((c) => (
          <td
            key={c.id}
            className={cn("px-3 py-1.5", indent, c.align === "right" && "text-right", c.className)}
          >
            {c.cell(row)}
          </td>
        ))}
      </tr>
    );
  };

  return (
    <div className="@container w-full overflow-x-auto">
      <table className="w-full border-collapse text-sm" aria-label={label}>
        <DataTableHeader columns={columns} sort={sort} onSort={onSort} inset={!!groups} />
        {sections.map((s, i) => (
          <tbody key={s.id}>
            {s.header && i > 0 && (
              <tr aria-hidden className="h-5">
                <td colSpan={columns.length} />
              </tr>
            )}
            {s.header && (
              <tr className="border-y border-border bg-surface">
                <td colSpan={columns.length} className="h-9 px-3">
                  {s.header}
                </td>
              </tr>
            )}
            {s.rows.length === 0 && s.empty ? (
              <tr className="h-row border-b border-border">
                <td colSpan={columns.length} className={cn("text-subtle", indent)}>
                  {s.empty}
                </td>
              </tr>
            ) : (
              s.rows.map(line)
            )}
          </tbody>
        ))}
      </table>
      {total === 0 && !groups && empty}
    </div>
  );
}
