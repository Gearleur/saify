import type { StreamEvent, QuestionAnswer } from "@/types/api";
import { readSse } from "@/lib/sse";
import { postJson, send } from "./http";

const BASE = "/api/questions";
const TYPES = new Set(["step", "understanding", "answer", "error", "end"]);

function toEvent(event: string, data: string): StreamEvent | null {
  if (!TYPES.has(event)) return null;
  try {
    return { type: event, data: JSON.parse(data) } as StreamEvent;
  } catch {
    return null;
  }
}

export const questionsApi = {
  ask: (question: string) => postJson<QuestionAnswer>(BASE, { question }),

  /** Flux SSE : la validation (422) et le rate limit (429) arrivent avant l'ouverture du flux. */
  async *stream(question: string, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
    const res = await send(`${BASE}/stream`, {
      method: "POST",
      json: { question },
      headers: { Accept: "text/event-stream" },
      signal,
    });
    if (!res.body) return;
    for await (const message of readSse(res.body, signal)) {
      const event = toEvent(message.event, message.data);
      if (event) yield event;
      if (event?.type === "end") return;
    }
  },
};
