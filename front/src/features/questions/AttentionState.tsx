import { CornerDownRight } from "lucide-react";
import { StatusLabel } from "@/components/StatusDot";
import type { ReponseQuestion } from "@/types/api";

interface AttentionStateProps {
  reponse: ReponseQuestion;
  onAsk: (question: string) => void;
}

/** Pas de réponse sûre : aucun chiffre, le message de l'API et des reformulations qui relancent la question. */
export function AttentionState({ reponse, onAsk }: AttentionStateProps) {
  const reste = reponse.reponse.replace(/^Attention\s*:\s*/, "");
  const texte = reste.charAt(0).toUpperCase() + reste.slice(1);
  return (
    <div className="space-y-4">
      <div>
        <StatusLabel tone="amber" className="font-medium">
          Pas de réponse chiffrée
        </StatusLabel>
        <p className="mt-1.5 max-w-[68ch] text-base">{texte}</p>
      </div>
      {reponse.reformulations.length > 0 && (
        <div>
          <p className="pb-1.5 text-xs text-muted-foreground">Essayez plutôt</p>
          <ul className="space-y-0.5">
            {reponse.reformulations.map((r) => (
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
