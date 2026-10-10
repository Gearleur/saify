import { formatDate } from "@/lib/dates";
import { formatDecimal, isDecimal } from "@/lib/decimal";
import type { LigneSource } from "@/types/api";

/** Colonnes numériques (alignées à droite, formatées en décimal), identifiées par leur nom. */
const NUMERIQUES = /^(quantite|cours|valorisation|nominal|montant|prix|poids|valeur)$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function sourceColumns(lignes: LigneSource[]): { cles: string[]; avecTable: boolean } {
  const cles: string[] = [];
  lignes.forEach((l) => Object.keys(l.valeurs).forEach((k) => !cles.includes(k) && cles.push(k)));
  return { cles, avecTable: new Set(lignes.map((l) => l.table)).size > 1 };
}

export function isNumericKey(cle: string): boolean {
  return NUMERIQUES.test(cle);
}

export function formatSourceValue(cle: string, valeur: string | undefined): string {
  if (valeur === undefined || valeur === "") return "";
  if (isNumericKey(cle) && isDecimal(valeur)) return formatDecimal(valeur);
  if (DATE.test(valeur)) return formatDate(valeur);
  return valeur;
}

export function headerLabel(cle: string): string {
  return cle.replace(/_/g, " ");
}
