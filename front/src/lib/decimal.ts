/**
 * Chaînes décimales du contrat, formatées et comparées sans jamais passer par un nombre flottant.
 * Format français : milliers séparés par une espace fine insécable, virgule décimale, vrai signe moins.
 */

const FINE = " ";
const MOINS = "−";
const MOTIF = /^([+-])?(\d+)(?:\.(\d+))?$/;

interface Parts {
  negatif: boolean;
  entier: string;
  fraction: string;
}

function decouper(valeur: string): Parts | null {
  const m = MOTIF.exec(valeur.trim());
  if (!m) return null;
  const entier = (m[2] ?? "0").replace(/^0+(?=\d)/, "");
  const fraction = m[3] ?? "";
  const nul = /^0*$/.test(entier) && /^0*$/.test(fraction);
  return { negatif: m[1] === "-" && !nul, entier, fraction };
}

function grouper(entier: string): string {
  return entier.replace(/\B(?=(\d{3})+(?!\d))/g, FINE);
}

export function isZero(valeur: string | null | undefined): boolean {
  const p = valeur == null ? null : decouper(valeur);
  return p !== null && /^0*$/.test(p.entier) && /^0*$/.test(p.fraction);
}

export function isNegative(valeur: string | null | undefined): boolean {
  return valeur != null && (decouper(valeur)?.negatif ?? false);
}

/** `"-1000"` → `−1 000` ; `signed` ajoute `+` devant un écart positif. Valeur illisible : rendue telle quelle. */
export function formatDecimal(valeur: string | null | undefined, signed = false): string {
  if (valeur == null || valeur === "") return "—";
  const p = decouper(valeur);
  if (!p) return valeur;
  const corps = grouper(p.entier) + (p.fraction ? `,${p.fraction}` : "");
  if (p.negatif) return MOINS + corps;
  if (signed && !isZero(valeur)) return `+${corps}`;
  return corps;
}

function comparerAbsolus(a: Parts, b: Parts): number {
  if (a.entier.length !== b.entier.length) return a.entier.length - b.entier.length;
  if (a.entier !== b.entier) return a.entier < b.entier ? -1 : 1;
  const n = Math.max(a.fraction.length, b.fraction.length);
  const fa = a.fraction.padEnd(n, "0");
  const fb = b.fraction.padEnd(n, "0");
  return fa === fb ? 0 : fa < fb ? -1 : 1;
}

/** Tri décimal exact ; `null` et les valeurs illisibles passent en dernier. */
export function compareDecimal(a: string | null, b: string | null): number {
  const pa = a == null ? null : decouper(a);
  const pb = b == null ? null : decouper(b);
  if (!pa || !pb) return pa ? -1 : pb ? 1 : 0;
  if (pa.negatif !== pb.negatif) return pa.negatif ? -1 : 1;
  const abs = comparerAbsolus(pa, pb);
  return pa.negatif ? -abs : abs;
}

export function isDecimal(valeur: string): boolean {
  return decouper(valeur) !== null;
}
