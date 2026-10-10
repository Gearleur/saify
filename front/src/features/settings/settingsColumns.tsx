import type { Column } from "@/components/DataTable";
import { Mono } from "@/components/Mono";
import { Tag } from "@/components/Tag";
import type { Conservateur, Fonds, Transco, TypeEcartParam } from "@/types/api";

export const TYPE_COLUMNS: Column<TypeEcartParam>[] = [
  { id: "code", header: "Code", className: "w-[96px]", cell: (t) => <Tag>{t.code}</Tag> },
  { id: "libelle", header: "Libellé", cell: (t) => t.libelle },
  {
    id: "action",
    header: "Action attendue",
    cell: (t) => <span className="font-medium">{t.action_attendue}</span>,
  },
];

export const FONDS_COLUMNS: Column<Fonds>[] = [
  { id: "code", header: "Code", className: "w-[96px]", cell: (f) => <Tag>{f.code}</Tag> },
  { id: "entite", header: "Entité", cell: (f) => f.entite },
];

export const CONSERVATEUR_COLUMNS: Column<Conservateur>[] = [
  { id: "code", header: "Code", className: "w-[96px]", cell: (c) => <Tag>{c.code}</Tag> },
  { id: "nom", header: "Nom", cell: (c) => c.nom },
];

export const TRANSCO_COLUMNS: Column<Transco>[] = [
  { id: "cle", header: "Clé source", className: "w-[45%]", cell: (t) => <Mono>{t.cle}</Mono> },
  { id: "entite", header: "Fonds", cell: (t) => t.entite },
];
