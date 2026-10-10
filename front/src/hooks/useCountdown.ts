import { useEffect, useState } from "react";

/** Secondes restantes à partir d'une durée initiale (Retry-After) ; 0 une fois écoulée. */
export function useCountdown(seconds: number | null): number {
  const [fin] = useState(() => (seconds ? Date.now() + seconds * 1000 : 0));
  const [restant, setRestant] = useState(seconds ?? 0);
  useEffect(() => {
    if (!fin) return;
    const id = window.setInterval(() => {
      const r = Math.max(0, Math.ceil((fin - Date.now()) / 1000));
      setRestant(r);
      if (r === 0) window.clearInterval(id);
    }, 500);
    return () => window.clearInterval(id);
  }, [fin]);
  return restant;
}
