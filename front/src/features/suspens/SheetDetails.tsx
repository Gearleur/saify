import { AttributeList } from "@/components/AttributeList";
import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import { useReferentiel } from "@/hooks/useReferentiel";
import { isCsdr, PRIORITES } from "@/lib/metier";
import type { Suspens } from "@/types/api";

function Signalements({ items }: { items: string[] }) {
  if (items.length === 0) return <span className="text-subtle">Aucun</span>;
  return (
    <ul className="space-y-1">
      {items.map((t) => (
        <li key={t}>
          <StatusLabel
            tone={isCsdr(t) ? "red" : "amber"}
            className="items-start whitespace-normal [&>span:last-child]:whitespace-normal"
          >
            {t}
          </StatusLabel>
        </li>
      ))}
    </ul>
  );
}

/** Attributs du suspens, en liste clé → valeur. */
export function SheetDetails({ s }: { s: Suspens }) {
  const { nomConservateur } = useReferentiel();
  return (
    <AttributeList
      items={[
        {
          label: "Priorité",
          value: (
            <StatusLabel tone={PRIORITES[s.priorite].tone}>
              {PRIORITES[s.priorite].label}
            </StatusLabel>
          ),
        },
        {
          label: "Type",
          value: (
            <span className="flex flex-wrap items-center gap-2">
              {s.libelle_type} <Tag>{s.type}</Tag>
            </span>
          ),
        },
        {
          label: "Fonds",
          value: (
            <span className="flex items-center gap-2">
              <Tag>{s.fonds}</Tag> {s.entite}
            </span>
          ),
        },
        { label: "Conservateur", value: `${nomConservateur(s.conservateur)} (${s.conservateur})` },
        { label: "ISIN", value: <Mono>{s.isin}</Mono> },
        {
          label: "Piste",
          value: s.piste ? (
            s.piste
          ) : (
            <span className="text-subtle">Aucune opération en attente ne l'explique.</span>
          ),
        },
        { label: "Signalements", value: <Signalements items={s.signalements} /> },
      ]}
    />
  );
}
