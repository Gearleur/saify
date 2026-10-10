import type { Comprehension, ReponseQuestion } from "@/types/api";

/** Ce que l'outil sait calculer (le catalogue du back), en mots de gérant. */
export const INTENTIONS: Record<string, string> = {
  ENCOURS: "Encours valorisé",
  ECHEANCES: "Tombées d'échéances",
  CONCENTRATION: "Concentration par émetteur",
  NON_DENOUEES: "Opérations non dénouées",
  ORIGINE_SUSPENS: "Origine d'un suspens",
  HORS_CATALOGUE: "Hors catalogue",
};

export const EXEMPLES = [
  "Quel est l'encours du fonds OBL ?",
  "Quelles tombées d'échéances dans les 3 mois ?",
  "Quelle est la concentration par émetteur du fonds PAT ?",
  "Quelles opérations ne sont pas encore dénouées ?",
  "D'où vient le suspens sur SCHNEIDER ?",
];

export function sourceLabel(source: string): string {
  return source === "llm" ? "LLM" : source === "mots_cles" ? "mots-clés" : source;
}

export function formatConfidence(c: number): string {
  return c.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** « Encours valorisé, fonds OBL » : l'intention comprise et ses paramètres. */
export function describeIntent(c: Comprehension): string {
  const morceaux = [INTENTIONS[c.intention] ?? c.intention];
  if (c.fonds) morceaux.push(`fonds ${c.fonds}`);
  if (c.horizon_mois) morceaux.push(`${c.horizon_mois} mois`);
  if (c.isin) morceaux.push(c.isin);
  return morceaux.join(", ");
}

/** Durée navigateur entre deux événements du flux. */
export function formatDuration(ms: number): string {
  return ms < 1000
    ? `${Math.max(1, Math.round(ms))} ms`
    : `${(ms / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} s`;
}

/** Réponse sans chiffre sûr (le back commence alors par « Attention : »). */
export function isAttention(r: ReponseQuestion): boolean {
  return r.chiffres.length === 0 || r.reponse.startsWith("Attention");
}
