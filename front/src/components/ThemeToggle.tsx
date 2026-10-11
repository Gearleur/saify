import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { useRef, type KeyboardEvent } from "react";
import { useTheme } from "@/hooks/useTheme";
import type { ThemePreference } from "@/lib/theme";
import { cn } from "@/lib/utils";

/** Les trois choix, partagés avec la palette ⌘K. */
export const THEME_OPTIONS: { value: ThemePreference; label: string; icon: LucideIcon }[] = [
  { value: "light", label: "Clair", icon: Sun },
  { value: "dark", label: "Sombre", icon: Moon },
  { value: "system", label: "Système", icon: Monitor },
];

const STEPS: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };

/** Sélecteur Clair / Sombre / Système : radiogroup à focus mobile (flèches), icônes seules. */
export function ThemeToggle({ className }: { className?: string }) {
  const { preference, setPreference } = useTheme();
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeys = (e: KeyboardEvent) => {
    const delta = STEPS[e.key];
    if (!delta) return;
    e.preventDefault();
    const i = THEME_OPTIONS.findIndex((o) => o.value === preference);
    const next = (i + delta + THEME_OPTIONS.length) % THEME_OPTIONS.length;
    const option = THEME_OPTIONS[next];
    if (!option) return;
    setPreference(option.value);
    buttons.current[next]?.focus();
  };

  return (
    <div
      role="radiogroup"
      aria-label="Thème de l'interface"
      onKeyDown={onKeys}
      className={cn(
        "inline-flex items-center gap-px rounded-md border border-border bg-background p-px",
        className,
      )}
    >
      {THEME_OPTIONS.map(({ value, label, icon: Icon }, i) => {
        const enabled = preference === value;
        return (
          <button
            key={value}
            ref={(el) => {
              buttons.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={enabled}
            aria-label={label}
            title={`Thème ${label.toLowerCase()}`}
            tabIndex={enabled ? 0 : -1}
            onClick={() => setPreference(value)}
            className={cn(
              "flex size-[22px] items-center justify-center rounded-[5px] text-subtle transition-colors duration-150 hover:text-foreground",
              enabled && "bg-hover text-foreground",
            )}
          >
            <Icon className="size-3.5" strokeWidth={1.75} />
          </button>
        );
      })}
    </div>
  );
}
