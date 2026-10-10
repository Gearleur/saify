import { ArrowUp } from "lucide-react";
import { useState, type RefObject } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { QUESTION_MAX, QUESTION_MIN } from "./useQuestionStream";

interface QuestionComposerProps {
  onAsk: (question: string) => void;
  busy: boolean;
  inputRef: RefObject<HTMLTextAreaElement>;
}

/** Champ de question : Entrée envoie, Maj + Entrée passe à la ligne ; 3 à 500 caractères (contrat). */
export function QuestionComposer({ onAsk, busy, inputRef }: QuestionComposerProps) {
  const [texte, setTexte] = useState("");
  const longueur = texte.trim().length;
  const valide = longueur >= QUESTION_MIN && texte.length <= QUESTION_MAX;
  const envoyer = () => {
    if (!valide || busy) return;
    onAsk(texte);
    setTexte("");
  };
  return (
    <form
      onSubmit={(e) => (e.preventDefault(), envoyer())}
      className="rounded-lg border border-border-strong bg-background shadow-[0_1px_2px_rgb(0_0_0/0.04)] transition-colors duration-150 focus-within:border-ring"
    >
      <label htmlFor="question" className="sr-only">
        Votre question
      </label>
      <textarea
        id="question"
        ref={inputRef}
        rows={2}
        value={texte}
        maxLength={QUESTION_MAX}
        onChange={(e) => setTexte(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            envoyer();
          }
        }}
        placeholder="Posez une question sur les fonds, les échéances, les opérations ou un suspens…"
        className="block w-full resize-none bg-transparent px-3.5 pt-3 text-sm outline-none placeholder:text-subtle"
      />
      <div className="flex items-center justify-between gap-3 px-3 pb-2.5">
        <span
          className={cn(
            "text-xs text-subtle",
            texte.length > QUESTION_MAX - 50 && "text-muted-foreground",
          )}
        >
          {longueur > 0 && longueur < QUESTION_MIN
            ? "3 caractères au moins"
            : `${texte.length} / ${QUESTION_MAX}`}
        </span>
        <Button type="submit" size="sm" disabled={!valide || busy}>
          {busy ? "Réponse en cours…" : "Poser la question"}
          {!busy && <ArrowUp />}
        </Button>
      </div>
    </form>
  );
}
