import { formatDate } from "@/lib/dates";
import { formatDecimal, isDecimal } from "@/lib/decimal";
import type { SourceRow } from "@/types/api";

/** Colonnes numériques (alignées à droite, formatées en décimal), identifiées par leur nom. */
const NUMERIC = /^(quantite|cours|valorisation|nominal|montant|prix|poids|valeur)$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function sourceColumns(lines: SourceRow[]): { keys: string[]; withTable: boolean } {
  const keys: string[] = [];
  lines.forEach((l) => Object.keys(l.values).forEach((k) => !keys.includes(k) && keys.push(k)));
  return { keys, withTable: new Set(lines.map((l) => l.table)).size > 1 };
}

export function isNumericKey(key: string): boolean {
  return NUMERIC.test(key);
}

export function formatSourceValue(key: string, value: string | undefined): string {
  if (value === undefined || value === "") return "";
  if (isNumericKey(key) && isDecimal(value)) return formatDecimal(value);
  if (DATE.test(value)) return formatDate(value);
  return value;
}

export function headerLabel(key: string): string {
  return key.replace(/_/g, " ");
}
