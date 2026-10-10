import { StatusDot } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReferentiel } from "@/hooks/useReferentiel";
import { PRIORITES } from "@/lib/metier";
import type { Matrix } from "./situationMatrix";

/** Où sont les suspens : un point de la priorité la plus haute, un clic ouvre les suspens filtrés. */
export function FundCustodianMatrix({ matrix }: { matrix: Matrix }) {
  const { navigate } = useHashRoute();
  const { nomConservateur } = useReferentiel();
  return (
    <table className="w-full table-fixed border-collapse text-sm">
      <thead>
        <tr className="border-b border-border">
          <th className="h-8 w-[30%] pl-1 text-left text-xs font-medium text-muted-foreground">
            Fonds
          </th>
          {matrix.conservateurs.map((c) => (
            <th
              key={c}
              className="h-8 px-2 text-right text-xs font-medium text-muted-foreground"
              title={nomConservateur(c)}
            >
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {matrix.fonds.map((f) => (
          <tr key={f.code} className="h-[38px] border-b border-border">
            <td className="pl-1" title={f.entite}>
              <Tag>{f.code}</Tag>
            </td>
            {matrix.conservateurs.map((c) => {
              const { count, top } = matrix.cell(f.code, c);
              return (
                <td key={c} className="px-1 text-right">
                  {count === 0 ? (
                    <span className="px-1 text-subtle">–</span>
                  ) : (
                    <button
                      onClick={() => navigate("suspens", { fonds: f.code, conservateur: c })}
                      aria-label={`${count} suspens ${f.code} chez ${nomConservateur(c)}`}
                      className="inline-flex items-center gap-1.5 rounded px-1 py-0.5 font-medium hover:bg-hover"
                    >
                      {top && <StatusDot tone={PRIORITES[top].tone} />}
                      {count}
                    </button>
                  )}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
