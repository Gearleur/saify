import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ReconciliationContext, type LoadingState } from "@/hooks/useReconciliation";
import { ApiError, reconciliationsApi, systemApi } from "@/lib/api";
import { readJson, writeJson } from "@/lib/storage";
import type {
  UploadedFile,
  ClientConfig,
  Reconciliation,
  ReconciliationSummary,
  Health,
} from "@/types/api";

const LAST_KEY = "mo.rapprochement";

function asApiError(e: unknown): ApiError {
  return e instanceof ApiError ? e : new ApiError(0, "INCONNU", "Erreur inattendue.");
}

export function ReconciliationProvider({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<ApiError | null>(null);
  const [clientConfig, setClientConfig] = useState<ClientConfig | null>(null);
  const [clientConfigError, setClientConfigError] = useState<ApiError | null>(null);
  const [history, setHistory] = useState<ReconciliationSummary[]>([]);
  const [current, setCurrent] = useState<Reconciliation | null>(null);
  const [loading, setLoading] = useState<LoadingState>("startup");

  const refreshHealth = useCallback(() => {
    systemApi
      .health()
      .then((s) => (setHealth(s), setHealthError(null)))
      .catch((e: unknown) => setHealthError(asApiError(e)));
  }, []);

  const refreshHistory = useCallback(async () => {
    const list = await reconciliationsApi.list();
    setHistory(list);
    return list;
  }, []);

  const show = useCallback((r: Reconciliation) => {
    setCurrent(r);
    writeJson(LAST_KEY, r.id);
  }, []);

  useEffect(() => {
    refreshHealth();
    systemApi
      .clientConfig()
      .then(setClientConfig)
      .catch((e: unknown) => setClientConfigError(asApiError(e)));
    const latest = readJson<string | null>(LAST_KEY, null);
    reconciliationsApi
      .list()
      .then((list) => (setHistory(list), list))
      .then((list) =>
        latest && list.some((r) => r.id === latest) ? reconciliationsApi.read(latest) : null,
      )
      .then((r) => r && setCurrent(r))
      .catch(() => undefined)
      .finally(() => setLoading(null));
  }, [refreshHealth]);

  const runReconciliation = useCallback(
    async (state: LoadingState, call: () => Promise<Reconciliation>) => {
      setLoading(state);
      try {
        const r = await call();
        show(r);
        void refreshHistory().catch(() => undefined);
        return r;
      } catch (e) {
        throw asApiError(e);
      } finally {
        setLoading(null);
      }
    },
    [show, refreshHistory],
  );

  const runSample = useCallback(
    () => runReconciliation("sample", reconciliationsApi.sample),
    [runReconciliation],
  );
  const upload = useCallback(
    (files: UploadedFile[]) => runReconciliation("upload", () => reconciliationsApi.create(files)),
    [runReconciliation],
  );
  const openReconciliation = useCallback(
    async (id: string) => {
      await runReconciliation("read", () => reconciliationsApi.read(id));
    },
    [runReconciliation],
  );

  const value = useMemo(
    () => ({
      health,
      healthError,
      clientConfig,
      clientConfigError,
      history,
      current,
      loading,
      runSample,
      upload,
      openReconciliation,
      refreshHealth,
    }),
    [
      health,
      healthError,
      clientConfig,
      clientConfigError,
      history,
      current,
      loading,
      runSample,
      upload,
      openReconciliation,
      refreshHealth,
    ],
  );

  return <ReconciliationContext.Provider value={value}>{children}</ReconciliationContext.Provider>;
}
