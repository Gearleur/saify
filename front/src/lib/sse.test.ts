import { describe, expect, it } from "vitest";
import { readSse, type SseMessage } from "./sse";

function stream(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(c) {
      chunks.forEach((m) => c.enqueue(encoder.encode(m)));
      c.close();
    },
  });
}

async function read(body: ReadableStream<Uint8Array>, signal?: AbortSignal) {
  const messages: SseMessage[] = [];
  for await (const m of readSse(body, signal)) messages.push(m);
  return messages;
}

describe("readSse", () => {
  it("découpe les événements séparés par une ligne vide", async () => {
    const messages = await read(stream('event: step\ndata: {"a":1}\n\nevent: end\ndata: {}\n\n'));
    expect(messages).toEqual([
      { event: "step", data: '{"a":1}' },
      { event: "end", data: "{}" },
    ]);
  });

  it("recolle un événement coupé entre deux paquets réseau, y compris au milieu d'un accent", async () => {
    const bytes = new TextEncoder().encode('event: answer\ndata: {"t":"échéance"}\n\n');
    const cut = bytes.indexOf(0xc3) + 1; // au milieu du « é » encodé sur deux octets
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(bytes.slice(0, cut));
        c.enqueue(bytes.slice(cut));
        c.close();
      },
    });
    expect(await read(body)).toEqual([{ event: "answer", data: '{"t":"échéance"}' }]);
  });

  it("accepte les fins de ligne CRLF et les données sur plusieurs lignes", async () => {
    const messages = await read(stream("event: x\r\ndata: a\r\ndata: b\r\n\r\n"));
    expect(messages).toEqual([{ event: "x", data: "a\nb" }]);
  });

  it("rend le dernier événement même sans ligne vide finale", async () => {
    expect(await read(stream("event: end\ndata: {}"))).toEqual([{ event: "end", data: "{}" }]);
  });

  it("s'arrête quand le signal est annulé", async () => {
    const ctrl = new AbortController();
    ctrl.abort();
    expect(await read(stream("event: step\ndata: {}\n\n"), ctrl.signal)).toEqual([]);
  });
});
