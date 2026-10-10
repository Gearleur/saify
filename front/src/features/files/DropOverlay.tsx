import { Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useFileStaging } from "./useFileStaging";

function porteDesFichiers(e: DragEvent): boolean {
  return Array.from(e.dataTransfer?.types ?? []).includes("Files");
}

/** Glisser-déposer n'importe où dans la page : les fichiers rejoignent la sélection du jour. */
export function DropOverlay() {
  const { add } = useFileStaging();
  const { navigate } = useHashRoute();
  const [visible, setVisible] = useState(false);
  const profondeur = useRef(0);

  useEffect(() => {
    const entrer = (e: DragEvent) => {
      if (!porteDesFichiers(e)) return;
      e.preventDefault();
      profondeur.current += 1;
      setVisible(true);
    };
    const survoler = (e: DragEvent) => porteDesFichiers(e) && e.preventDefault();
    const sortir = () => {
      profondeur.current = Math.max(0, profondeur.current - 1);
      if (profondeur.current === 0) setVisible(false);
    };
    const deposer = (e: DragEvent) => {
      if (!porteDesFichiers(e)) return;
      e.preventDefault();
      profondeur.current = 0;
      setVisible(false);
      if (e.dataTransfer?.files.length) {
        add(e.dataTransfer.files);
        navigate("a-traiter");
      }
    };
    window.addEventListener("dragenter", entrer);
    window.addEventListener("dragover", survoler);
    window.addEventListener("dragleave", sortir);
    window.addEventListener("drop", deposer);
    return () => {
      window.removeEventListener("dragenter", entrer);
      window.removeEventListener("dragover", survoler);
      window.removeEventListener("dragleave", sortir);
      window.removeEventListener("drop", deposer);
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
