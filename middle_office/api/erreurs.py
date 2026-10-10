"""Erreurs de l'API : un seul format `{"erreur": {"code", "message", "details"}}`, jamais de trace."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("middle_office.api.erreurs")

CODES_HTTP = {404: "INTROUVABLE", 405: "METHODE_NON_AUTORISEE"}
ERREUR_INTERNE = (
    500,
    "ERREUR_INTERNE",
    "Erreur interne : réessayer, puis transmettre l'identifiant de requête (X-Request-ID)",
)


class ErreurApi(Exception):
    """Erreur prévue, levée par les services ou les routes, traduite telle quelle en réponse HTTP."""

    def __init__(self, statut: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.statut, self.code, self.message, self.details = statut, code, message, details


def reponse_erreur(statut: int, code: str, message: str, details: Any = None,
                   en_tetes: dict[str, str] | None = None) -> JSONResponse:  # fmt: skip
    corps = {"erreur": {"code": code, "message": message, "details": details}}
    return JSONResponse(corps, status_code=statut, headers=en_tetes)


def enregistrer_gestionnaires(app: FastAPI) -> None:
    @app.exception_handler(ErreurApi)
    def _erreur_api(_request: Request, exc: ErreurApi) -> JSONResponse:
        return reponse_erreur(exc.statut, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Sans l'« input » de pydantic : il recopierait le contenu des fichiers déposés.
        details = [
            {"champ": ".".join(str(x) for x in e["loc"]), "message": e["msg"]} for e in exc.errors()
        ]
        return reponse_erreur(422, "VALIDATION", "Requête invalide : voir details", details)

    @app.exception_handler(StarletteHTTPException)
    def _http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = CODES_HTTP.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = "Ressource introuvable" if exc.status_code == 404 else str(exc.detail)
        return reponse_erreur(exc.status_code, code, message, None, exc.headers)

    @app.exception_handler(Exception)
    def _interne(request: Request, exc: Exception) -> JSONResponse:
        log.error("erreur interne %s %s", request.method, request.url.path, exc_info=exc)
        return reponse_erreur(*ERREUR_INTERNE)
