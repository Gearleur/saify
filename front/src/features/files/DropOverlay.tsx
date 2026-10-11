import { Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useFileStaging } from "./useFileStaging";

function carriesFiles(e: DragEvent): boolean {
  return Array.from(e.dataTransfer?.types ?? []).includes("Files");
}

/** Glisser-déposer n'importe où dans la page : les fichiers rejoignent la sélection du jour. */
export function DropOverlay() {
  const { add } = useFileStaging();
  const { navigate } = useHashRoute();
  const [visible, setVisible] = useState(false);
  const depth = useRef(0);

  useEffect(() => {
    const enter = (e: DragEvent) => {
      if (!carriesFiles(e)) return;
      e.preventDefault();
      depth.current += 1;
      setVisible(true);
    };
    const hover = (e: DragEvent) => carriesFiles(e) && e.preventDefault();
    const leave = () => {
      depth.current = Math.max(0, depth.current - 1);
      if (depth.current === 0) setVisible(false);
    };
    const drop = (e: DragEvent) => {
      if (!carriesFiles(e)) return;
      e.preventDefault();
      depth.current = 0;
      setVisible(false);
      if (e.dataTransfer?.files.length) {
        add(e.dataTransfer.files);
        navigate("a-traiter");
      }
    };
    window.addEventListener("dragenter", enter);
    window.addEventListener("dragover", hover);
    window.addEventListener("dragleave", leave);
    window.addEventListener("drop", drop);
    return () => {
      window.removeEventListener("dragenter", enter);
      window.removeEventListener("dragover", hover);
      window.removeEventListener("dragleave", leave);
      window.removeEventListener("drop", drop);
    };
  }, [add, navigate]);

  if (!visible) return null;
  return (
    <div className="pointer-events-none fixed inset-0 z-[70] flex items-center justify-center bg-background/80 animate-fade-in">
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-foreground/40 bg-background px-10 py-8 shadow-pop">
        <Upload className="size-5 text-muted-foreground" />
        <p className="font-medium">Déposez les fichiers du jour</p>
        <p className="text-sm text-muted-foreground">
          PMS et conservateurs A, B, C (.csv, .xlsx, .txt, .xml)
        </p>
      </div>
    </div>
  );
}
