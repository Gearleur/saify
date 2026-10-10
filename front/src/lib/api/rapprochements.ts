import type {
  FichierEnvoye,
  PointDeSituation,
  Rapprochement,
  RapprochementResume,
} from "@/types/api";
import { getJson, postJson } from "./http";

const BASE = "/api/rapprochements";

export const rapprochementsApi = {
  liste: (signal?: AbortSignal) => getJson<RapprochementResume[]>(BASE, signal),
  lire: (id: string, signal?: AbortSignal) =>
    getJson<Rapprochement>(`${BASE}/${encodeURIComponent(id)}`, signal),
  creer: (fichiers: FichierEnvoye[]) => postJson<Rapprochement>(BASE, { fichiers }),
  exemple: () => postJson<Rapprochement>(`${BASE}/exemple`),
  pointDeSituation: (id: string, signal?: AbortSignal) =>
    getJson<PointDeSituation>(`${BASE}/${encodeURIComponent(id)}/point-de-situation`, signal),
  /** Lien direct (téléchargement par le navigateur, `Content-Disposition: attachment`). */
  csvUrl: (id: string) => `${BASE}/${encodeURIComponent(id)}/suspens.csv`,
};
