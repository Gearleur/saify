import { ChevronDown, ChevronUp, X } from "lucide-react";
import type { ReactNode } from "react";
import { Mono } from "@/components/Mono";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { useHotkeys } from "@/hooks/useHotkeys";
import { useReconciliation } from "@/hooks/useReconciliation";
import { useStatuts } from "./statutsTraitement";
import { StatutControl } from "./StatutControl";
import { SheetComparison } from "./SheetComparison";
import { SheetDetails } from "./SheetDetails";
import { SheetSources } from "./SheetSources";
import { useSuspensSheet } from "./useSuspensSheet";

function Bloc({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t border-border px-5 py-3.5">
      <h3 className="pb-2 text-xs font-medium text-muted-foreground">{title}</h3>
      {children}
    </section>
  );
}

/** Fiche du suspens, lue comme un record Attio : comparer, agir, détails, traçabilité. */
export function SuspensSheet() {
  const { courant } = useReconciliation();
  const { openId, sequence, open, close } = useSuspensSheet();
  const { get, set } = useStatuts(courant);
  const s = courant?.suspens.find((x) => x.id === openId);
  useHotkeys({ Escape: close }, !!s);
  if (!s) return null;

  const i = sequence.indexOf(s.id);
  const voisin = (pas: number) => sequence[i + pas];

  return (
    <aside
      aria-label={`Suspens ${s.id}`}
      className="fixed inset-y-0 right-0 z-40 flex w-[min(420px,100vw)] flex-col border-l border-border bg-background shadow-pop animate-slide-in min-[1280px]:sticky min-[1280px]:top-0 min-[1280px]:z-auto min-[1280px]:h-screen min-[1280px]:shadow-none"
    >
      <header className="flex h-bar shrink-0 items-center gap-1 px-3">
        <Mono className="px-2 text-subtle">{s.id}</Mono>
        <span className="flex-1" />
        <Button
          variant="ghost"
          size="icon"
          aria-label="Suspens précédent"
          disabled={!voisin(-1)}
          onClick={() => open(voisin(-1) ?? s.id)}
        >
          <ChevronUp />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Suspens suivant"
          disabled={!voisin(1)}
          onClick={() => open(voisin(1) ?? s.id)}
        >
          <ChevronDown />
        </Button>
        <Button variant="ghost" size="icon" aria-label="Fermer la fiche" onClick={close}>
          <X />
        </Button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="px-5 pb-4">
          <h2 className="text-heading">{s.libelle_titre}</h2>
          <p className="text-sm text-muted-foreground">
            <Mono>{s.isin}</Mono> <span className="px-1 text-subtle">/</span> {s.entite}
          </p>
          <div className="mt-4">
            <SheetComparison s={s} />
          </div>
        </div>
        <Bloc title="Action attendue">
          <p className="pb-3 font-medium">{s.action}</p>
          <StatutControl value={get(s)} onChange={(v) => set(s, v)} />
          <p className="mt-2 text-xs text-subtle">Statut partagé avec l'équipe ; chaque changement est tracé.</p>
        </Bloc>
        <Bloc title="Détails">
          <SheetDetails s={s} />
        </Bloc>
        <Bloc title="Lignes sources">
          <SheetSources sources={s.sources} />
        </Bloc>
      </div>
      <footer className="flex h-9 shrink-0 items-center gap-3 border-t border-border px-5 text-xs text-subtle">
        <span className="flex items-center gap-1">
          <Kbd>↑</Kbd>
          <Kbd>↓</Kbd> suspens voisin
        </span>
        <span className="flex items-center gap-1">
          <Kbd>Échap</Kbd> fermer
        </span>
      </footer>
    </aside>
  );
}
