import type { ReactNode } from "react";
import { Section } from "@/components/Section";
import { StatusLabel } from "@/components/StatusDot";
import { useReconciliation } from "@/hooks/useReconciliation";
import { LEVELS, LEVEL_ORDER, TYPE_ORDER, SHORT_TYPES } from "@/lib/domain";
import type { Reconciliation } from "@/types/api";
import { FundCustodianMatrix } from "./FundCustodianMatrix";
import { buildMatrix } from "./situationMatrix";

function Ligne({ label, value }: { label: ReactNode; value: number }) {
  return (
    <li className="flex h-9 items-center justify-between border-b border-border pl-1 text-sm">
      {label}
      <span className="tabular-nums text-muted-foreground">{value}</span>
    </li>
  );
}

/** En appui du texte : où sont les suspens, de quel type, et ce qu'a fait le nettoyage. */
export function SituationAside({ r }: { r: Reconciliation }) {
  const { clientConfig } = useReconciliation();
  const matrix = buildMatrix(r.breaks, clientConfig?.fund ?? r.summary.by_fund);
  return (
    <div className="space-y-7">
      <Section title="Fonds × conservateur">
        <FundCustodianMatrix matrix={matrix} />
      </Section>
      <Section title="Par type d'écart">
        <ul>
          {TYPE_ORDER.map((t) => (
            <Ligne key={t} label={SHORT_TYPES[t]} value={r.summary.by_type[t] ?? 0} />
          ))}
        </ul>
      </Section>
      <Section title="Journal de nettoyage">
        <ul>
          {LEVEL_ORDER.map((n) => (
            <Ligne
              key={n}
              label={<StatusLabel tone={LEVELS[n].tone}>{LEVELS[n].label}</StatusLabel>}
              value={r.summary.cleaning_log[n] ?? 0}
            />
          ))}
        </ul>
      </Section>
    </div>
  );
}
