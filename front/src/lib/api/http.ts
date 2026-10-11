import type { ErrorBody } from "@/types/api";

/** Erreur du contrat `{"error": {"code", "message", "details"}}`, avec `Retry-After` pour un 429. */
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

function isErrorBody(body: unknown): body is ErrorBody {
  return typeof body === "object" && body !== null && "error" in body;
}

function readRetryAfter(res: Response): number | null {
  const raw = res.headers.get("Retry-After");
  if (!raw || !/^\d+$/.test(raw.trim())) return null;
  return Number.parseInt(raw, 10);
}

/** Transforme une réponse en échec en `ApiError`, quel que soit son corps. */
export async function toApiError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* corps vide ou non JSON */
  }
  if (isErrorBody(body)) {
    const { code, message, details } = body.error;
    return new ApiError(res.status, code, message, details, readRetryAfter(res));
  }
  return new ApiError(
    res.status,
    `HTTP_${res.status}`,
    `Réponse inattendue du serveur (${res.status}).`,
    null,
    readRetryAfter(res),
  );
}

export const NETWORK = "NETWORK";

/** `fetch` vers l'API : en-têtes JSON, erreurs réseau et HTTP converties en `ApiError`. */
export async function send(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<Response> {
  const { json, headers, ...rest } = init;
  const requestHeaders = new Headers(headers);
  if (!requestHeaders.has("Accept")) requestHeaders.set("Accept", "application/json");
  let body = rest.body;
  if (json !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }
  let res: Response;
  try {
    res = await fetch(path, { ...rest, headers: requestHeaders, body });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, NETWORK, "Serveur injoignable. Vérifiez que l'API est lancée.");
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
