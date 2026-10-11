import { AttributeList } from "@/components/AttributeList";
import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import { useReferenceData } from "@/hooks/useReferenceData";
import { PRIORITIES } from "@/lib/domain";
import type { Flag, Break } from "@/types/api";

function FlagList({ items }: { items: Flag[] }) {
  if (items.length === 0) return <span className="text-subtle">Aucun</span>;
  return (
    <ul className="space-y-1">
      {items.map((g) => (
        <li key={`${g.code}-${g.message}`}>
          <StatusLabel
            tone={g.code === "CSDR" ? "red" : "amber"}
            className="items-start whitespace-normal [&>span:last-child]:whitespace-normal"
          >
            {g.message}
          </StatusLabel>
        </li>
      ))}
    </ul>
  );
}

/** Attributs du suspens, en liste clé → valeur. */
export function SheetDetails({ s }: { s: Break }) {
  const { custodianName } = useReferenceData();
  return (
    <AttributeList
      items={[
        {
          label: "Priorité",
          value: (
            <StatusLabel tone={PRIORITIES[s.priority].tone}>
              {PRIORITIES[s.priority].label}
            </StatusLabel>
          ),
        },
        {
          label: "Type",
          value: (
            <span className="flex flex-wrap items-center gap-2">
              {s.break_type_label} <Tag>{s.type}</Tag>
            </span>
          ),
        },
        {
          label: "Fonds",
          value: (
            <span className="flex items-center gap-2">
              <Tag>{s.fund}</Tag> {s.entity}
            </span>
          ),
        },
        { label: "Conservateur", value: `${custodianName(s.custodian)} (${s.custodian})` },
        { label: "ISIN", value: <Mono>{s.isin}</Mono> },
        {
          label: "Piste",
          value: s.lead ? (
            s.lead
          ) : (
            <span className="text-subtle">Aucune opération en attente ne l'explique.</span>
          ),
        },
        { label: "Signalements", value: <FlagList items={s.flags} /> },
      ]}
    />
  );
}
