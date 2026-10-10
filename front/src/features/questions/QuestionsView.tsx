import { MessageSquareText } from "lucide-react";
import { useEffect, useRef } from "react";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useHotkeys } from "@/hooks/useHotkeys";
import { QuestionComposer } from "./QuestionComposer";
import { QuestionsRail } from "./QuestionsRail";
import { RunView } from "./RunView";
import { useQuestionSession } from "./sessionStore";
import { useQuestionStream } from "./useQuestionStream";

/** Questions sur la base de gestion (besoin 2) : gérants et RCCI, dans la journée. */
export function QuestionsView() {
  const { selected } = useQuestionSession();
  const { ask, busy } = useQuestionStream();
  const { route, navigate } = useHashRoute();
  const champ = useRef<HTMLTextAreaElement>(null);
  const depuisPalette = route.params.get("q");

  useHotkeys({ "/": (e) => (e.preventDefault(), champ.current?.focus()) });
  useEffect(() => {
    if (!depuisPalette) return;
    navigate("questions");
    void ask(depuisPalette);
  }, [depuisPalette, ask, navigate]);

  return (
    <>
      <PageHeader
        title="Questions"
        description="Interrogez la base de gestion en français. Chaque chiffre vient d'une requête SQL en lecture seule, affichée avec ses lignes sources."
      />
      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div className="min-w-0 max-w-[860px] space-y-6">
          <QuestionComposer onAsk={ask} busy={busy} inputRef={champ} />
          {selected ? (
            <RunView key={selected.id} run={selected} onAsk={ask} />
          ) : (
            <EmptyState
              icon={<MessageSquareText />}
              title="Aucune question pour l'instant"
              description="Encours, tombées d'échéances, concentration par émetteur, opérations non dénouées, origine d'un suspens. Le LLM ne fait que comprendre la question ; il ne voit aucune donnée et n'invente aucun chiffre."
            />
          )}
        </div>
        <QuestionsRail onAsk={ask} busy={busy} />
      </div>
    </>
  );
}
