import { formatDecimal } from "@/lib/decimal";
import type { Figure } from "@/types/api";

function FigureValue({ c, large }: { c: Figure; large?: boolean }) {
  return (
    <span className={large ? "text-figure" : "font-medium"}>
      {formatDecimal(c.value)}
      <span
        className={
          large ? "ml-1.5 text-sm font-normal text-muted-foreground" : "ml-1 text-muted-foreground"
        }
      >
        {c.unit}
      </span>
    </span>
  );
}

/** Les chiffres en grand ; au-delà de trois (concentration), un classement compact sous le premier. */
export function AnswerFigures({ figures }: { figures: Figure[] }) {
  if (figures.length === 0) return null;
  if (figures.length <= 3) {
    return (
      <div className="flex flex-wrap gap-x-10 gap-y-3">
        {figures.map((c) => (
          <div key={c.label}>
            <p className="text-xs text-muted-foreground">{c.label}</p>
            <FigureValue c={c} large />
          </div>
        ))}
      </div>
    );
  }
  return (
    <ol className="max-w-md">
      {figures.map((c, i) => (
        <li
          key={c.label}
          className="flex h-8 items-center gap-3 border-b border-border text-sm last:border-b-0"
        >
          <span className="w-4 text-xs text-subtle">{i + 1}</span>
          <span className="flex-1 truncate">{c.label}</span>
          <FigureValue c={c} />
        </li>
      ))}
    </ol>
  );
}
