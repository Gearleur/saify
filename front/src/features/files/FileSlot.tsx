import { X } from "lucide-react";
import type { ReactNode } from "react";
import { Mono } from "@/components/Mono";
import { StatusLabel } from "@/components/StatusDot";
import type { DotTone } from "@/lib/domain";
import { cn } from "@/lib/utils";

interface FileSlotProps {
  code: string;
  name: string;
  format: string;
  file: string | null;
  tone: DotTone;
  state: ReactNode;
  meta?: ReactNode;
  rejected?: boolean;
  onRemove?: () => void;
}

/** Une source attendue (PMS, A, B, C) : le fichier reçu ou sélectionné, et son état. */
export function FileSlot({
  code,
  name,
  format,
  file,
  tone,
  state,
  meta,
  rejected,
  onRemove,
}: FileSlotProps) {
  return (
    <div className={cn("min-w-0 px-4 py-3", rejected && "bg-danger-wash")}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-semibold text-foreground">{code}</span>
        <span className="truncate">{name}</span>
        <span className="ml-auto text-subtle">{format}</span>
      </div>
      <div className="mt-1.5 flex h-5 items-center gap-1">
        {file ? (
          <Mono className="truncate">{file}</Mono>
        ) : (
          <span className="text-sm text-subtle">Aucun fichier</span>
        )}
        {onRemove && file && (
          <button
            onClick={onRemove}
            aria-label={`Retirer ${file}`}
            className="ml-auto rounded p-0.5 text-subtle hover:text-foreground"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>
      <div className="mt-1 flex items-center justify-between gap-2 text-xs">
        <StatusLabel tone={tone} className="min-w-0">
          {state}
        </StatusLabel>
        {meta && <span className="shrink-0 text-subtle">{meta}</span>}
      </div>
    </div>
  );
}
