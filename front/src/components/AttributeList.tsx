import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface Attribute {
  label: string;
  value: ReactNode;
}

/** Attributs d'un record, façon Attio : libellé gris à gauche, valeur à droite. */
export function AttributeList({ items, className }: { items: Attribute[]; className?: string }) {
  return (
    <dl className={cn("grid grid-cols-[132px_minmax(0,1fr)] gap-x-3", className)}>
      {items.map((item) => (
        <div key={item.label} className="contents">
          <dt className="py-1.5 text-muted-foreground">{item.label}</dt>
          <dd className="min-w-0 py-1.5">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
