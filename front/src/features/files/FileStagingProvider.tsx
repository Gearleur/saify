import { useCallback, useMemo, useRef, useState, type ReactNode } from "react";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { ApiError } from "@/lib/api";
import { checkFile, encodeFiles, EXTENSIONS, NB_MAX } from "@/lib/files";
import { useAnnounceResult } from "./useAnnounceResult";
import { FileStagingContext, type StagedFile } from "./useFileStaging";

export function FileStagingProvider({ children }: { children: ReactNode }) {
  const { envoyer, chargement } = useReconciliation();
  const { navigate } = useHashRoute();
  const annoncer = useAnnounceResult();
  const [staged, setStaged] = useState<StagedFile[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const add = useCallback((files: FileList | File[]) => {
    const nouveaux = Array.from(files).map((file) => ({ file, probleme: checkFile(file) }));
    setStaged((l) => [
      ...l.filter((s) => !nouveaux.some((n) => n.file.name === s.file.name)),
      ...nouveaux,
    ]);
    setError(null);
  }, []);
  const remove = useCallback(
    (name: string) => setStaged((l) => l.filter((s) => s.file.name !== name)),
    [],
  );
  const clear = useCallback(() => (setStaged([]), setError(null)), []);
  const pick = useCallback(() => input.current?.click(), []);

  const submit = useCallback(async () => {
    const fichiers = staged.map((s) => s.file);
    if (fichiers.length > NB_MAX) {
      setError(new ApiError(0, "VALIDATION", `Au plus ${NB_MAX} fichiers par rapprochement.`));
      return;
    }
    setError(null);
    try {
      const r = await envoyer(await encodeFiles(fichiers));
      setStaged([]);
      annoncer(r);
      navigate("a-traiter");
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, "INCONNU", "Envoi impossible."));
    }
  }, [staged, envoyer, annoncer, navigate]);

  const valeur = useMemo(
    () => ({ staged, error, sending: chargement === "envoi", add, remove, clear, submit, pick }),
    [staged, error, chargement, add, remove, clear, submit, pick],
  );

  return (
    <FileStagingContext.Provider value={valeur}>
      {children}
      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept={EXTENSIONS.join(",")}
        aria-label="Choisir les fichiers du jour"
        onChange={(e) => {
          if (e.target.files) add(e.target.files);
          e.target.value = "";
        }}
      />
    </FileStagingContext.Provider>
  );
}
