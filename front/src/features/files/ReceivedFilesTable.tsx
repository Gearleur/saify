import { DataTable, type Column } from "@/components/DataTable";
import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import { formatSize } from "@/lib/dates";
import type { Reconciliation } from "@/types/api";
import { receivedSlots, type ReceivedSlot } from "./fileStates";

const COLUMNS: Column<ReceivedSlot>[] = [
  {
    id: "source",
    header: "Source",
    className: "w-[80px]",
    cell: (r) => <Tag>{r.expected.label}</Tag>,
  },
  {
    id: "name",
    header: "Fichier",
    cell: (r) =>
      r.file ? <Mono>{r.file.name}</Mono> : <span className="text-subtle">Non reçu</span>,
  },
  {
    id: "size",
    header: "Taille",
    align: "right",
    className: "w-[90px]",
    cell: (r) => (r.file ? formatSize(r.file.size) : ""),
  },
  {
    id: "controle",
    header: "Contrôle",
    className: "w-[200px]",
    cell: (r) =>
      r.state === "rejected" ? (
        <StatusLabel tone="red">Refusé, {r.blocking?.rule}</StatusLabel>
      ) : r.state === "accepted" ? (
        <StatusLabel tone="green">Accepté</StatusLabel>
      ) : (
        <StatusLabel tone="ring">Non reçu</StatusLabel>
      ),
  },
  {
    id: "sha",
    header: "Empreinte SHA-256",
    className: "hidden w-[520px] @4xl:table-cell",
    cell: (r) => <Mono className="break-all text-subtle">{r.file?.sha256 ?? ""}</Mono>,
  },
];

/** Preuve de ce qui a été rapproché : nom, taille, contrôle et empreinte complète. */
export function ReceivedFilesTable({ reconciliation }: { reconciliation: Reconciliation }) {
  return (
    <DataTable
      label="Fichiers reçus"
      rows={receivedSlots(reconciliation)}
      columns={COLUMNS}
      getRowId={(r) => r.expected.source}
    />
  );
}
