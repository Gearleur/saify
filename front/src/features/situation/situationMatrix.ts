import { ORDRE_PRIORITES } from "@/lib/metier";
import type { Fonds, Priorite, Suspens } from "@/types/api";

export interface MatrixCell {
  count: number;
  /** Priorité la plus haute de la case (porte la couleur du point). */
  top: Priorite | null;
}

export interface Matrix {
  fonds: Fonds[];
  conservateurs: string[];
  cell: (fonds: string, conservateur: string) => MatrixCell;
}

/** Croisement fonds × conservateur ; un DEP `A→B` garde sa propre colonne (on ne le range pas d'office). */
export function buildMatrix(suspens: Suspens[], fondsRef: Fonds[]): Matrix {
  const codesFonds = new Set([...fondsRef.map((f) => f.code), ...suspens.map((s) => s.fonds)]);
  const fonds = [...codesFonds].map(
    (code) => fondsRef.find((f) => f.code === code) ?? { code, entite: code },
  );
  const base = ["A", "B", "C"];
  const conservateurs = [
    ...base,
    ...[...new Set(suspens.map((s) => s.conservateur))].filter((c) => !base.includes(c)).sort(),
  ];
  const cell = (f: string, c: string): MatrixCell => {
    const ici = suspens.filter((s) => s.fonds === f && s.conservateur === c);
    const top = ORDRE_PRIORITES.find((p) => ici.some((s) => s.priorite === p)) ?? null;
    return { count: ici.length, top };
  };
  return { fonds, conservateurs, cell };
}
