import { useSyncExternalStore } from "react";
import {
  getResolvedTheme,
  getThemePreference,
  setThemePreference,
  subscribeTheme,
} from "@/lib/theme";

/** Préférence de thème (clair, sombre, système) et thème effectivement appliqué. */
export function useTheme() {
  const preference = useSyncExternalStore(subscribeTheme, getThemePreference);
  const resolved = useSyncExternalStore(subscribeTheme, getResolvedTheme);
  return { preference, resolved, setPreference: setThemePreference };
}
