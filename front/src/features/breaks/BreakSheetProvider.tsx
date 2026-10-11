import { useCallback, useMemo, useState, type ReactNode } from "react";
import { BreakSheetContext } from "./useBreakSheet";

export function BreakSheetProvider({ children }: { children: ReactNode }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [sequence, setSequence] = useState<string[]>([]);
  const open = useCallback((id: string, ids?: string[]) => {
    setOpenId(id);
    if (ids) setSequence(ids);
  }, []);
  const close = useCallback(() => setOpenId(null), []);
  const value = useMemo(() => ({ openId, sequence, open, close }), [openId, sequence, open, close]);
  return <BreakSheetContext.Provider value={value}>{children}</BreakSheetContext.Provider>;
}
