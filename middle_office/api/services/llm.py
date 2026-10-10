"""Encadrement de l'usage de la clé API Anthropic : le seul endroit du code qui appelle le LLM.

- La clé est lue dans l'environnement (ou `.env`) par le SDK ; elle n'est ni journalisée ni renvoyée.
- Modèle imposé (Haiku 5.5) : personne ne peut choisir un modèle plus cher via la requête.
- Budget d'appels par jour, appels simultanés bornés, timeout court, une seule nouvelle tentative.
- Cache des questions identiques : une même question ne consomme la clé qu'une fois.
- Interrupteur `RECO_LLM_ACTIF=0` : coupe le LLM sans redéployer (les tests l'utilisent).
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

from middle_office.domaine.questions.comprehension import MODELE, LLMIndisponible

log = logging.getLogger("middle_office.api.llm")


class ClientEncadre:
    """Imite `client.messages.parse` du SDK, en appliquant les garde-fous avant chaque appel réel."""

    def __init__(
        self, client, budget_jour: int, concurrence: int, timeout: float, cache_max: int = 256
    ):
        self._client = client
        self.budget_jour, self.timeout, self.cache_max = budget_jour, timeout, cache_max
        self._places = threading.BoundedSemaphore(concurrence)
        self._verrou = threading.Lock()
        self._jour, self._appels = date.today(), 0
        self._cache: OrderedDict[str, object] = OrderedDict()
        self.messages = SimpleNamespace(parse=self._parse)

    @property
    def appels_aujourdhui(self) -> int:
        with self._verrou:
            return self._appels if self._jour == date.today() else 0

    def _reserver(self) -> None:
        with self._verrou:
            if self._jour != date.today():
                self._jour, self._appels = date.today(), 0
            if self._appels >= self.budget_jour:
                raise LLMIndisponible(f"budget quotidien de {self.budget_jour} appels atteint")
            self._appels += 1

    def _parse(self, **requete):
        if requete.get("model") != MODELE:
            raise LLMIndisponible(
                f"modèle « {requete.get('model')} » refusé, seul {MODELE} est autorisé"
            )
        cle = json.dumps(
            [requete.get("system"), requete.get("messages")], sort_keys=True, ensure_ascii=False
        )
        with self._verrou:
            if cle in self._cache:
                self._cache.move_to_end(cle)
                return self._cache[cle]
        if not self._places.acquire(blocking=False):
            raise LLMIndisponible("trop de questions simultanées")
        try:
            self._reserver()
            debut = time.perf_counter()
            reponse = self._client.messages.parse(**requete)
            usage = getattr(reponse, "usage", None)
            # Consommation tracée (jetons, durée, compteur du jour) ; jamais la clé ni le texte de la question.
            log.info("llm appel modele=%s entree=%s sortie=%s duree=%.0fms appels_jour=%d/%d", MODELE,
                     getattr(usage, "input_tokens", "?"), getattr(usage, "output_tokens", "?"),
                     (time.perf_counter() - debut) * 1000, self.appels_aujourdhui, self.budget_jour)  # fmt: skip
        finally:
            self._places.release()
        if getattr(reponse, "parsed_output", None) is not None:
            with self._verrou:
                self._cache[cle] = reponse
                while len(self._cache) > self.cache_max:
                    self._cache.popitem(last=False)
        return reponse


def client_depuis_environnement(
    budget_jour: int, concurrence: int, timeout: float
) -> ClientEncadre | None:
    """None si le LLM est coupé (`RECO_LLM_ACTIF=0`) ou si aucune clé n'est configurée."""
    if os.environ.get("RECO_LLM_ACTIF", "1") == "0":
        log.info("llm coupé par RECO_LLM_ACTIF=0 : compréhension par mots-clés")
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.info("llm : aucune clé configurée, compréhension par mots-clés")
        return None
    sdk = anthropic.Anthropic(timeout=timeout, max_retries=1)
    return ClientEncadre(sdk, budget_jour, concurrence, timeout)
