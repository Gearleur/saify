import { Mono } from "@/components/Mono";

function split(source: string): { file: string; line: string } {
  const i = source.lastIndexOf(":");
  return i > 0
    ? { file: source.slice(0, i), line: source.slice(i + 1) }
    : { file: source, line: "" };
}

/** Traçabilité : chaque ligne source, fichier et numéro de ligne. */
export function SheetSources({ sources }: { sources: string[] }) {
  return (
    <ol className="divide-y divide-border rounded-lg border border-border">
      {sources.map((src) => {
        const { file, line } = split(src);
        return (
          <li key={src} className="flex items-center justify-between gap-3 px-3 py-2">
            <Mono className="truncate">{file}</Mono>
            {line && <Mono className="shrink-0 text-subtle">ligne {line}</Mono>}
          </li>
        );
      })}
    </ol>
  );
}
