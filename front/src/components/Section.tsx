import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface SectionProps {
  title: ReactNode;
  count?: number;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}

/** Bloc de page : un titre de 13 px, un compteur gris, et le contenu à plat (sans carte). */
export function Section({ title, count, aside, children, className, id }: SectionProps) {
  return (
    <section id={id} className={cn("scroll-mt-16", className)}>
      <div className="flex min-h-8 items-center justify-between gap-4 pb-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          {title}
          {count !== undefined && <span className="font-normal text-subtle">{count}</span>}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
