import { useReferenceData } from "@/hooks/useReferenceData";
import { formatSize } from "@/lib/dates";
import { EXPECTED_SOURCES, sourceOf } from "@/lib/files";
import { FileSlot } from "./FileSlot";
import { useFileStaging } from "./useFileStaging";

/** Pendant un dépôt : la sélection en cours seulement, source par source. */
export function StagedStrip() {
  const { staged, remove } = useFileStaging();
  const { custodianName } = useReferenceData();
  return (
    <>
      {EXPECTED_SOURCES.map((expected) => {
        const s = staged.find((x) => sourceOf(x.file.name) === expected.source);
        return (
          <FileSlot
            key={expected.source}
            code={expected.label}
            name={expected.source === "PMS" ? "Inventaire interne" : custodianName(expected.source)}
            format={expected.format}
            file={s?.file.name ?? null}
            tone={!s ? "ring" : s.problem ? "amber" : "blue"}
            state={!s ? "Non sélectionné" : (s.problem ?? "Prêt à envoyer")}
            meta={s ? formatSize(s.file.size) : undefined}
            onRemove={s ? () => remove(s.file.name) : undefined}
          />
        );
      })}
    </>
  );
}
