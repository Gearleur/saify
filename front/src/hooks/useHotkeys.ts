import { useEffect, useRef } from "react";

export type HotkeyMap = Record<string, (event: KeyboardEvent) => void>;

/** Vrai si la frappe vise un champ de saisie (les raccourcis à une touche s'effacent alors). */
export function isTyping(event: KeyboardEvent): boolean {
  const cible = event.target as HTMLElement | null;
  if (!cible) return false;
  return cible.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(cible.tagName);
}

/**
 * Raccourcis globaux. Clés : `ArrowDown`, `Enter`, `/`, `mod+k` (⌘ ou Ctrl).
 * Les touches simples sont ignorées pendant la saisie et quand un menu ou la palette est ouvert.
 */
export function useHotkeys(map: HotkeyMap, enabled = true) {
  const ref = useRef(map);
  useEffect(() => {
    ref.current = map;
  });
  useEffect(() => {
    if (!enabled) return;
    const surTouche = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      const cle = mod ? `mod+${e.key.toLowerCase()}` : e.key;
      const action = ref.current[cle];
      if (!action) return;
      if (!mod && (isTyping(e) || document.querySelector("[role=menu],[cmdk-root][data-open]")))
        return;
      action(e);
    };
    window.addEventListener("keydown", surTouche);
    return () => window.removeEventListener("keydown", surTouche);
  }, [enabled]);
}
