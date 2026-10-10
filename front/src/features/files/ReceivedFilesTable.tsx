import { DataTable, type Column } from "@/components/DataTable";
import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import { formatSize } from "@/lib/dates";
import type { Rapprochement } from "@/types/api";
import { receivedSlots, type ReceivedSlot } from "./fileStates";

const COLONNES: Column<ReceivedSlot>[] = [
  {
    id: "source",
    header: "Source",
    className: "w-[80px]",
    cell: (r) => <Tag>{r.attendu.label}</Tag>,
  },
  {
    id: "nom",
    header: "Fichier",
    cell: (r) =>
      r.fichier ? <Mono>{r.fichier.nom}</Mono> : <span className="text-subtle">Non reçu</span>,
  },
  {
    id: "taille",
    header: "Taille",
    align: "right",
    className: "w-[90px]",
    cell: (r) => (r.fichier ? formatSize(r.fichier.taille) : ""),
  },
  {
    id: "controle",
    header: "Contrôle",
    className: "w-[200px]",
    cell: (r) =>
      r.etat === "refuse" ? (
        <StatusLabel tone="red">Refusé, {r.blocage?.regle}</StatusLabel>
      ) : r.etat === "accepte" ? (
        <StatusLabel tone="green">Accepté</StatusLabel>
      ) : (
        <StatusLabel tone="ring">Non reçu</StatusLabel>
      ),
  },
  {
    id: "sha",
    header: "Empreinte SHA-256",
    className: "hidden w-[520px] @4xl:table-cell",
    cell: (r) => <Mono className="break-all text-subtle">{r.fichier?.sha256 ?? ""}</Mono>,
  },
];

/** Preuve de ce qui a été rapproché : nom, taille, contrôle et empreinte complète. */
export function ReceivedFilesTable({ rapprochement }: { rapprochement: Rapprochement }) {
  return (
    <DataTable
      label="Fichiers reçus"
      rows={receivedSlots(rapprochement)}
      columns={COLONNES}
      getRowId={(r) => r.attendu.source}
    />
  );
}
