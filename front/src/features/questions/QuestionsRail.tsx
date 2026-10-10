import { Section } from "@/components/Section";
import { StatusDot } from "@/components/StatusDot";
import { cn } from "@/lib/utils";
import { EXEMPLES } from "./catalogue";
import { LlmIndicator } from "./LlmIndicator";
import { sessionStore, useQuestionSession } from "./sessionStore";
import { runTone } from "./runTone";

/** Colonne d'appui : état du LLM, exemples cliquables, historique de la session. */
export function QuestionsRail({ onAsk, busy }: { onAsk: (q: string) => void; busy: boolean }) {
  const { runs, selected } = useQuestionSession();
  return (
    <aside className="space-y-7 xl:sticky xl:top-20 xl:self-start">
      <LlmIndicator />
      <Section title="Exemples">
        <ul className="-mx-1">
          {EXEMPLES.map((q) => (
            <li key={q}>
              <button
                disabled={busy}
                onClick={() => onAsk(q)}
                className="w-full rounded px-1.5 py-1.5 text-left text-sm transition-colors duration-150 hover:bg-hover disabled:opacity-50"
              >
                {q}
              </button>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Cette session" count={runs.length}>
        {runs.length === 0 ? (
          <p className="text-sm text-muted-foreground">Vos questions apparaîtront ici.</p>
        ) : (
          <ul className="-mx-1">
            {runs.map((r) => (
              <li key={r.id}>
                <button
                  onClick={() => sessionStore.select(r.id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded px-1.5 py-1.5 text-left text-sm hover:bg-hover",
                    selected?.id === r.id && "bg-selected",
                  )}
                >
                  <StatusDot
                    tone={runTone(r)}
                    pulse={r.phase === "comprehension" || r.phase === "calcul"}
                  />
                  <span className="truncate">{r.question}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </aside>
  );
}
