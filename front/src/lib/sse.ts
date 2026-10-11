/**
 * Lecteur de flux SSE sur une réponse `fetch` (POST), puisque `EventSource` ne fait que du GET.
 * Découpe le corps en événements `event:` / `data:` séparés par une ligne vide.
 */

export interface SseMessage {
  event: string;
  data: string;
}

function readBlock(block: string): SseMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
  }
  return data.length > 0 || event !== "message" ? { event, data: data.join("\n") } : null;
}

export async function* readSse(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<SseMessage> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (!signal?.aborted) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let separator = /\r?\n\r?\n/.exec(buffer);
      while (separator) {
        const message = readBlock(buffer.slice(0, separator.index));
        buffer = buffer.slice(separator.index + separator[0].length);
        if (message) yield message;
        separator = /\r?\n\r?\n/.exec(buffer);
      }
    }
    const rest = readBlock(buffer);
    if (rest) yield rest;
  } finally {
    reader.releaseLock();
  }
}
