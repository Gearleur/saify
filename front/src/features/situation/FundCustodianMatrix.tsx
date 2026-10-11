import { StatusDot } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReferenceData } from "@/hooks/useReferenceData";
import { PRIORITIES } from "@/lib/domain";
import type { Matrix } from "./situationMatrix";

/** Où sont les suspens : un point de la priorité la plus haute, un clic ouvre les suspens filtrés. */
export function FundCustodianMatrix({ matrix }: { matrix: Matrix }) {
  const { navigate } = useHashRoute();
  const { custodianName } = useReferenceData();
  return (
    <table className="w-full table-fixed border-collapse text-sm">
      <thead>
        <tr className="border-b border-border">
          <th className="h-8 w-[30%] pl-1 text-left text-xs font-medium text-muted-foreground">
            Fonds
          </th>
          {matrix.custodians.map((c) => (
            <th
              key={c}
              className="h-8 px-2 text-right text-xs font-medium text-muted-foreground"
              title={custodianName(c)}
            >
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {matrix.fund.map((f) => (
          <tr key={f.code} className="h-row border-b border-border">
            <td className="pl-1" title={f.entity}>
              <Tag>{f.code}</Tag>
            </td>
            {matrix.custodians.map((c) => {
              const { count, top } = matrix.cell(f.code, c);
              return (
                <td key={c} className="px-1 text-right">
                  {count === 0 ? (
                    <span className="px-1 text-subtle">–</span>
                  ) : (
                    <button
                      onClick={() => navigate("suspens", { fund: f.code, custodian: c })}
                      aria-label={`${count} suspens ${f.code} chez ${custodianName(c)}`}
                      className="inline-flex items-center gap-1.5 rounded px-1 py-0.5 font-medium hover:bg-hover"
                    >
                      {top && <StatusDot tone={PRIORITIES[top].tone} />}
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
