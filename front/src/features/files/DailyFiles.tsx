import { Upload } from "lucide-react";
import { ErrorNotice } from "@/components/ErrorNotice";
import { Mono } from "@/components/Mono";
import { Section } from "@/components/Section";
import { StatusLabel } from "@/components/StatusDot";
import { Button } from "@/components/ui/button";
import { sourceOf } from "@/lib/files";
import { ReceivedStrip } from "./ReceivedStrip";
import { StagedStrip } from "./StagedStrip";
import { useFileStaging } from "./useFileStaging";

/** Fichiers du jour : la bande des 4 sources, en réception ou en cours de dépôt. */
export function DailyFiles() {
  const { staged, error, sending, submit, clear, pick } = useFileStaging();
  const upload = staged.length > 0;
  const unrecognized = staged.filter((s) => !sourceOf(s.file.name));
  const ready = upload && staged.every((s) => !s.problem);

  return (
    <Section
      title="Fichiers du jour"
      aside={
        upload ? (
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={clear} disabled={sending}>
              Annuler
            </Button>
            <Button size="sm" onClick={submit} disabled={!ready || sending}>
              {sending ? "Envoi…" : `Rapprocher ces fichiers (${staged.length})`}
            </Button>
          </div>
        ) : (
          <Button variant="ghost" size="sm" onClick={pick}>
            <Upload />
            Déposer des fichiers
          </Button>
        )
      }
    >
      <div className="grid grid-cols-2 divide-border overflow-hidden rounded-lg border border-border lg:grid-cols-4 lg:divide-x [&>*:nth-child(-n+2)]:border-b [&>*:nth-child(-n+2)]:border-border lg:[&>*:nth-child(-n+2)]:border-b-0 [&>*:nth-child(odd)]:border-r [&>*:nth-child(odd)]:border-border">
        {upload ? <StagedStrip /> : <ReceivedStrip />}
      </div>
      {unrecognized.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs">
          {unrecognized.map((s) => (
            <li key={s.file.name} className="flex items-center gap-2">
              <StatusLabel tone="amber">
                <Mono>{s.file.name}</Mono>
              </StatusLabel>
              <span className="text-muted-foreground">{s.problem}</span>
            </li>
          ))}
        </ul>
      )}
      {!upload && (
        <p className="mt-2 text-xs text-subtle">
          Glissez les fichiers n'importe où dans la page, ou utilisez « Déposer des fichiers ».
        </p>
      )}
      {error && <ErrorNotice key={error.at} error={error} className="mt-3" />}
    </Section>
  );
}
