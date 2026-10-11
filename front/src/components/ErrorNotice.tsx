import { useCountdown } from "@/hooks/useCountdown";
import type { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { StatusDot } from "./StatusDot";

interface ErrorNoticeProps {
  error: ApiError;
  className?: string;
}

function readableDetails(details: unknown): string[] {
  if (!Array.isArray(details)) return [];
  return details
    .map((d) => {
      if (typeof d === "string") return d;
      if (d && typeof d === "object" && "message" in d)
        return String((d as { message: unknown }).message);
      return null;
    })
    .filter((d): d is string => !!d)
    .slice(0, 4);
}

/** Erreur du contrat, sobre : un point, le message de l'API, et le délai `Retry-After` d'un 429. */
export function ErrorNotice({ error, className }: ErrorNoticeProps) {
  const remaining = useCountdown(error.retryAfter);
  const details = readableDetails(error.details);
  return (
    <div
      role="alert"
      className={cn(
        "rounded-md border border-border-strong bg-surface px-3 py-2.5 text-sm",
        className,
      )}
    >
      <div className="flex items-start gap-2">
        <StatusDot tone="amber" className="mt-[7px]" />
        <div className="min-w-0">
          <p className="font-medium">{error.message}</p>
          {error.status === 429 && (
            <p className="text-muted-foreground">
              {remaining > 0
                ? `Nouvel essai possible dans ${remaining} s.`
                : "Vous pouvez réessayer."}
            </p>
          )}
          {details.map((d) => (
            <p key={d} className="text-muted-foreground">
              {d}
            </p>
          ))}
          <p className="mt-0.5 font-mono text-2xs text-subtle">
            {error.status > 0 ? `${error.status} ` : ""}
            {error.code}
          </p>
        </div>
      </div>
    </div>
  );
}
