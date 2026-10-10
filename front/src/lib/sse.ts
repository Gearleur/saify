/**
 * Lecteur de flux SSE sur une réponse `fetch` (POST), puisque `EventSource` ne fait que du GET.
 * Découpe le corps en événements `event:` / `data:` séparés par une ligne vide.
 */

export interface SseMessage {
  event: string;
  data: string;
}

function lireBloc(bloc: string): SseMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const ligne of bloc.split(/\r?\n/)) {
    if (ligne.startsWith("event:")) event = ligne.slice(6).trim();
    else if (ligne.startsWith("data:")) data.push(ligne.slice(5).replace(/^ /, ""));
  }
  return data.length > 0 || event !== "message" ? { event, data: data.join("\n") } : null;
}

export async function* readSse(
  corps: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<SseMessage> {
  const lecteur = corps.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  try {
    while (!signal?.aborted) {
      const { value, done } = await lecteur.read();
      if (done) break;
      tampon += decodeur.decode(value, { stream: true });
      let separateur = /\r?\n\r?\n/.exec(tampon);
      while (separateur) {
        const message = lireBloc(tampon.slice(0, separateur.index));
        tampon = tampon.slice(separateur.index + separateur[0].length);
        if (message) yield message;
        separateur = /\r?\n\r?\n/.exec(tampon);
      }
    }
    const reste = lireBloc(tampon);
    if (reste) yield reste;
  } finally {
    lecteur.releaseLock();
  }
}
