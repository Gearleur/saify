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

/** Table façon Supabase : en-têtes gris 12 px, lignes de 38 px, filets de 1 px, sans carte. */
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
  const sections: RowGroup<T>[] = groups ?? [{ id: "lignes", header: null, rows: rows ?? [] }];
  const total = sections.reduce((n, s) => n + s.rows.length, 0);

  const ligne = (row: T) => {
    const id = getRowId(row);
    return (
      <tr
        key={id}
        data-row-id={id}
        aria-selected={onRowClick ? activeId === id : undefined}
        onClick={onRowClick ? () => onRowClick(row) : undefined}
        className={cn(
          "h-[38px] border-b border-border transition-colors duration-100",
          onRowClick && "cursor-pointer hover:bg-hover",
          cursorId === id && "bg-hover shadow-[inset_2px_0_0_var(--foreground)]",
          activeId === id && "bg-selected hover:bg-selected",
        )}
      >
        {columns.map((c) => (
          <td
            key={c.id}
            className={cn(
              "px-3 py-1.5 first:pl-1 last:pr-1",
              c.align === "right" && "text-right",
              c.className,
            )}
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
        <DataTableHeader columns={columns} sort={sort} onSort={onSort} />
        {sections.map((s) => (
          <tbody key={s.id}>
            {s.header && (
              <tr className="border-b border-border">
                <td colSpan={columns.length} className="h-10 pb-2 pl-1 pt-4 align-bottom">
                  {s.header}
                </td>
              </tr>
            )}
            {s.rows.length === 0 && s.empty ? (
              <tr className="h-[38px] border-b border-border">
                <td colSpan={columns.length} className="pl-1 text-sm text-muted-foreground">
                  {s.empty}
                </td>
              </tr>
            ) : (
              s.rows.map(ligne)
            )}
          </tbody>
        ))}
      </table>
      {total === 0 && !groups && empty}
    </div>
  );
}
