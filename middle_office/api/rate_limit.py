"""Rate limit par IP, fenêtre glissante, en mémoire (process unique : non partagé entre workers)."""

import threading
import time
from collections import defaultdict, deque

MAX_TRACKED_IPS = 10_000


class RateLimiter:
    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def wait(self, key: str) -> float:
        """0 si l'appel est autorisé (et compté), sinon les secondes avant le prochain créneau."""
        with self._lock:
            now = time.monotonic()
            if len(self._calls) > MAX_TRACKED_IPS:
                self._forget_inactive(now)
            calls = self._calls[key]
            while calls and calls[0] <= now - self.window:
                calls.popleft()
            if len(calls) >= self.limit:
                return calls[0] + self.window - now
            calls.append(now)
            return 0.0

    def _forget_inactive(self, now: float) -> None:
        """La mémoire reste bornée même si beaucoup d'IP différentes passent."""
        for ip in [ip for ip, q in self._calls.items() if q[-1] <= now - self.window]:
            del self._calls[ip]
