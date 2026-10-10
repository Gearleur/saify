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
import { useSuspensSheet } from "@/features/suspens/useSuspensSheet";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { rapprochementsApi } from "@/lib/api";
import { PRIORITES } from "@/lib/metier";
import { ROUTE_DEFS } from "./routes";
import { ThemeCommands } from "./ThemeCommands";

/** « Poser la question » passe toujours après les vues, actions et suspens qui correspondent. */
function filtrer(valeur: string, recherche: string): number {
  if (valeur.startsWith("question ")) return 0.01;
  const mots = recherche.toLowerCase().split(/\s+/).filter(Boolean);
  const texte = valeur.toLowerCase();
  return mots.every((m) => texte.includes(m)) ? 1 : 0;
}

/** Palette ⌘K : aller à une vue, lancer, déposer, exporter, chercher un suspens, poser une question. */
export function CommandPalette({ onClose }: { onClose: () => void }) {
  const [recherche, setRecherche] = useState("");
  const { navigate } = useHashRoute();
  const { courant } = useReconciliation();
  const exemple = useRunExample();
  const { pick } = useFileStaging();
  const sheet = useSuspensSheet();
  const precedent = useRef<Element | null>(document.activeElement);

  useEffect(() => {
    const focus = precedent.current;
    return () => (focus instanceof HTMLElement ? focus.focus() : undefined);
  }, []);

  const faire = (action: () => void) => () => {
    onClose();
    action();
  };
  const question = recherche.trim();

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
          filter={filtrer}
          onKeyDown={(e) => e.key === "Escape" && (e.preventDefault(), onClose())}
        >
          <CommandInput
            autoFocus
            value={recherche}
            onValueChange={setRecherche}
            placeholder="Aller à une vue, chercher un suspens, poser une question…"
          />
          <CommandList>
            <CommandEmpty>Aucun résultat.</CommandEmpty>
            <CommandGroup heading="Vues">
              {ROUTE_DEFS.map(({ id, title, icon: Icon }) => (
                <CommandItem key={id} value={`vue ${title}`} onSelect={faire(() => navigate(id))}>
                  <Icon />
                  {title}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandGroup heading="Actions">
              <CommandItem value={`action ${exemple.label}`} onSelect={faire(exemple.run)}>
                <Play />
                {exemple.label}
              </CommandItem>
              <CommandItem value="action déposer des fichiers" onSelect={faire(pick)}>
                <Upload />
                Déposer des fichiers
              </CommandItem>
              {courant && (
                <CommandItem
                  value="action exporter csv suspens"
                  onSelect={faire(() =>
                    window.location.assign(rapprochementsApi.csvUrl(courant.id)),
                  )}
                >
                  <Download />
                  Exporter les suspens en CSV
                </CommandItem>
              )}
            </CommandGroup>
            <ThemeCommands onDone={onClose} />
            {courant && courant.suspens.length > 0 && (
              <CommandGroup heading="Suspens">
                {courant.suspens.map((s) => (
                  <CommandItem
                    key={s.id}
                    value={`suspens ${s.libelle_titre} ${s.isin} ${s.fonds}`}
                    onSelect={faire(
                      () => (
                        navigate("suspens"),
                        sheet.open(
                          s.id,
                          courant.suspens.map((x) => x.id),
                        )
                      ),
                    )}
                  >
                    <StatusDot tone={PRIORITES[s.priorite].tone} />
                    <span className="truncate">{s.libelle_titre}</span>
                    <Mono className="text-subtle">{s.isin}</Mono>
                    <span className="ml-auto text-xs text-subtle">{s.fonds}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {question.length >= 3 && (
              <CommandGroup heading="Base de gestion">
                <CommandItem
                  value={`question ${question}`}
                  onSelect={faire(() => navigate("questions", { q: question }))}
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
