import { X } from "lucide-react";
import { useCallback, useMemo, useRef, useState, type ReactNode } from "react";
import { ToastContext, type ToastInput } from "@/hooks/useToast";
import { StatusDot } from "./StatusDot";

interface ToastItem extends ToastInput {
  id: number;
}

const MAX = 3;
const DURATION = 4200;

/** Toasts discrets : blancs, un point de couleur, trois au plus, en bas à droite. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const next = useRef(0);

  const dismiss = useCallback((id: number) => setItems((l) => l.filter((t) => t.id !== id)), []);
  const toast = useCallback(
    (input: ToastInput) => {
      const id = ++next.current;
      setItems((l) => [...l, { ...input, id }].slice(-MAX));
      window.setTimeout(() => dismiss(id), DURATION);
    },
    [dismiss],
  );
  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ol
        aria-live="polite"
        className="pointer-events-none fixed bottom-4 left-1/2 z-[60] flex w-[360px] -translate-x-1/2 flex-col gap-2"
      >
        {items.map((t) => (
          <li
            key={t.id}
            className="pointer-events-auto flex items-start gap-2.5 rounded-lg border border-border bg-popover px-3 py-2.5 shadow-pop animate-fade-in"
          >
            <StatusDot tone={t.tone ?? "green"} className="mt-[7px]" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{t.title}</p>
              {t.description && <p className="text-sm text-muted-foreground">{t.description}</p>}
            </div>
            <button
              onClick={() => dismiss(t.id)}
              aria-label="Fermer"
              className="rounded p-0.5 text-subtle hover:text-foreground"
            >
              <X className="size-3.5" />
            </button>
          </li>
        ))}
      </ol>
    </ToastContext.Provider>
  );
}
