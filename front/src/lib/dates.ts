/** Dates du contrat (ISO), affichées à la française. Aucune date n'est codée en dur. */

const INCONNUE = "date inconnue";

function parties(iso: string): [string, string, string] | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? [m[1] ?? "", m[2] ?? "", m[3] ?? ""] : null;
}

/** `2026-09-25` → `25/09/2026` ; `null` → « date inconnue ». */
export function formatDate(iso: string | null | undefined): string {
  const p = iso ? parties(iso) : null;
  return p ? `${p[2]}/${p[1]}/${p[0]}` : INCONNUE;
}

/** `2026-09-25` → `25/09`. */
export function formatDateShort(iso: string | null | undefined): string {
  const p = iso ? parties(iso) : null;
  return p ? `${p[2]}/${p[1]}` : INCONNUE;
}

/** Horodatage UTC du contrat → heure locale `14:03`. */
export function formatTime(stamp: string): string {
  const d = new Date(stamp);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/** Horodatage → `10/10 14:03`. */
export function formatStamp(stamp: string): string {
  const d = new Date(stamp);
  if (Number.isNaN(d.getTime())) return stamp;
  const jour = d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
  return `${jour} ${formatTime(stamp)}`;
}

/** Taille d'un fichier en octets (entier, pas un montant) → `2,5 Ko`. */
export function formatSize(octets: number): string {
  if (octets < 1024) return `${octets} o`;
  const ko = octets / 1024;
  if (ko < 1024) return `${ko.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} Ko`;
  return `${(ko / 1024).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} Mo`;
}

/** « Arrêté du 25/09/2026 », ou « Date d'arrêté inconnue » (PMS absent ou multi-dates). */
export function arreteLabel(iso: string | null | undefined): string {
  return iso ? `Arrêté du ${formatDate(iso)}` : "Date d'arrêté inconnue";
}

/** « Rapprochement du 25/09/2026 », ou « Rapprochement à date inconnue ». */
export function rapprochementLabel(iso: string | null | undefined): string {
  return iso ? `Rapprochement du ${formatDate(iso)}` : "Rapprochement à date inconnue";
}
