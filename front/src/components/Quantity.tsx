import { formatDecimal, isNegative, isZero } from "@/lib/decimal";
import { cn } from "@/lib/utils";

interface QuantityProps {
  value: string | null;
  /** Écart : `+` devant un positif, gris si nul. */
  signed?: boolean;
  className?: string;
}

/** Quantité ou écart (chaîne décimale), en chiffres tabulaires, sans passer par un float. */
export function Quantity({ value, signed = false, className }: QuantityProps) {
  if (value == null) return <span className={cn("text-subtle", className)}>—</span>;
  const zero = isZero(value);
  return (
    <span
      className={cn(
        "tabular-nums",
        signed && zero && "text-subtle",
        signed && !zero && "font-medium",
        className,
      )}
      data-negative={isNegative(value) || undefined}
    >
      {formatDecimal(value, signed)}
    </span>
  );
}
