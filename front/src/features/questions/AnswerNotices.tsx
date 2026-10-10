import { StatusDot } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import type { Vigilance } from "@/types/api";

/** Vigilances (seuils internes, jamais un verdict réglementaire) puis avertissements de méthode. */
export function AnswerNotices({
  vigilances,
  avertissements,
}: {
  vigilances: Vigilance[];
  avertissements: string[];
}) {
  if (vigilances.length === 0 && avertissements.length === 0) return null;
  return (
    <div className="space-y-3">
      {vigilances.map((v) => (
        <div key={v.code} className="flex gap-2.5 text-sm">
          <StatusDot tone="amber" className="mt-[7px]" />
          <div className="min-w-0">
            <p className="font-medium">{v.message}</p>
            <p className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
              Seuil de vigilance interne, pas un verdict réglementaire.
              {v.emetteurs.map((e) => (
                <Tag key={e}>{e}</Tag>
              ))}
            </p>
          </div>
        </div>
      ))}
      {avertissements.length > 0 && (
        <ul className="space-y-1 text-sm text-muted-foreground">
          {avertissements.map((a) => (
            <li key={a} className="flex gap-2.5">
              <StatusDot tone="gray" className="mt-[7px]" />
              {a}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
