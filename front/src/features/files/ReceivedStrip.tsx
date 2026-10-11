import { useReconciliation } from "@/hooks/useReconciliation";
import { useReferenceData } from "@/hooks/useReferenceData";
import { formatSize } from "@/lib/dates";
import { FileSlot } from "./FileSlot";
import { receivedSlots, type ReceivedState } from "./fileStates";

const STATES: Record<ReceivedState, { label: string; tone: "green" | "red" | "ring" }> = {
  accepted: { label: "Accepté", tone: "green" },
  rejected: { label: "Refusé", tone: "red" },
  absent: { label: "Non reçu", tone: "ring" },
};

/** Les 4 fichiers du dernier rapprochement : reçu, accepté ou refusé. */
export function ReceivedStrip() {
  const { current } = useReconciliation();
  const { custodianName } = useReferenceData();
  return (
    <>
      {receivedSlots(current).map(({ expected, file, state, blocking }) => (
        <FileSlot
          key={expected.source}
          code={expected.label}
          name={expected.source === "PMS" ? "Inventaire interne" : custodianName(expected.source)}
          format={expected.format}
          file={file?.name ?? null}
          tone={STATES[state].tone}
          state={blocking ? `${STATES[state].label}, règle ${blocking.rule}` : STATES[state].label}
          meta={file ? formatSize(file.size) : undefined}
          rejected={state === "rejected"}
        />
      ))}
    </>
  );
}
