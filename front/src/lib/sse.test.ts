import { describe, expect, it } from "vitest";
import { readSse, type SseMessage } from "./sse";

function flux(...morceaux: string[]): ReadableStream<Uint8Array> {
  const encodeur = new TextEncoder();
  return new ReadableStream({
    start(c) {
      morceaux.forEach((m) => c.enqueue(encodeur.encode(m)));
      c.close();
    },
  });
}

async function lire(corps: ReadableStream<Uint8Array>, signal?: AbortSignal) {
  const messages: SseMessage[] = [];
  for await (const m of readSse(corps, signal)) messages.push(m);
  return messages;
}

describe("readSse", () => {
  it("découpe les événements séparés par une ligne vide", async () => {
    const messages = await lire(flux('event: etape\ndata: {"a":1}\n\nevent: fin\ndata: {}\n\n'));
    expect(messages).toEqual([
      { event: "etape", data: '{"a":1}' },
      { event: "fin", data: "{}" },
    ]);
  });

  it("recolle un événement coupé entre deux paquets réseau, y compris au milieu d'un accent", async () => {
    const octets = new TextEncoder().encode('event: reponse\ndata: {"t":"échéance"}\n\n');
    const coupe = octets.indexOf(0xc3) + 1; // au milieu du « é » encodé sur deux octets
    const corps = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(octets.slice(0, coupe));
        c.enqueue(octets.slice(coupe));
        c.close();
      },
    });
    expect(await lire(corps)).toEqual([{ event: "reponse", data: '{"t":"échéance"}' }]);
  });

  it("accepte les fins de ligne CRLF et les données sur plusieurs lignes", async () => {
    const messages = await lire(flux("event: x\r\ndata: a\r\ndata: b\r\n\r\n"));
    expect(messages).toEqual([{ event: "x", data: "a\nb" }]);
  });

  it("rend le dernier événement même sans ligne vide finale", async () => {
    expect(await lire(flux("event: fin\ndata: {}"))).toEqual([{ event: "fin", data: "{}" }]);
  });

  it("s'arrête quand le signal est annulé", async () => {
    const ctrl = new AbortController();
    ctrl.abort();
    expect(await lire(flux("event: etape\ndata: {}\n\n"), ctrl.signal)).toEqual([]);
  });
});
