import { Menu } from "lucide-react";
import { StatusLabel } from "@/components/StatusDot";
import { Button } from "@/components/ui/button";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { asOfLabel, formatTime } from "@/lib/dates";
import { routeDef } from "./routes";

/** Fil d'Ariane à gauche, état du rapprochement chargé à droite. */
export function Topbar({ onMenu }: { onMenu: () => void }) {
  const { route } = useHashRoute();
  const { current, loading } = useReconciliation();
  const def = routeDef(route.id);
  return (
    <header className="sticky top-0 z-30 flex h-bar shrink-0 items-center gap-3 border-b border-border bg-background/90 px-4 backdrop-blur md:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="min-[900px]:hidden"
        aria-label="Ouvrir la navigation"
        onClick={onMenu}
      >
        <Menu />
      </Button>
      <p className="flex min-w-0 items-center gap-1.5 text-sm">
        <span className="text-subtle">{def.section}</span>
        <span className="text-subtle">/</span>
        <span className="truncate font-medium">{def.title}</span>
      </p>
      <span className="ml-auto text-xs text-muted-foreground">
        {loading && loading !== "startup" ? (
          <StatusLabel tone="blue" pulse>
            Rapprochement en cours…
          </StatusLabel>
        ) : current ? (
          <StatusLabel tone={current.status === "BLOQUE" ? "red" : "green"}>
            {`${asOfLabel(current.as_of_date)}, ${current.status === "BLOQUE" ? "bloqué" : `${current.summary.break_count} suspens`}, lancé à ${formatTime(current.created_at)}`}
          </StatusLabel>
        ) : null}
      </span>
    </header>
  );
}
