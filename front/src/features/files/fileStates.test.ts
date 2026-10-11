import { describe, expect, it } from "vitest";
import sample from "../../../../docs/sample_reconciliation.json";
import type { Anomaly, Reconciliation } from "@/types/api";
import { receivedSlots } from "./fileStates";

// La réponse réelle du back (contrat docs/API.md) : si elle ne colle plus aux types, ce test ne compile plus.
const SAMPLE: Reconciliation = sample as Reconciliation;

const blocking = (file: string): Anomaly => ({
  file,
  line: 0,
  level: "BLOQUANT",
  rule: "TOTAL_CONTROLE",
  raw: "",
  kept: "",
  reason: "NbItems faux",
  remedy: "Redemander le fichier",
});

describe("receivedSlots", () => {
  it("les 4 fichiers du 25/09 sont acceptés, dans l'ordre PMS, A, B, C", () => {
    const slots = receivedSlots(SAMPLE);
    expect(slots.map((s) => [s.expected.source, s.state])).toEqual([
      ["PMS", "accepted"],
      ["A", "accepted"],
      ["B", "accepted"],
      ["C", "accepted"],
    ]);
  });

  it("un BLOQUANT sur un fichier le marque refusé, avec son remède", () => {
    const r = { ...SAMPLE, cleaning_log: [blocking("depositaire_C_20260925.xml")] };
    const c = receivedSlots(r).find((s) => s.expected.source === "C");
    expect(c?.state).toBe("rejected");
    expect(c?.blocking?.remedy).toBe("Redemander le fichier");
  });

  it("un fichier non déposé est absent, sans rapprochement tout est absent", () => {
    const r = { ...SAMPLE, files: SAMPLE.files.filter((f) => f.source !== "B") };
    expect(receivedSlots(r).find((s) => s.expected.source === "B")?.state).toBe("absent");
    expect(receivedSlots(null).every((s) => s.state === "absent")).toBe(true);
  });

  it("le contrat expose les alertes structurées (le front ne lit jamais le texte)", () => {
    const invalid = SAMPLE.breaks.find((s) => s.isin === "FR0000012966");
    expect(invalid?.alerts).toEqual(["ISIN_INVALIDE"]);
    expect(invalid?.flags[0]?.code).toBe("ISIN_INVALIDE");
  });
});
