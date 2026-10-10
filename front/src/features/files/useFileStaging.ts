import { createContext, useContext } from "react";
import type { ApiError } from "@/lib/api";

export interface StagedFile {
  file: File;
  /** Contrôle local avant envoi (extension, taille, nom). */
  probleme: string | null;
}

export interface FileStagingValue {
  staged: StagedFile[];
  error: ApiError | null;
  sending: boolean;
  add: (files: FileList | File[]) => void;
  remove: (name: string) => void;
  clear: () => void;
  submit: () => Promise<void>;
  /** Ouvre le sélecteur de fichiers du système. */
  pick: () => void;
}

export const FileStagingContext = createContext<FileStagingValue | null>(null);

/** Dépôt en cours : sélection, contrôles locaux, envoi en base64, erreur 413 / 422 / 429. */
export function useFileStaging(): FileStagingValue {
  const ctx = useContext(FileStagingContext);
  if (!ctx) throw new Error("useFileStaging doit être utilisé sous <FileStagingProvider>");
  return ctx;
}
