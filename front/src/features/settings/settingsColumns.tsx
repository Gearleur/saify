import type { Column } from "@/components/DataTable";
import { Mono } from "@/components/Mono";
import { Tag } from "@/components/Tag";
import type { Custodian, Fund, Mapping, BreakTypeSetting } from "@/types/api";

export const TYPE_COLUMNS: Column<BreakTypeSetting>[] = [
  { id: "code", header: "Code", className: "w-[96px]", cell: (t) => <Tag>{t.code}</Tag> },
  { id: "label", header: "Libellé", cell: (t) => t.label },
  {
    id: "action",
    header: "Action attendue",
    cell: (t) => <span className="font-medium">{t.expected_action}</span>,
  },
];

export const FUND_COLUMNS: Column<Fund>[] = [
  { id: "code", header: "Code", className: "w-[96px]", cell: (f) => <Tag>{f.code}</Tag> },
  { id: "entity", header: "Entité", cell: (f) => f.entity },
];

export const CUSTODIAN_COLUMNS: Column<Custodian>[] = [
  { id: "code", header: "Code", className: "w-[96px]", cell: (c) => <Tag>{c.code}</Tag> },
  { id: "name", header: "Nom", cell: (c) => c.name },
];

export const MAPPING_COLUMNS: Column<Mapping>[] = [
  { id: "key", header: "Clé source", className: "w-[45%]", cell: (t) => <Mono>{t.key}</Mono> },
  { id: "entity", header: "Fonds", cell: (t) => t.entity },
];
