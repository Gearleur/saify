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
            <span id={`groupe-${priorite}`} className="flex scroll-mt-20 items-center gap-2">
              <StatusDot tone={info.tone} />
              <span className="font-semibold">{info.group}</span>
              <span className="text-subtle">{rows.length}</span>
              <span className="hidden truncate text-xs text-muted-foreground @3xl:inline">
                {info.description}
              </span>
            </span>
          ),
        };
      })}
    />
  );
}
