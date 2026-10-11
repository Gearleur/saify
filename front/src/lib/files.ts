/** Dépôt des fichiers du jour : reconnaissance de la source, contrôles avant envoi, encodage base64. */

import type { UploadedFile, FileSource } from "@/types/api";

export const MAX_SIZE = 5 * 1024 * 1024;
export const MAX_FILES = 8;
export const EXTENSIONS = [".csv", ".xlsx", ".txt", ".xml"];

export interface ExpectedSource {
  source: FileSource;
  prefixe: string;
  label: string;
  format: string;
}

export const EXPECTED_SOURCES: ExpectedSource[] = [
  { source: "PMS", prefixe: "positions_internes", label: "PMS", format: "CSV" },
  { source: "A", prefixe: "depositaire_A", label: "A", format: "XLSX" },
  { source: "B", prefixe: "depositaire_B", label: "B", format: "TXT" },
  { source: "C", prefixe: "depositaire_C", label: "C", format: "XML" },
];

export function sourceOf(name: string): FileSource | null {
  if (/^positions_internes/i.test(name)) return "PMS";
  const m = /^depositaire_([abc])/i.exec(name);
  return m?.[1] ? (m[1].toUpperCase() as FileSource) : null;
}

/** Contrôle local (le back refait tout) : un message lisible avant même l'envoi. */
export function checkFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return `Extension non acceptée (attendu : ${EXTENSIONS.join(", ")}).`;
  }
  if (file.size > MAX_SIZE) return "Fichier de plus de 5 Mo.";
  if (!sourceOf(file.name)) {
    return "Nom non reconnu : il doit commencer par positions_internes ou depositaire_A, _B, _C.";
  }
  return null;
}

async function toBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  const delta = 0x8000;
  for (let i = 0; i < bytes.length; i += delta) {
    binary += String.fromCharCode(...bytes.subarray(i, i + delta));
  }
  return btoa(binary);
}

export async function encodeFiles(files: File[]): Promise<UploadedFile[]> {
  return Promise.all(files.map(async (f) => ({ name: f.name, content_b64: await toBase64(f) })));
}
