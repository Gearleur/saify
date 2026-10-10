import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** ISIN, références sources, règles et SQL. */
export function Mono({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("font-mono text-mono tracking-tight", className)} {...props} />;
}
