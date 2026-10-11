import { useCallback, useMemo, useRef, useState, type ReactNode } from "react";
import { useHashRoute } from "@/hooks/useHashRoute";
import { useReconciliation } from "@/hooks/useReconciliation";
import { ApiError } from "@/lib/api";
import { checkFile, encodeFiles, EXTENSIONS, MAX_FILES } from "@/lib/files";
import { useAnnounceResult } from "./useAnnounceResult";
import { FileStagingContext, type StagedFile } from "./useFileStaging";

export function FileStagingProvider({ children }: { children: ReactNode }) {
  const { upload, loading } = useReconciliation();
  const { navigate } = useHashRoute();
  const announce = useAnnounceResult();
  const [staged, setStaged] = useState<StagedFile[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const add = useCallback((files: FileList | File[]) => {
    const added = Array.from(files).map((file) => ({ file, problem: checkFile(file) }));
    setStaged((l) => [
      ...l.filter((s) => !added.some((n) => n.file.name === s.file.name)),
      ...added,
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
    const files = staged.map((s) => s.file);
    if (files.length > MAX_FILES) {
      setError(new ApiError(0, "VALIDATION", `Au plus ${MAX_FILES} fichiers par rapprochement.`));
      return;
    }
    setError(null);
    try {
      const r = await upload(await encodeFiles(files));
      setStaged([]);
      announce(r);
      navigate("a-traiter");
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, "INCONNU", "Envoi impossible."));
    }
  }, [staged, upload, announce, navigate]);

  const value = useMemo(
    () => ({ staged, error, sending: loading === "upload", add, remove, clear, submit, pick }),
    [staged, error, loading, add, remove, clear, submit, pick],
  );

  return (
    <FileStagingContext.Provider value={value}>
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
