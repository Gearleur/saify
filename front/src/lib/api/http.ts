import type { ErreurApi } from "@/types/api";

/** Erreur du contrat `{"erreur": {"code", "message", "details"}}`, avec `Retry-After` pour un 429. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  /** Secondes à attendre (429), lues dans l'en-tête `Retry-After`. */
  readonly retryAfter: number | null;
  /** Instant de l'erreur : sert de clé pour réinitialiser un compte à rebours. */
  readonly at = Date.now();

  constructor(
    status: number,
    code: string,
    message: string,
    details?: unknown,
    retryAfter?: number | null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.retryAfter = retryAfter ?? null;
  }
}

function estErreurApi(corps: unknown): corps is ErreurApi {
  return typeof corps === "object" && corps !== null && "erreur" in corps;
}

function lireRetryAfter(res: Response): number | null {
  const brut = res.headers.get("Retry-After");
  if (!brut || !/^\d+$/.test(brut.trim())) return null;
  return Number.parseInt(brut, 10);
}

/** Transforme une réponse en échec en `ApiError`, quel que soit son corps. */
export async function toApiError(res: Response): Promise<ApiError> {
  let corps: unknown = null;
  try {
    corps = await res.json();
  } catch {
    /* corps vide ou non JSON */
  }
  if (estErreurApi(corps)) {
    const { code, message, details } = corps.erreur;
    return new ApiError(res.status, code, message, details, lireRetryAfter(res));
  }
  return new ApiError(
    res.status,
    `HTTP_${res.status}`,
    `Réponse inattendue du serveur (${res.status}).`,
    null,
    lireRetryAfter(res),
  );
}

export const RESEAU = "RESEAU";

/** `fetch` vers l'API : en-têtes JSON, erreurs réseau et HTTP converties en `ApiError`. */
export async function send(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<Response> {
  const { json, headers, ...reste } = init;
  const entetes = new Headers(headers);
  if (!entetes.has("Accept")) entetes.set("Accept", "application/json");
  let body = reste.body;
  if (json !== undefined) {
    entetes.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }
  let res: Response;
  try {
    res = await fetch(path, { ...reste, headers: entetes, body });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, RESEAU, "Serveur injoignable. Vérifiez que l'API est lancée.");
  }
  if (!res.ok) throw await toApiError(res);
  return res;
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await send(path, { signal });
  return (await res.json()) as T;
}

export async function postJson<T>(path: string, json?: unknown): Promise<T> {
  const res = await send(path, { method: "POST", json });
  return (await res.json()) as T;
}

export async function putJson<T>(path: string, json: unknown): Promise<T> {
  const res = await send(path, { method: "PUT", json });
  return (await res.json()) as T;
}
