import { useCallback } from "react";
import { ApiError } from "@/lib/api";
import { useToast } from "./useToast";

/** Erreur d'API en toast discret (avec le délai Retry-After d'un 429). */
export function useErrorToast() {
  const { toast } = useToast();
  return useCallback(
    (e: unknown) => {
      const err = e instanceof ApiError ? e : null;
      const attente = err?.retryAfter ? ` Réessayez dans ${err.retryAfter} s.` : "";
      toast({
        title: err?.message ?? "Erreur inattendue.",
        description: attente || undefined,
        tone: "amber",
      });
    },
    [toast],
  );
}
