import { useRef } from "react";
import { useHotkeys } from "./useHotkeys";

/** `/` place le curseur dans le champ de recherche de la vue. */
export function useSlashFocus<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useHotkeys({
    "/": (e) => {
      e.preventDefault();
      ref.current?.focus();
    },
  });
  return ref;
}
