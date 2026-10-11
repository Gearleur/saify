import { useEffect, useState } from "react";

/** Secondes restantes à partir d'une durée initiale (Retry-After) ; 0 une fois écoulée. */
export function useCountdown(seconds: number | null): number {
  const [end] = useState(() => (seconds ? Date.now() + seconds * 1000 : 0));
  const [remaining, setRemaining] = useState(seconds ?? 0);
  useEffect(() => {
    if (!end) return;
    const id = window.setInterval(() => {
      const r = Math.max(0, Math.ceil((end - Date.now()) / 1000));
      setRemaining(r);
      if (r === 0) window.clearInterval(id);
    }, 500);
    return () => window.clearInterval(id);
  }, [end]);
  return remaining;
}
