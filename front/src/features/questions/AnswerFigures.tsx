import { formatDecimal } from "@/lib/decimal";
import type { Chiffre } from "@/types/api";

function Valeur({ c, grand }: { c: Chiffre; grand?: boolean }) {
  return (
    <span className={grand ? "text-figure" : "font-medium"}>
      {formatDecimal(c.valeur)}
      <span
        className={
          grand ? "ml-1.5 text-sm font-normal text-muted-foreground" : "ml-1 text-muted-foreground"
        }
      >
        {c.unite}
      </span>
    </span>
  );
}

/** Les chiffres en grand ; au-delà de trois (concentration), un classement compact sous le premier. */
export function AnswerFigures({ chiffres }: { chiffres: Chiffre[] }) {
  if (chiffres.length === 0) return null;
  if (chiffres.length <= 3) {
    return (
      <div className="flex flex-wrap gap-x-10 gap-y-3">
        {chiffres.map((c) => (
          <div key={c.libelle}>
            <p className="text-xs text-muted-foreground">{c.libelle}</p>
            <Valeur c={c} grand />
          </div>
        ))}
      </div>
    );
  }
  return (
    <ol className="max-w-md">
      {chiffres.map((c, i) => (
        <li
          key={c.libelle}
          className="flex h-8 items-center gap-3 border-b border-border text-sm last:border-b-0"
        >
          <span className="w-4 text-xs text-subtle">{i + 1}</span>
          <span className="flex-1 truncate">{c.libelle}</span>
          <Valeur c={c} />
        </li>
      ))}
    </ol>
  );
}
