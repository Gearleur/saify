import { useCallback, useMemo, useState, type ReactNode } from "react";
import { SuspensSheetContext } from "./useSuspensSheet";

export function SuspensSheetProvider({ children }: { children: ReactNode }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [sequence, setSequence] = useState<string[]>([]);
  const open = useCallback((id: string, ids?: string[]) => {
    setOpenId(id);
    if (ids) setSequence(ids);
  }, []);
  const close = useCallback(() => setOpenId(null), []);
  const valeur = useMemo(
    () => ({ openId, sequence, open, close }),
    [openId, sequence, open, close],
  );
  return <SuspensSheetContext.Provider value={valeur}>{children}</SuspensSheetContext.Provider>;
}
