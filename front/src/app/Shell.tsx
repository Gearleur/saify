import { useEffect, useState } from "react";
import { DropOverlay } from "@/features/files/DropOverlay";
import { SuspensSheet } from "@/features/suspens/SuspensSheet";
import { useSuspensSheet } from "@/features/suspens/useSuspensSheet";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useHotkeys } from "@/hooks/useHotkeys";
import { useReconciliation } from "@/hooks/useReconciliation";
import { cn } from "@/lib/utils";
import { CommandPalette } from "./CommandPalette";
import { routeDef } from "./routes";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/** Coquille : barre latérale, barre du haut, vue courante, fiche ancrée à droite, palette. */
export function Shell() {
  const { route } = useHashRoute();
  const { courant } = useReconciliation();
  const sheet = useSuspensSheet();
  const [palette, setPalette] = useState(false);
  const [tiroir, setTiroir] = useState(false);
  const { View, title } = routeDef(route.id);

  useHotkeys({ "mod+k": (e) => (e.preventDefault(), setPalette((p) => !p)) });
  useHotkeys({ Escape: () => setTiroir(false) }, tiroir);
  useEffect(() => {
    document.title = `${title} · Orsay Gestion`;
  }, [title]);
  const { close } = sheet;
  useEffect(() => close(), [courant?.id, close]);
  const ficheOuverte = !!sheet.openId && (route.id === "a-traiter" || route.id === "suspens");

  return (
    <div className="flex min-h-screen">
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-sidebar shrink-0 border-r border-border transition-transform duration-150 min-[900px]:sticky min-[900px]:top-0 min-[900px]:h-screen min-[900px]:translate-x-0",
          tiroir ? "translate-x-0 shadow-pop" : "-translate-x-full",
        )}
      >
        <Sidebar onSearch={() => setPalette(true)} onNavigate={() => setTiroir(false)} />
      </div>
      {tiroir && (
        <div
          className="fixed inset-0 z-30 bg-foreground/10 min-[900px]:hidden"
          onClick={() => setTiroir(false)}
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenu={() => setTiroir(true)} />
        <main className="mx-auto w-full max-w-[1320px] flex-1 px-4 pb-16 pt-6 md:px-6">
          <View key={route.id} />
        </main>
      </div>
      {ficheOuverte && <SuspensSheet />}
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
      <DropOverlay />
    </div>
  );
}
