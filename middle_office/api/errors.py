"""Erreurs de l'API : un seul format `{"erreur": {"code", "message", "details"}}`, jamais de trace."""

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("middle_office.api.erreurs")

HTTP_CODES = {404: "INTROUVABLE", 405: "METHODE_NON_AUTORISEE"}
INTERNAL_ERROR = (
    500,
    "ERREUR_INTERNE",
    "Erreur interne : réessayer, puis transmettre l'identifiant de requête (X-Request-ID)",
)


class ApiError(Exception):
    """Erreur prévue, levée par les services ou les routes, traduite telle quelle en réponse HTTP."""

    def __init__(self, status: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def error_response(
    status: int,
    code: str,
    message: str,
    details: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details}}
    return JSONResponse(body, status_code=status, headers=headers)


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Sans l'« input » de pydantic : il recopierait le contenu des fichiers déposés.
        details = [
            {"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]} for e in exc.errors()
        ]
        return error_response(422, "VALIDATION", "Requête invalide : voir details", details)

    @app.exception_handler(StarletteHTTPException)
    def _http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = "Ressource introuvable" if exc.status_code == 404 else str(exc.detail)
        return error_response(exc.status_code, code, message, None, exc.headers)

    @app.exception_handler(Exception)
    def _internal(request: Request, exc: Exception) -> JSONResponse:
        log.error("erreur interne %s %s", request.method, request.url.path, exc_info=exc)
        return error_response(*INTERNAL_ERROR)
