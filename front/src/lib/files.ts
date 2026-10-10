/** Dépôt des fichiers du jour : reconnaissance de la source, contrôles avant envoi, encodage base64. */

import type { FichierEnvoye, SourceFichier } from "@/types/api";

export const TAILLE_MAX = 5 * 1024 * 1024;
export const NB_MAX = 8;
export const EXTENSIONS = [".csv", ".xlsx", ".txt", ".xml"];

export interface SourceAttendue {
  source: SourceFichier;
  prefixe: string;
  label: string;
  format: string;
}

export const SOURCES_ATTENDUES: SourceAttendue[] = [
  { source: "PMS", prefixe: "positions_internes", label: "PMS", format: "CSV" },
  { source: "A", prefixe: "depositaire_A", label: "A", format: "XLSX" },
  { source: "B", prefixe: "depositaire_B", label: "B", format: "TXT" },
  { source: "C", prefixe: "depositaire_C", label: "C", format: "XML" },
];

export function sourceOf(nom: string): SourceFichier | null {
  if (/^positions_internes/i.test(nom)) return "PMS";
  const m = /^depositaire_([abc])/i.exec(nom);
  return m?.[1] ? (m[1].toUpperCase() as SourceFichier) : null;
}

/** Contrôle local (le back refait tout) : un message lisible avant même l'envoi. */
export function checkFile(fichier: File): string | null {
  const nom = fichier.name.toLowerCase();
  if (!EXTENSIONS.some((ext) => nom.endsWith(ext))) {
    return `Extension non acceptée (attendu : ${EXTENSIONS.join(", ")}).`;
  }
  if (fichier.size > TAILLE_MAX) return "Fichier de plus de 5 Mo.";
  if (!sourceOf(fichier.name)) {
    return "Nom non reconnu : il doit commencer par positions_internes ou depositaire_A, _B, _C.";
  }
  return null;
}

async function versBase64(fichier: File): Promise<string> {
  const octets = new Uint8Array(await fichier.arrayBuffer());
  let binaire = "";
  const pas = 0x8000;
  for (let i = 0; i < octets.length; i += pas) {
    binaire += String.fromCharCode(...octets.subarray(i, i + pas));
  }
  return btoa(binaire);
}

export async function encodeFiles(fichiers: File[]): Promise<FichierEnvoye[]> {
  return Promise.all(
    fichiers.map(async (f) => ({ nom: f.name, contenu_b64: await versBase64(f) })),
  );
}
