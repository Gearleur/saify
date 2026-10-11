import { PRIORITY_ORDER } from "@/lib/domain";
import type { Fund, Priority, Break } from "@/types/api";

export interface MatrixCell {
  count: number;
  /** Priorité la plus haute de la case (porte la couleur du point). */
  top: Priority | null;
}

export interface Matrix {
  fund: Fund[];
  custodians: string[];
  cell: (fund: string, custodian: string) => MatrixCell;
}

/** Croisement fonds × conservateur ; un DEP `A→B` garde sa propre colonne (on ne le range pas d'office). */
export function buildMatrix(breaks: Break[], fundRef: Fund[]): Matrix {
  const fundCodes = new Set([...fundRef.map((f) => f.code), ...breaks.map((s) => s.fund)]);
  const fund = [...fundCodes].map(
    (code) => fundRef.find((f) => f.code === code) ?? { code, entity: code },
  );
  const base = ["A", "B", "C"];
  const custodians = [
    ...base,
    ...[...new Set(breaks.map((s) => s.custodian))].filter((c) => !base.includes(c)).sort(),
  ];
  const cell = (f: string, c: string): MatrixCell => {
    const here = breaks.filter((s) => s.fund === f && s.custodian === c);
    const top = PRIORITY_ORDER.find((p) => here.some((s) => s.priority === p)) ?? null;
    return { count: here.length, top };
  };
  return { fund, custodians, cell };
}
