import { Play } from "lucide-react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { useRunExample } from "./useRunExample";

export function RunExampleButton({ variant = "default" }: { variant?: ButtonProps["variant"] }) {
  const { run, label, busy } = useRunExample();
  return (
    <Button variant={variant} onClick={run} disabled={busy}>
      <Play />
      {busy ? "Rapprochement en cours…" : label}
    </Button>
  );
}
