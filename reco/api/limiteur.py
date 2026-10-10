"""Rate limit par IP, fenêtre glissante, en mémoire (process unique : non partagé entre workers)."""

import threading
import time
from collections import defaultdict, deque

MAX_IP_SUIVIES = 10_000


class Limiteur:
    def __init__(self, limite: int, fenetre: float):
        self.limite, self.fenetre = limite, fenetre
        self._appels: dict[str, deque[float]] = defaultdict(deque)
        self._verrou = threading.Lock()

    def attente(self, cle: str) -> float:
        """0 si l'appel est autorisé (et compté), sinon les secondes avant le prochain créneau."""
        with self._verrou:
            maintenant = time.monotonic()
            if len(self._appels) > MAX_IP_SUIVIES:
                self._oublier_inactives(maintenant)
            appels = self._appels[cle]
            while appels and appels[0] <= maintenant - self.fenetre:
                appels.popleft()
            if len(appels) >= self.limite:
                return appels[0] + self.fenetre - maintenant
            appels.append(maintenant)
            return 0.0

    def _oublier_inactives(self, maintenant: float) -> None:
        """La mémoire reste bornée même si beaucoup d'IP différentes passent."""
        for ip in [ip for ip, q in self._appels.items() if q[-1] <= maintenant - self.fenetre]:
            del self._appels[ip]
