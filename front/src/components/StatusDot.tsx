import type { ReactNode } from "react";
import type { DotTone } from "@/lib/domain";
import { cn } from "@/lib/utils";

const TONES: Record<DotTone, string> = {
  red: "bg-dot-red",
  amber: "bg-dot-amber",
  green: "bg-dot-green",
  gray: "bg-dot-gray",
  blue: "bg-dot-blue",
  ring: "border border-dot-gray bg-transparent",
};

interface StatusDotProps {
  tone: DotTone;
  className?: string;
  pulse?: boolean;
}

/** Le seul porteur de couleur de l'interface : un point de 7 px. */
export function StatusDot({ tone, className, pulse }: StatusDotProps) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block size-[7px] shrink-0 rounded-full",
        TONES[tone],
        pulse && "animate-pulse-soft",
        className,
      )}
    />
  );
}

interface StatusLabelProps extends StatusDotProps {
  children: ReactNode;
}

/** Point de couleur suivi d'un texte gris foncé. */
export function StatusLabel({ tone, children, className, pulse }: StatusLabelProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-foreground", className)}>
      <StatusDot tone={tone} pulse={pulse} />
      <span className="truncate">{children}</span>
    </span>
  );
}
