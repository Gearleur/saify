import { useCallback } from "react";
import { useToast } from "./useToast";

/** Copie dans le presse-papiers, avec un toast qui dit ce qui a été copié. */
export function useCopy() {
  const { toast } = useToast();
  return useCallback(
    async (text: string, subject: string) => {
      try {
        await navigator.clipboard.writeText(text);
        toast({ title: `${subject} copié`, description: "Prêt à coller dans un mail." });
      } catch {
        toast({
          title: "Copie impossible",
          description: "Sélectionnez le texte et copiez-le à la main.",
          tone: "amber",
        });
      }
    },
    [toast],
  );
}
