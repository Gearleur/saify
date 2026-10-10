import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded bg-hover animate-pulse-soft", className)} {...props} />;
}

export { Skeleton };
