import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** ISIN, références sources, règles et SQL. */
export function Mono({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("font-mono text-[11.5px] tracking-tight", className)} {...props} />;
}
