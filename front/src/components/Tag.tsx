import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** Étiquette neutre (fonds, type, conservateur) : jamais de couleur. */
export function Tag({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center whitespace-nowrap rounded-[5px] border border-tag-border bg-tag px-1.5 text-xs text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
