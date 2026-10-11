/**
 * Types du contrat d'API (docs/API.md). Quantités, montants et pourcentages : chaînes décimales.
 * Toute évolution du contrat passe d'abord par docs/API.md, puis par ce fichier.
 */

/** Chaîne décimale (`"250000"`, `"-1000"`, `"5000.5"`), jamais un nombre JSON. */
export type Decimal = string;
/** Date ISO `YYYY-MM-DD`. */
export type IsoDate = string;

export type Priorite = "critique" | "a_relever" | "en_attente";
export type TypeEcart = "QTE" | "ABS_DEP" | "ABS_INT" | "DEP";
export type Niveau = "NORMALISE" | "EXCLU" | "SIGNALE" | "BLOQUANT";
export type StatutRapprochement = "OK" | "BLOQUE";
export type SourceFichier = "PMS" | "A" | "B" | "C";

export interface ErreurApi {
  erreur: { code: string; message: string; details?: unknown };
}

export interface EtatLlm {
  actif: boolean;
  modele: string;
  appels_aujourdhui: number;
  budget_jour: number;
}

export interface Sante {
  statut: string;
  version: string;
  /** Date de référence de la base de gestion (dernière date de positions dans orsay.db). */
  date_arrete: IsoDate;
  base_disponible: boolean;
  llm: EtatLlm;
}

export interface Fonds {
  entite: string;
  code: string;
}

export interface Conservateur {
  code: string;
  nom: string;
}

export interface TypeEcartParam {
  code: string;
  libelle: string;
  action_attendue: string;
}

export interface Transco {
  cle: string;
  entite: string;
}

export interface Parametrage {
  date_arrete: IsoDate;
  fonds: Fonds[];
  conservateurs: Conservateur[];
  types_ecarts: TypeEcartParam[];
  transcos: Record<string, Transco[]>;
  exclusions: string[];
}

export interface FichierRecu {
  nom: string;
  source: SourceFichier | string;
  taille: number;
  sha256: string;
}

export interface FondsSynthese {
  code: string;
  entite: string;
  nb_suspens: number;
}

export interface Synthese {
  nb_suspens: number;
  par_priorite: Record<Priorite, number>;
  par_type: Partial<Record<TypeEcart, number>>;
  par_fonds: FondsSynthese[];
  par_conservateur: Record<string, number>;
  journal: Partial<Record<Niveau, number>>;
}

export interface Suspens {
  id: string;
  priorite: Priorite;
  fonds: string;
  entite: string;
  isin: string;
  libelle_titre: string;
  /** `A`, `B`, `C`, ou `A→B` pour un DEP (attendu chez A, trouvé chez B). */
  conservateur: string;
  type: TypeEcart;
  libelle_type: string;
  qte_pms: Decimal | null;
  qte_dep: Decimal | null;
  ecart: Decimal;
  action: string;
  piste: string;
  /** Ce que les opérations en attente expliquent de l'écart (calcul signé, côté back). */
  explication: Explication;
  /** Codes des signalements : c'est eux qu'on lit, jamais le texte des messages. */
  alertes: Alerte[];
  signalements: Signalement[];
  sources: string[];
}

export type Explication = "aucune" | "totale" | "partielle" | "contraire";
export type Alerte = "CSDR" | "DEP_AMBIGU" | "ISIN_INVALIDE" | "PISTE_MULTI_CONSERVATEURS";

export interface Signalement {
  code: Alerte;
  message: string;
}

export interface Anomalie {
  fichier: string;
  ligne: number;
  niveau: Niveau;
  regle: string;
  brut: string;
  retenu: string;
  motif: string;
  remede: string;
}

export interface Rapprochement {
  id: string;
  cree_le: string;
  /** `null` si le PMS est absent ou porte plusieurs dates (le rapprochement est alors BLOQUE). */
  date_arrete: IsoDate | null;
  statut: StatutRapprochement;
  fichiers: FichierRecu[];
  synthese: Synthese;
  suspens: Suspens[];
  journal: Anomalie[];
}

export interface RapprochementResume {
  id: string;
  cree_le: string;
  date_arrete: IsoDate | null;
  statut: StatutRapprochement;
  nb_suspens: number;
  nb_a_traiter: number;
}

export interface PointDeSituation {
  texte: string;
}

export interface FichierEnvoye {
  nom: string;
  contenu_b64: string;
}

/* Besoin 2 : questions sur la base de gestion */

export type Intention =
  "ENCOURS" | "ECHEANCES" | "CONCENTRATION" | "NON_DENOUEES" | "ORIGINE_SUSPENS" | "HORS_CATALOGUE";

export interface Chiffre {
  libelle: string;
  valeur: Decimal;
  unite: string;
}

export interface LigneSource {
  table: string;
  valeurs: Record<string, string>;
}

export interface Vigilance {
  code: string;
  message: string;
  emetteurs: string[];
  /** En %. */
  valeur: Decimal;
}

export interface Comprehension {
  intention: Intention | string;
  fonds: string | null;
  horizon_mois: number | null;
  isin: string | null;
  source: "llm" | "mots_cles" | string;
  confiance: number;
  detail: string;
  /** Date citée dans la question (AAAA-MM-JJ ou expression relative) : hors date de référence, pas de chiffre. */
  date_demandee?: string | null;
}

export interface ReponseQuestion {
  question: string;
  reponse: string;
  chiffres: Chiffre[];
  requete_sql: string;
  parametres_sql: Record<string, string | null>;
  lignes_sources: LigneSource[];
  confiance: "haute" | "basse" | string;
  avertissements: string[];
  vigilances: Vigilance[];
  reformulations: string[];
  comprehension: Comprehension;
}

export interface EtapeFlux {
  etape: "comprehension" | "calcul" | string;
  message: string;
}

/** Événements de `POST /api/questions/flux`, dans l'ordre d'émission. */
export type EvenementFlux =
  | { type: "etape"; data: EtapeFlux }
  | { type: "comprehension"; data: Comprehension }
  | { type: "reponse"; data: ReponseQuestion }
  | { type: "erreur"; data: { code: string; message: string } }
  | { type: "fin"; data: Record<string, never> };
