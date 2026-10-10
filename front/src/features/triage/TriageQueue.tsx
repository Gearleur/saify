import { DataTable, type Column } from "@/components/DataTable";
import { StatusDot } from "@/components/StatusDot";
import { useSuspensSheet } from "@/features/suspens/useSuspensSheet";
import { useListNavigation } from "@/hooks/useListNavigation";
import { PRIORITES } from "@/lib/metier";
import type { Suspens } from "@/types/api";
import type { TriageGroup } from "./useTriage";

interface TriageQueueProps {
  groups: TriageGroup[];
  ids: string[];
  columns: Column<Suspens>[];
}

/** File de traitement groupée par priorité ; un groupe vide le dit (l'absence de critique est une information). */
export function TriageQueue({ groups, ids, columns }: TriageQueueProps) {
  const sheet = useSuspensSheet();
  const ouvrir = (id: string) => sheet.open(id, ids);
  const { cursorId } = useListNavigation({ ids, openId: sheet.openId, onOpen: ouvrir });

  return (
    <DataTable
      label="File de traitement"
      columns={columns}
      getRowId={(s) => s.id}
      onRowClick={(s) => ouvrir(s.id)}
      activeId={sheet.openId}
      cursorId={cursorId}
      groups={groups.map(({ priorite, rows }) => {
        const info = PRIORITES[priorite];
        return {
          id: priorite,
          rows,
          empty: info.empty,
          header: (
            <span
              id={`groupe-${priorite}`}
              className="flex min-w-0 scroll-mt-24 items-center gap-2 whitespace-nowrap"
            >
              <StatusDot tone={info.tone} />
              <span className="font-medium">{info.group}</span>
              <span className="text-xs tabular-nums text-subtle">{rows.length}</span>
              <span className="hidden truncate pl-2 text-xs text-subtle @3xl:inline">
                {info.description}
              </span>
            </span>
          ),
        };
      })}
    />
  );
}
