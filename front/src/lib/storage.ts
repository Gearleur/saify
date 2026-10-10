/** `localStorage` sûr : navigation privée, quota ou accès refusé ne cassent jamais l'interface. */

export function readJson<T>(cle: string, defaut: T): T {
  try {
    const brut = window.localStorage.getItem(cle);
    return brut === null ? defaut : (JSON.parse(brut) as T);
  } catch {
    return defaut;
  }
}

export function writeJson(cle: string, valeur: unknown): void {
  try {
    window.localStorage.setItem(cle, JSON.stringify(valeur));
  } catch {
    /* stockage indisponible : l'état reste en mémoire pour la session */
  }
}
