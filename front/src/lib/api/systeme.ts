import type { Parametrage, Sante } from "@/types/api";
import { getJson } from "./http";

export const systemeApi = {
  sante: (signal?: AbortSignal) => getJson<Sante>("/api/sante", signal),
  parametrage: (signal?: AbortSignal) => getJson<Parametrage>("/api/parametrage", signal),
};
