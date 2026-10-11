import { describe, expect, it } from "vitest";
import exemple from "../../../../docs/exemple_rapprochement.json";
import type { Anomalie, Rapprochement } from "@/types/api";
import { receivedSlots } from "./fileStates";

// La réponse réelle du back (contrat docs/API.md) : si elle ne colle plus aux types, ce test ne compile plus.
const EXEMPLE: Rapprochement = exemple as Rapprochement;

const bloquant = (fichier: string): Anomalie => ({
  fichier,
  ligne: 0,
  niveau: "BLOQUANT",
  regle: "TOTAL_CONTROLE",
  brut: "",
  retenu: "",
  motif: "NbItems faux",
  remede: "Redemander le fichier",
});

describe("receivedSlots", () => {
  it("les 4 fichiers du 25/09 sont acceptés, dans l'ordre PMS, A, B, C", () => {
    const slots = receivedSlots(EXEMPLE);
    expect(slots.map((s) => [s.attendu.source, s.etat])).toEqual([
      ["PMS", "accepte"],
      ["A", "accepte"],
      ["B", "accepte"],
      ["C", "accepte"],
    ]);
  });

  it("un BLOQUANT sur un fichier le marque refusé, avec son remède", () => {
    const r = { ...EXEMPLE, journal: [bloquant("depositaire_C_20260925.xml")] };
    const c = receivedSlots(r).find((s) => s.attendu.source === "C");
    expect(c?.etat).toBe("refuse");
    expect(c?.blocage?.remede).toBe("Redemander le fichier");
  });

  it("un fichier non déposé est absent, sans rapprochement tout est absent", () => {
    const r = { ...EXEMPLE, fichiers: EXEMPLE.fichiers.filter((f) => f.source !== "B") };
    expect(receivedSlots(r).find((s) => s.attendu.source === "B")?.etat).toBe("absent");
    expect(receivedSlots(null).every((s) => s.etat === "absent")).toBe(true);
  });

  it("le contrat expose les alertes structurées (le front ne lit jamais le texte)", () => {
    const invalide = EXEMPLE.suspens.find((s) => s.isin === "FR0000012966");
    expect(invalide?.alertes).toEqual(["ISIN_INVALIDE"]);
    expect(invalide?.signalements[0]?.code).toBe("ISIN_INVALIDE");
  });
});
