import { CornerDownRight } from "lucide-react";
import { StatusLabel } from "@/components/StatusDot";
import type { QuestionAnswer } from "@/types/api";

interface AttentionStateProps {
  answer: QuestionAnswer;
  onAsk: (question: string) => void;
}

/** Pas de réponse sûre : aucun chiffre, le message de l'API et des reformulations qui relancent la question. */
export function AttentionState({ answer, onAsk }: AttentionStateProps) {
  const rest = answer.answer.replace(/^Attention\s*:\s*/, "");
  const text = rest.charAt(0).toUpperCase() + rest.slice(1);
  return (
    <div className="space-y-4">
      <div>
        <StatusLabel tone="amber" className="font-medium">
          Pas de réponse chiffrée
        </StatusLabel>
        <p className="mt-1.5 max-w-[68ch] text-base">{text}</p>
      </div>
      {answer.suggestions.length > 0 && (
        <div>
          <p className="pb-1.5 text-xs text-muted-foreground">Essayez plutôt</p>
          <ul className="space-y-0.5">
            {answer.suggestions.map((r) => (
              <li key={r}>
                <button
                  onClick={() => onAsk(r)}
                  className="group flex items-center gap-2 rounded px-1 py-1 text-left text-sm hover:bg-hover"
                >
                  <CornerDownRight className="size-3.5 text-subtle group-hover:text-foreground" />
                  {r}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
