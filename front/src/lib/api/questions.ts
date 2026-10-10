import type { EvenementFlux, ReponseQuestion } from "@/types/api";
import { readSse } from "@/lib/sse";
import { postJson, send } from "./http";

const BASE = "/api/questions";
const TYPES = new Set(["etape", "comprehension", "reponse", "erreur", "fin"]);

function versEvenement(event: string, data: string): EvenementFlux | null {
  if (!TYPES.has(event)) return null;
  try {
    return { type: event, data: JSON.parse(data) } as EvenementFlux;
  } catch {
    return null;
  }
}

export const questionsApi = {
  poser: (question: string) => postJson<ReponseQuestion>(BASE, { question }),

  /** Flux SSE : la validation (422) et le rate limit (429) arrivent avant l'ouverture du flux. */
  async *flux(question: string, signal?: AbortSignal): AsyncGenerator<EvenementFlux> {
    const res = await send(`${BASE}/flux`, {
      method: "POST",
      json: { question },
      headers: { Accept: "text/event-stream" },
      signal,
    });
    if (!res.body) return;
    for await (const message of readSse(res.body, signal)) {
      const evenement = versEvenement(message.event, message.data);
      if (evenement) yield evenement;
      if (evenement?.type === "fin") return;
    }
  },
};
