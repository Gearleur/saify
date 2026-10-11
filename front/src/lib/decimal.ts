/**
 * Chaînes décimales du contrat, formatées et comparées sans jamais passer par un nombre flottant.
 * Format français : milliers séparés par une espace fine insécable, virgule décimale, vrai signe moins.
 */

const THIN_SPACE = "\u202f"; // espace fine insécable (séparateur de milliers)
const MINUS = "\u2212"; // vrai signe moins, pas le trait d'union
const PATTERN = /^([+-])?(\d+)(?:\.(\d+))?$/;

interface Parts {
  negative: boolean;
  integerPart: string;
  fraction: string;
}

function split(value: string): Parts | null {
  const m = PATTERN.exec(value.trim());
  if (!m) return null;
  const integerPart = (m[2] ?? "0").replace(/^0+(?=\d)/, "");
  const fraction = m[3] ?? "";
  const zero = /^0*$/.test(integerPart) && /^0*$/.test(fraction);
  return { negative: m[1] === "-" && !zero, integerPart, fraction };
}

function groupThousands(integerPart: string): string {
  return integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, THIN_SPACE);
}

export function isZero(value: string | null | undefined): boolean {
  const p = value == null ? null : split(value);
  return p !== null && /^0*$/.test(p.integerPart) && /^0*$/.test(p.fraction);
}

export function isNegative(value: string | null | undefined): boolean {
  return value != null && (split(value)?.negative ?? false);
}

/** `"-1000"` → `−1 000` ; `signed` ajoute `+` devant un écart positif. Valeur illisible : rendue telle quelle. */
export function formatDecimal(value: string | null | undefined, signed = false): string {
  if (value == null || value === "") return "—";
  const p = split(value);
  if (!p) return value;
  const body = groupThousands(p.integerPart) + (p.fraction ? `,${p.fraction}` : "");
  if (p.negative) return MINUS + body;
  if (signed && !isZero(value)) return `+${body}`;
  return body;
}

function compareAbsolute(a: Parts, b: Parts): number {
  if (a.integerPart.length !== b.integerPart.length)
    return a.integerPart.length - b.integerPart.length;
  if (a.integerPart !== b.integerPart) return a.integerPart < b.integerPart ? -1 : 1;
  const n = Math.max(a.fraction.length, b.fraction.length);
  const fa = a.fraction.padEnd(n, "0");
  const fb = b.fraction.padEnd(n, "0");
  return fa === fb ? 0 : fa < fb ? -1 : 1;
}

/** Tri décimal exact ; `null` et les valeurs illisibles passent en dernier. */
export function compareDecimal(a: string | null, b: string | null): number {
  const pa = a == null ? null : split(a);
  const pb = b == null ? null : split(b);
  if (!pa || !pb) return pa ? -1 : pb ? 1 : 0;
  if (pa.negative !== pb.negative) return pa.negative ? -1 : 1;
  const abs = compareAbsolute(pa, pb);
  return pa.negative ? -abs : abs;
}

export function isDecimal(value: string): boolean {
  return split(value) !== null;
}
