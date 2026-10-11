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
  const current = openId ?? cursor;

  const move = (delta: 1 | -1) => (e: KeyboardEvent) => {
    if (ids.length === 0) return;
    e.preventDefault();
    const i = current ? ids.indexOf(current) : -1;
    const next = ids[Math.min(ids.length - 1, Math.max(0, i === -1 ? 0 : i + delta))];
    if (!next) return;
    setCursor(next);
    if (openId) onOpen(next);
  };

  useHotkeys(
    {
      ArrowDown: move(1),
      ArrowUp: move(-1),
      Enter: (e) => {
        if (!cursor || openId === cursor) return;
        e.preventDefault();
        onOpen(cursor);
      },
    },
    enabled,
  );

  useEffect(() => {
    if (!current) return;
    document
      .querySelector(`[data-row-id="${CSS.escape(current)}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [current]);

  return { cursorId: current };
}
