"""Assemblage de l'application : réglages, services, gestionnaires d'erreurs, routes, middleware."""

import os
from dataclasses import fields

from dotenv import load_dotenv
from fastapi import FastAPI

from middle_office.api.config import (
    ROOT,
    VERSION,
    Settings,
    configure_logging,
    expected_date_from,
)
from middle_office.api.errors import register_handlers
from middle_office.api.middleware import Guard
from middle_office.api.rate_limit import RateLimiter
from middle_office.api.routes import questions, reconciliations, system, web
from middle_office.api.services.history import History
from middle_office.api.services.llm import GuardedClient, client_from_environment

FROM_ENVIRONMENT = object()


def create_app(*, llm_client=FROM_ENVIRONMENT, **overrides) -> FastAPI:
    """`surcharges` : champs de `Reglages` à remplacer (tests), ex. `create_app(limite_post=2)`.
    `client_llm` : par défaut construit depuis l'environnement ; None le coupe ; un client fourni
    (tests) passe lui aussi par l'encadrement."""
    unknown = overrides.keys() - {f.name for f in fields(Settings)}
    if unknown:
        raise TypeError(f"réglage(s) inconnu(s) : {', '.join(sorted(unknown))}")
    # `.env` d'abord : il peut porter EXPECTED_AS_OF_DATE comme la clé (qui reste dans l'environnement
    # du process, jamais dans les réglages). Les variables déjà définies gardent la priorité.
    load_dotenv(ROOT.parent / ".env", override=False)
    if "expected_as_of_date" not in overrides:
        overrides["expected_as_of_date"] = expected_date_from(os.environ.get("EXPECTED_AS_OF_DATE"))
    settings = Settings(**overrides)
    file = settings.history_file
    if file is not None and file.resolve() == settings.db_path.resolve():
        raise ValueError("l'historique ne doit jamais être écrit dans orsay.db (lecture seule)")
    configure_logging()

    # Swagger désactivé : incompatible avec la CSP stricte (scripts et styles externes).
    app = FastAPI(
        title="Rapprochement Orsay Gestion",
        version=VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.history = History(settings.history_size, file)
    if llm_client is FROM_ENVIRONMENT:
        app.state.llm = client_from_environment(
            settings.llm_daily_budget, settings.llm_concurrency, settings.llm_timeout
        )
    else:
        app.state.llm = (
            None
            if llm_client is None
            else GuardedClient(llm_client, settings.llm_daily_budget, settings.llm_concurrency)
        )

    register_handlers(app)
    for module in (system, reconciliations, questions, web):
        app.include_router(module.router)
    app.mount(
        "/static",
        web.OptionalStaticFiles(directory=settings.web_dir, check_dir=False),
        name="static",
    )

    rate_limiters = {
        "POST": RateLimiter(settings.post_limit, settings.window),
        "GET": RateLimiter(settings.get_limit, settings.window),
        "PUT": RateLimiter(settings.put_limit, settings.window),
        "QUESTIONS": RateLimiter(settings.question_limit, settings.window),
    }
    app.add_middleware(Guard, rate_limiters=rate_limiters, max_body_size=settings.max_body_size)
    return app
