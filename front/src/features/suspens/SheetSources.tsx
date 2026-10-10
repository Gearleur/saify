import { Mono } from "@/components/Mono";

function decouper(source: string): { fichier: string; ligne: string } {
  const i = source.lastIndexOf(":");
  return i > 0
    ? { fichier: source.slice(0, i), ligne: source.slice(i + 1) }
    : { fichier: source, ligne: "" };
}

/** Traçabilité : chaque ligne source, fichier et numéro de ligne. */
export function SheetSources({ sources }: { sources: string[] }) {
  return (
    <ol className="divide-y divide-border rounded-lg border border-border">
      {sources.map((src) => {
        const { fichier, ligne } = decouper(src);
        return (
          <li key={src} className="flex items-center justify-between gap-3 px-3 py-2">
            <Mono className="truncate">{fichier}</Mono>
            {ligne && <Mono className="shrink-0 text-subtle">ligne {ligne}</Mono>}
          </li>
        );
      })}
    </ol>
  );
}
