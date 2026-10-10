import { useReferentiel } from "@/hooks/useReferentiel";
import { formatSize } from "@/lib/dates";
import { SOURCES_ATTENDUES, sourceOf } from "@/lib/files";
import { FileSlot } from "./FileSlot";
import { useFileStaging } from "./useFileStaging";

/** Pendant un dépôt : la sélection en cours seulement, source par source. */
export function StagedStrip() {
  const { staged, remove } = useFileStaging();
  const { nomConservateur } = useReferentiel();
  return (
    <>
      {SOURCES_ATTENDUES.map((attendu) => {
        const s = staged.find((x) => sourceOf(x.file.name) === attendu.source);
        return (
          <FileSlot
            key={attendu.source}
            code={attendu.label}
            nom={attendu.source === "PMS" ? "Inventaire interne" : nomConservateur(attendu.source)}
            format={attendu.format}
            fichier={s?.file.name ?? null}
            tone={!s ? "ring" : s.probleme ? "amber" : "blue"}
            etat={!s ? "Non sélectionné" : (s.probleme ?? "Prêt à envoyer")}
            meta={s ? formatSize(s.file.size) : undefined}
            onRemove={s ? () => remove(s.file.name) : undefined}
          />
        );
      })}
    </>
  );
}
