import type { ReactNode } from "react";
import { Section } from "@/components/Section";
import { StatusLabel } from "@/components/StatusDot";
import { useReconciliation } from "@/hooks/useReconciliation";
import { NIVEAUX, ORDRE_NIVEAUX, ORDRE_TYPES, TYPES_COURTS } from "@/lib/metier";
import type { Rapprochement } from "@/types/api";
import { FundCustodianMatrix } from "./FundCustodianMatrix";
import { buildMatrix } from "./situationMatrix";

function Ligne({ label, value }: { label: ReactNode; value: number }) {
  return (
    <li className="flex h-8 items-center justify-between border-b border-border pl-1 text-sm">
      {label}
      <span className="tabular-nums text-muted-foreground">{value}</span>
    </li>
  );
}

/** En appui du texte : où sont les suspens, de quel type, et ce qu'a fait le nettoyage. */
export function SituationAside({ r }: { r: Rapprochement }) {
  const { parametrage } = useReconciliation();
  const matrix = buildMatrix(r.suspens, parametrage?.fonds ?? r.synthese.par_fonds);
  return (
    <div className="space-y-8">
      <Section title="Fonds × conservateur">
        <FundCustodianMatrix matrix={matrix} />
      </Section>
      <Section title="Par type d'écart">
        <ul>
          {ORDRE_TYPES.map((t) => (
            <Ligne key={t} label={TYPES_COURTS[t]} value={r.synthese.par_type[t] ?? 0} />
          ))}
        </ul>
      </Section>
      <Section title="Journal de nettoyage">
        <ul>
          {ORDRE_NIVEAUX.map((n) => (
            <Ligne
              key={n}
              label={<StatusLabel tone={NIVEAUX[n].tone}>{NIVEAUX[n].label}</StatusLabel>}
              value={r.synthese.journal[n] ?? 0}
            />
          ))}
        </ul>
      </Section>
    </div>
  );
}
