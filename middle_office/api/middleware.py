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

from middle_office.api.config import MB, SECURITY_HEADERS
from middle_office.api.errors import INTERNAL_ERROR, error_response
from middle_office.api.rate_limit import RateLimiter

log = logging.getLogger("middle_office.api.acces")


def request_id(provided: str | None) -> str:
    """Repris tel quel seulement s'il est sûr à journaliser (pas d'injection de lignes)."""
    if provided and re.fullmatch(r"[A-Za-z0-9._-]{1,64}", provided):
        return provided
    return uuid.uuid4().hex


class Guard:
    def __init__(self, app, rate_limiters: dict[str, RateLimiter], max_body_size: int):
        self.app, self.rate_limiters, self.max_body_size = app, rate_limiters, max_body_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        start = time.perf_counter()
        rid = request_id(Headers(scope=scope).get("x-request-id"))
        scope.setdefault("state", {})["request_id"] = rid  # lu par les routes (request.state)
        state = {"status": 500, "started": False}

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                state["status"], state["started"] = message["status"], True
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = rid
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
            await send(message)

        try:
            refusal = self._rate_limit(scope) or self._declared_too_large(scope)
            if refusal is None:
                receive, refusal = await self._read_body(scope, receive)
            await (refusal or self.app)(scope, receive, send_with_headers)
        except Exception:
            log.exception("rid=%s erreur interne", rid)
            if not state["started"]:
                await error_response(*INTERNAL_ERROR)(scope, receive, send_with_headers)
        finally:
            log.info(
                "rid=%s %s %s %s %.1fms",
                rid,
                scope["method"],
                scope["path"],
                state["status"],
                (time.perf_counter() - start) * 1000,
            )

    def _rate_limit(self, scope) -> JSONResponse | None:
        # Quotas séparés : trier ses suspens (PUT) ne doit pas consommer le quota des dépôts (POST).
        family = {"GET": "GET", "HEAD": "GET", "PUT": "PUT"}.get(scope["method"], "POST")
        if family == "POST" and scope["path"].startswith("/api/questions"):
            family = "QUESTIONS"  # quota à part : une question peut consommer la clé API
        ip = (scope.get("client") or ("inconnue",))[0]
        wait = self.rate_limiters[family].wait(ip)
        if not wait:
            return None
        seconds = max(1, math.ceil(wait))
        return error_response(
            429,
            "RATE_LIMIT",
            f"Trop de requêtes {family} : réessayer dans {seconds} s",
            {"retry_after": seconds},
            {"Retry-After": str(seconds)},
        )

    def _too_large(self) -> JSONResponse:
        limit = self.max_body_size
        readable = f"{limit // MB} Mo" if limit >= MB else f"{limit} octets"
        return error_response(413, "CORPS_TROP_GROS", f"Corps de requête limité à {readable}")

    def _declared_too_large(self, scope) -> JSONResponse | None:
        declared = Headers(scope=scope).get("content-length", "")
        if declared.isdigit() and int(declared) > self.max_body_size:
            return self._too_large()
        return None

    async def _read_body(self, scope, receive):
        """Lit le corps en comptant les octets réellement reçus (Content-Length peut mentir ou
        manquer), puis le rejoue à l'application."""
        if scope["method"] not in ("POST", "PUT", "PATCH"):
            return receive, None
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return receive, None  # client parti : l'application le constatera
            total += len(message.get("body", b""))
            if total > self.max_body_size:
                return receive, self._too_large()
            chunks.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        body, replayed = b"".join(chunks), False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return replay, None
