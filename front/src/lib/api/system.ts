import type { ClientConfig, Health } from "@/types/api";
import { getJson } from "./http";

export const systemApi = {
  health: (signal?: AbortSignal) => getJson<Health>("/api/health", signal),
  clientConfig: (signal?: AbortSignal) => getJson<ClientConfig>("/api/client-config", signal),
};
