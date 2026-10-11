/**
 * Types du contrat d'API (docs/API.md). Quantités, montants et pourcentages : chaînes décimales.
 * Toute évolution du contrat passe d'abord par docs/API.md, puis par ce fichier.
 */

/** Chaîne décimale (`"250000"`, `"-1000"`, `"5000.5"`), jamais un nombre JSON. */
export type Decimal = string;
/** Date ISO `YYYY-MM-DD`. */
export type IsoDate = string;

export type Priority = "critique" | "a_relever" | "en_attente";
export type BreakType = "QTE" | "ABS_DEP" | "ABS_INT" | "DEP";
export type Level = "NORMALISE" | "EXCLU" | "SIGNALE" | "BLOQUANT";
export type ReconciliationStatus = "OK" | "BLOQUE";
export type FileSource = "PMS" | "A" | "B" | "C";

export interface ErrorBody {
  error: { code: string; message: string; details?: unknown };
}

export interface LlmState {
  enabled: boolean;
  model: string;
  calls_today: number;
  daily_budget: number;
}

export interface Health {
  status: string;
  version: string;
  /** Date de référence de la base de gestion (dernière date de positions dans orsay.db). */
  as_of_date: IsoDate;
  db_available: boolean;
  llm: LlmState;
}

export interface Fund {
  entity: string;
  code: string;
}

export interface Custodian {
  code: string;
  name: string;
}

export interface BreakTypeSetting {
  code: string;
  label: string;
  expected_action: string;
}

export interface Mapping {
  key: string;
  entity: string;
}

export interface ClientConfig {
  as_of_date: IsoDate;
  fund: Fund[];
  custodians: Custodian[];
  break_types: BreakTypeSetting[];
  mappings: Record<string, Mapping[]>;
  exclusions: string[];
}

export interface ReceivedFile {
  name: string;
  source: FileSource | string;
  size: number;
  sha256: string;
}

export interface FundSummary {
  code: string;
  entity: string;
  break_count: number;
}

export interface Summary {
  break_count: number;
  by_priority: Record<Priority, number>;
  by_type: Partial<Record<BreakType, number>>;
  by_fund: FundSummary[];
  by_custodian: Record<string, number>;
  cleaning_log: Partial<Record<Level, number>>;
}

export interface Break {
  id: string;
  priority: Priority;
  fund: string;
  entity: string;
  isin: string;
  security_name: string;
  /** `A`, `B`, `C`, ou `A→B` pour un DEP (attendu chez A, trouvé chez B). */
  custodian: string;
  type: BreakType;
  break_type_label: string;
  pms_qty: Decimal | null;
  custodian_qty: Decimal | null;
  difference: Decimal;
  action: string;
  lead: string;
  /** Ce que les opérations en attente expliquent de l'écart (calcul signé, côté back). */
  explanation: Explanation;
  /** Codes des signalements : c'est eux qu'on lit, jamais le texte des messages. */
  alerts: Alert[];
  flags: Flag[];
  sources: string[];
}

export type Explanation = "aucune" | "totale" | "partielle" | "contraire";
export type Alert = "CSDR" | "DEP_AMBIGU" | "ISIN_INVALIDE" | "PISTE_MULTI_CONSERVATEURS";

export interface Flag {
  code: Alert;
  message: string;
}

/** Statut de traitement d'un suspens, partagé entre les postes (absent = « a_traiter »). */
export type WorkStatus = "a_traiter" | "en_cours" | "traite";

export interface WorkStatuses {
  statuses: Record<string, WorkStatus>;
}

export interface BreakWorkStatus {
  break_id: string;
  status: WorkStatus;
  updated_at: string;
}

export interface Anomaly {
  file: string;
  line: number;
  level: Level;
  rule: string;
  raw: string;
  kept: string;
  reason: string;
  remedy: string;
}

export interface Reconciliation {
  id: string;
  created_at: string;
  /** `null` si le PMS est absent ou porte plusieurs dates (le rapprochement est alors BLOQUE). */
  as_of_date: IsoDate | null;
  status: ReconciliationStatus;
  files: ReceivedFile[];
  summary: Summary;
  breaks: Break[];
  cleaning_log: Anomaly[];
}

export interface ReconciliationSummary {
  id: string;
  created_at: string;
  as_of_date: IsoDate | null;
  status: ReconciliationStatus;
  break_count: number;
  open_count: number;
}

export interface StatusReport {
  text: string;
}

export interface UploadedFile {
  name: string;
  content_b64: string;
}

/* Besoin 2 : questions sur la base de gestion */

export type Intent =
  "ENCOURS" | "ECHEANCES" | "CONCENTRATION" | "NON_DENOUEES" | "ORIGINE_SUSPENS" | "HORS_CATALOGUE";

export interface Figure {
  label: string;
  value: Decimal;
  unit: string;
}

export interface SourceRow {
  table: string;
  values: Record<string, string>;
}

export interface Vigilance {
  code: string;
  message: string;
  issuers: string[];
  /** En %. */
  value: Decimal;
}

export interface Understanding {
  intent: Intent | string;
  fund: string | null;
  horizon_months: number | null;
  isin: string | null;
  source: "llm" | "mots_cles" | string;
  confidence: number;
  detail: string;
  /** Date citée dans la question (AAAA-MM-JJ ou expression relative) : hors date de référence, pas de chiffre. */
  requested_date?: string | null;
}

export interface QuestionAnswer {
  question: string;
  answer: string;
  figures: Figure[];
  sql_query: string;
  sql_params: Record<string, string | null>;
  source_rows: SourceRow[];
  confidence: "haute" | "basse" | string;
  warnings: string[];
  vigilances: Vigilance[];
  suggestions: string[];
  understanding: Understanding;
}

export interface StreamStep {
  step: "understanding" | "computing" | string;
  message: string;
}

/** Événements de `POST /api/questions/flux`, dans l'ordre d'émission. */
export type StreamEvent =
  | { type: "step"; data: StreamStep }
  | { type: "understanding"; data: Understanding }
  | { type: "answer"; data: QuestionAnswer }
  | { type: "error"; data: { code: string; message: string } }
  | { type: "end"; data: Record<string, never> };
