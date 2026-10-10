import { FileStack } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { RunExampleButton } from "./RunExampleButton";

/** État vide commun aux vues qui ont besoin d'un rapprochement. */
export function NoReconciliation({ what }: { what: string }) {
  return (
    <EmptyState
      icon={<FileStack />}
      title="Aucun rapprochement chargé"
      description={`Déposez les fichiers du jour ou lancez l'exemple pour voir ${what}.`}
      action={<RunExampleButton />}
    />
  );
}
