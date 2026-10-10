import { useEffect, useState } from "react";
import { useHotkeys } from "./useHotkeys";

interface Options {
  ids: string[];
  /** Ligne ouverte dans la fiche : ↑ ↓ passent alors directement à la voisine. */
  openId: string | null;
  onOpen: (id: string) => void;
  enabled?: boolean;
}

/** ↑ ↓ déplacent le curseur dans une liste, Entrée ouvre la ligne ; la ligne reste visible à l'écran. */
export function useListNavigation({ ids, openId, onOpen, enabled = true }: Options) {
  const [cursor, setCursor] = useState<string | null>(null);
  const courant = openId ?? cursor;

  const deplacer = (pas: 1 | -1) => (e: KeyboardEvent) => {
    if (ids.length === 0) return;
    e.preventDefault();
    const i = courant ? ids.indexOf(courant) : -1;
    const suivant = ids[Math.min(ids.length - 1, Math.max(0, i === -1 ? 0 : i + pas))];
    if (!suivant) return;
    setCursor(suivant);
    if (openId) onOpen(suivant);
  };

  useHotkeys(
    {
      ArrowDown: deplacer(1),
      ArrowUp: deplacer(-1),
      Enter: (e) => {
        if (!cursor || openId === cursor) return;
        e.preventDefault();
        onOpen(cursor);
      },
    },
    enabled,
  );

  useEffect(() => {
    if (!courant) return;
    document
      .querySelector(`[data-row-id="${CSS.escape(courant)}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [courant]);

  return { cursorId: courant };
}
