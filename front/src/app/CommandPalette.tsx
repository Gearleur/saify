import { Download, MessageSquareText, Play, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Mono } from "@/components/Mono";
import { StatusDot } from "@/components/StatusDot";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useFileStaging } from "@/features/files/useFileStaging";
import { useRunExample } from "@/features/files/useRunExample";
import { useBreakSheet } from "@/features/breaks/useBreakSheet";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { reconciliationsApi } from "@/lib/api";
import { PRIORITIES } from "@/lib/domain";
import { ROUTE_DEFS } from "./routes";
import { ThemeCommands } from "./ThemeCommands";

/** « Poser la question » passe toujours après les vues, actions et suspens qui correspondent. */
function applyFilter(value: string, search: string): number {
  if (value.startsWith("question ")) return 0.01;
  const words = search.toLowerCase().split(/\s+/).filter(Boolean);
  const text = value.toLowerCase();
  return words.every((m) => text.includes(m)) ? 1 : 0;
}

/** Palette ⌘K : aller à une vue, lancer, déposer, exporter, chercher un suspens, poser une question. */
export function CommandPalette({ onClose }: { onClose: () => void }) {
  const [search, setSearch] = useState("");
  const { navigate } = useHashRoute();
  const { current } = useReconciliation();
  const sample = useRunExample();
  const { pick } = useFileStaging();
  const sheet = useBreakSheet();
  const previous = useRef<Element | null>(document.activeElement);

  useEffect(() => {
    const focus = previous.current;
    return () => (focus instanceof HTMLElement ? focus.focus() : undefined);
  }, []);

  const act = (action: () => void) => () => {
    onClose();
    action();
  };
  const question = search.trim();

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-foreground/10 px-4 pt-[14vh] animate-fade-in"
      onMouseDown={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Palette de commandes"
        onMouseDown={(e) => e.stopPropagation()}
        className="w-full max-w-[600px] overflow-hidden rounded-xl border border-border bg-popover shadow-pop"
      >
        <Command
          data-open
          loop
          filter={applyFilter}
          onKeyDown={(e) => e.key === "Escape" && (e.preventDefault(), onClose())}
        >
          <CommandInput
            autoFocus
            value={search}
            onValueChange={setSearch}
            placeholder="Aller à une vue, chercher un suspens, poser une question…"
          />
          <CommandList>
            <CommandEmpty>Aucun résultat.</CommandEmpty>
            <CommandGroup heading="Vues">
              {ROUTE_DEFS.map(({ id, title, icon: Icon }) => (
                <CommandItem key={id} value={`vue ${title}`} onSelect={act(() => navigate(id))}>
                  <Icon />
                  {title}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandGroup heading="Actions">
              <CommandItem value={`action ${sample.label}`} onSelect={act(sample.run)}>
                <Play />
                {sample.label}
              </CommandItem>
              <CommandItem value="action déposer des fichiers" onSelect={act(pick)}>
                <Upload />
                Déposer des fichiers
              </CommandItem>
              {current && (
                <CommandItem
                  value="action exporter csv suspens"
                  onSelect={act(() =>
                    window.location.assign(reconciliationsApi.csvUrl(current.id)),
                  )}
                >
                  <Download />
                  Exporter les suspens en CSV
                </CommandItem>
              )}
            </CommandGroup>
            <ThemeCommands onDone={onClose} />
            {current && current.breaks.length > 0 && (
              <CommandGroup heading="Suspens">
                {current.breaks.map((s) => (
                  <CommandItem
                    key={s.id}
                    value={`suspens ${s.security_name} ${s.isin} ${s.fund}`}
                    onSelect={act(
                      () => (
                        navigate("suspens"),
                        sheet.open(
                          s.id,
                          current.breaks.map((x) => x.id),
                        )
                      ),
                    )}
                  >
                    <StatusDot tone={PRIORITIES[s.priority].tone} />
                    <span className="truncate">{s.security_name}</span>
                    <Mono className="text-subtle">{s.isin}</Mono>
                    <span className="ml-auto text-xs text-subtle">{s.fund}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {question.length >= 3 && (
              <CommandGroup heading="Base de gestion">
                <CommandItem
                  value={`question ${question}`}
                  onSelect={act(() => navigate("questions", { q: question }))}
                >
                  <MessageSquareText />
                  Poser la question :{" "}
                  <span className="truncate text-muted-foreground">{question}</span>
                </CommandItem>
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </div>
    </div>
  );
}
