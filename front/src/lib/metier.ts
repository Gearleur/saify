/** Vocabulaire métier affiché (libellés courts, ordres, couleurs de point). Les règles restent au back. */

import type { Niveau, Priorite, TypeEcart } from "@/types/api";

export type DotTone = "red" | "amber" | "green" | "gray" | "blue" | "ring";

export interface PrioriteInfo {
  label: string;
  group: string;
  tone: DotTone;
  description: string;
  empty: string;
}

export const PRIORITES: Record<Priorite, PrioriteInfo> = {
  critique: {
    label: "Critique",
    group: "Critique",
    tone: "red",
    description: "Risque CSDR : opération non dénouée à sa date prévue, pénalités en jeu.",
    empty: "Aucun risque CSDR détecté.",
  },
  a_relever: {
    label: "À relever",
    group: "À relever",
    tone: "amber",
    description: "Absences, mauvais conservateur, écarts non expliqués.",
    empty: "Rien à relever : tous les écarts sont expliqués.",
  },
  en_attente: {
    label: "En attente",
    group: "En attente de dénouement",
    tone: "gray",
    description: "Écart expliqué par une opération en attente : surveiller le dénouement.",
    empty: "Aucun écart en attente de dénouement.",
  },
};

export const ORDRE_PRIORITES: Priorite[] = ["critique", "a_relever", "en_attente"];

/** Libellé court pour les tables ; le libellé officiel (TYPES_ECARTS) reste dans la fiche. */
export const TYPES_COURTS: Record<TypeEcart, string> = {
  QTE: "Écart de quantité",
  ABS_DEP: "Absent conservateur",
  ABS_INT: "Absent du PMS",
  DEP: "Autre conservateur",
};

export const ORDRE_TYPES: TypeEcart[] = ["QTE", "ABS_DEP", "ABS_INT", "DEP"];

export interface NiveauInfo {
  label: string;
  tone: DotTone;
  description: string;
}

export const NIVEAUX: Record<Niveau, NiveauInfo> = {
  BLOQUANT: {
    label: "Bloquant",
    tone: "red",
    description: "Fichier refusé : rien n'est rapproché tant qu'il n'est pas corrigé.",
  },
  SIGNALE: {
    label: "Signalé",
    tone: "amber",
    description: "Ligne conservée mais douteuse, à vérifier.",
  },
  EXCLU: {
    label: "Exclu",
    tone: "gray",
    description: "Ligne retirée en application d'une règle du client.",
  },
  NORMALISE: {
    label: "Normalisé",
    tone: "ring",
    description: "Valeur remise en forme sans en changer le sens.",
  },
};

export const ORDRE_NIVEAUX: Niveau[] = ["BLOQUANT", "SIGNALE", "EXCLU", "NORMALISE"];

/** Noms de repli si le paramétrage est indisponible (le back les code aussi en dur). */
export const CONSERVATEURS_REPLI: Record<string, string> = {
  A: "CACEIS",
  B: "Euroclear",
  C: "BNP Paribas (BP2S)",
};
