"""Middleware ASGI de garde, le plus externe : tout passe par lui, y compris les erreurs internes.

Dans l'ordre : request id, rate limit, taille du corps, puis l'application ; en sortie, en-têtes de
sécurité et log d'accès. Un filet renvoie un 500 propre, pour que même une panne porte ses en-têtes.
"""

import logging
import math
import re
import time
import uuid

from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders

from reco.api.config import EN_TETES_SECURITE, MO
from reco.api.erreurs import ERREUR_INTERNE, reponse_erreur
from reco.api.limiteur import Limiteur

log = logging.getLogger("reco.api.acces")


def request_id(fourni: str | None) -> str:
    """Repris tel quel seulement s'il est sûr à journaliser (pas d'injection de lignes)."""
    if fourni and re.fullmatch(r"[A-Za-z0-9._-]{1,64}", fourni):
        return fourni
    return uuid.uuid4().hex


class Garde:
    def __init__(self, app, limiteurs: dict[str, Limiteur], taille_corps_max: int):
        self.app, self.limiteurs, self.taille_corps_max = app, limiteurs, taille_corps_max

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        debut = time.perf_counter()
        rid = request_id(Headers(scope=scope).get("x-request-id"))
        etat = {"statut": 500, "demarre": False}

        async def envoyer(message):
            if message["type"] == "http.response.start":
                etat["statut"], etat["demarre"] = message["status"], True
                en_tetes = MutableHeaders(scope=message)
                en_tetes["X-Request-ID"] = rid
                for nom, valeur in EN_TETES_SECURITE.items():
                    en_tetes[nom] = valeur
            await send(message)

        try:
            refus = self._limiter(scope) or self._annonce_trop_gros(scope)
            if refus is None:
                receive, refus = await self._lire_corps(scope, receive)
            await (refus or self.app)(scope, receive, envoyer)
        except Exception:
            log.exception("rid=%s erreur interne", rid)
            if not etat["demarre"]:
                await reponse_erreur(*ERREUR_INTERNE)(scope, receive, envoyer)
        finally:
            log.info("rid=%s %s %s %s %.1fms", rid, scope["method"], scope["path"],
                     etat["statut"], (time.perf_counter() - debut) * 1000)  # fmt: skip

    def _limiter(self, scope) -> JSONResponse | None:
        famille = "GET" if scope["method"] in ("GET", "HEAD") else "POST"
        if famille == "POST" and scope["path"].startswith("/api/questions"):
            famille = "QUESTIONS"  # quota à part : une question peut consommer la clé API
        ip = (scope.get("client") or ("inconnue",))[0]
        attente = self.limiteurs[famille].attente(ip)
        if not attente:
            return None
        secondes = max(1, math.ceil(attente))
        return reponse_erreur(429, "RATE_LIMIT", f"Trop de requêtes {famille} : réessayer dans {secondes} s",
                              {"retry_after": secondes}, {"Retry-After": str(secondes)})  # fmt: skip

    def _trop_gros(self) -> JSONResponse:
        limite = self.taille_corps_max
        lisible = f"{limite // MO} Mo" if limite >= MO else f"{limite} octets"
        return reponse_erreur(413, "CORPS_TROP_GROS", f"Corps de requête limité à {lisible}")

    def _annonce_trop_gros(self, scope) -> JSONResponse | None:
        annonce = Headers(scope=scope).get("content-length", "")
        if annonce.isdigit() and int(annonce) > self.taille_corps_max:
            return self._trop_gros()
        return None

    async def _lire_corps(self, scope, receive):
        """Lit le corps en comptant les octets réellement reçus (Content-Length peut mentir ou
        manquer), puis le rejoue à l'application."""
        if scope["method"] not in ("POST", "PUT", "PATCH"):
            return receive, None
        morceaux, total = [], 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return receive, None  # client parti : l'application le constatera
            total += len(message.get("body", b""))
            if total > self.taille_corps_max:
                return receive, self._trop_gros()
            morceaux.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        corps, rejoue = b"".join(morceaux), False

        async def rejouer():
            nonlocal rejoue
            if not rejoue:
                rejoue = True
                return {"type": "http.request", "body": corps, "more_body": False}
            return await receive()

        return rejouer, None
