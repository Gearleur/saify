import type {
  UploadedFile,
  StatusReport,
  Reconciliation,
  ReconciliationSummary,
  WorkStatuses,
  BreakWorkStatus,
  WorkStatus,
} from "@/types/api";
import { getJson, postJson, putJson } from "./http";

const BASE = "/api/reconciliations";

export const reconciliationsApi = {
  list: (signal?: AbortSignal) => getJson<ReconciliationSummary[]>(BASE, signal),
  read: (id: string, signal?: AbortSignal) =>
    getJson<Reconciliation>(`${BASE}/${encodeURIComponent(id)}`, signal),
  create: (files: UploadedFile[]) => postJson<Reconciliation>(BASE, { files }),
  sample: () => postJson<Reconciliation>(`${BASE}/sample`),
  statusReport: (id: string, signal?: AbortSignal) =>
    getJson<StatusReport>(`${BASE}/${encodeURIComponent(id)}/status-report`, signal),
  statuses: (id: string) => getJson<WorkStatuses>(`${BASE}/${encodeURIComponent(id)}/statuses`),
  setWorkStatus: (id: string, breakId: string, status: WorkStatus) =>
    putJson<BreakWorkStatus>(
      `${BASE}/${encodeURIComponent(id)}/breaks/${encodeURIComponent(breakId)}/status`,
      { status },
    ),
  /** Lien direct (téléchargement par le navigateur, `Content-Disposition: attachment`). */
  csvUrl: (id: string) => `${BASE}/${encodeURIComponent(id)}/breaks.csv`,
};
