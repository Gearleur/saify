"""Encadrement de l'usage de la clé API Anthropic : le seul endroit du code qui appelle le LLM.

- La clé est lue dans l'environnement (ou `.env`) par le SDK ; elle n'est ni journalisée ni renvoyée.
- Modèle imposé (Haiku 5.5) : personne ne peut choisir un modèle plus cher via la requête.
- Budget d'appels par jour, appels simultanés bornés, timeout court, une seule nouvelle tentative.
- Cache des questions identiques : une même question ne consomme la clé qu'une fois.
- Interrupteur `LLM_ENABLED=0` : coupe le LLM sans redéployer (les tests l'utilisent).
Toute limite atteinte lève `LLMIndisponible` : le domaine se replie sur les mots-clés, sans erreur
pour l'utilisateur et sans consommer la clé. Compteurs en mémoire : remis à zéro au redémarrage.
"""

import json
import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import date
from types import SimpleNamespace

import anthropic

from middle_office.domain.questions.understanding import MODEL, LlmUnavailable

log = logging.getLogger("middle_office.api.llm")


class GuardedClient:
    """Imite `client.messages.parse` du SDK, en appliquant les garde-fous avant chaque appel réel."""

    def __init__(self, client, daily_budget: int, concurrency: int, cache_max: int = 256):
        """Le timeout et la nouvelle tentative sont réglés sur le client du SDK (voir plus bas)."""
        self._client = client
        self.daily_budget, self.cache_max = daily_budget, cache_max
        self._slots = threading.BoundedSemaphore(concurrency)
        self._lock = threading.Lock()
        self._day, self._calls = date.today(), 0
        self._cache: OrderedDict[str, object] = OrderedDict()
        self.messages = SimpleNamespace(parse=self._parse)

    @property
    def calls_today(self) -> int:
        with self._lock:
            return self._calls if self._day == date.today() else 0

    def _reserve(self) -> None:
        with self._lock:
            if self._day != date.today():
                self._day, self._calls = date.today(), 0
            if self._calls >= self.daily_budget:
                raise LlmUnavailable(f"budget quotidien de {self.daily_budget} appels atteint")
            self._calls += 1

    def _parse(self, **query):
        if query.get("model") != MODEL:
            raise LlmUnavailable(
                f"modèle « {query.get('model')} » refusé, seul {MODEL} est autorisé"
            )
        key = json.dumps(
            [query.get("system"), query.get("messages")], sort_keys=True, ensure_ascii=False
        )
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        if not self._slots.acquire(blocking=False):
            raise LlmUnavailable("trop de questions simultanées")
        try:
            self._reserve()
            start = time.perf_counter()
            answer = self._client.messages.parse(**query)
            usage = getattr(answer, "usage", None)
            # Consommation tracée (jetons, durée, compteur du jour) ; jamais la clé ni le texte de la question.
            log.info(
                "llm appel modele=%s entree=%s sortie=%s duree=%.0fms appels_jour=%d/%d",
                MODEL,
                getattr(usage, "input_tokens", "?"),
                getattr(usage, "output_tokens", "?"),
                (time.perf_counter() - start) * 1000,
                self.calls_today,
                self.daily_budget,
            )
        finally:
            self._slots.release()
        if getattr(answer, "parsed_output", None) is not None:
            with self._lock:
                self._cache[key] = answer
                while len(self._cache) > self.cache_max:
                    self._cache.popitem(last=False)
        return answer


def client_from_environment(
    daily_budget: int, concurrency: int, timeout: float
) -> GuardedClient | None:
    """None si le LLM est coupé (`LLM_ENABLED=0`) ou si aucune clé n'est configurée."""
    if os.environ.get("LLM_ENABLED", "1") == "0":
        log.info("llm coupé par LLM_ENABLED=0 : compréhension par mots-clés")
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.info("llm : aucune clé configurée, compréhension par mots-clés")
        return None
    sdk = anthropic.Anthropic(timeout=timeout, max_retries=1)
    return GuardedClient(sdk, daily_budget, concurrency)
