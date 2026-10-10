"""Assemblage de l'application : réglages, services, gestionnaires d'erreurs, routes, middleware."""

from dataclasses import fields

from dotenv import load_dotenv
from fastapi import FastAPI

from middle_office.api.config import RACINE, VERSION, Reglages, configurer_logs
from middle_office.api.erreurs import enregistrer_gestionnaires
from middle_office.api.limiteur import Limiteur
from middle_office.api.middleware import Garde
from middle_office.api.routes import questions, rapprochements, systeme, web
from middle_office.api.services.historique import Historique
from middle_office.api.services.llm import ClientEncadre, client_depuis_environnement

DEPUIS_ENVIRONNEMENT = object()


def create_app(*, client_llm=DEPUIS_ENVIRONNEMENT, **surcharges) -> FastAPI:
    """`surcharges` : champs de `Reglages` à remplacer (tests), ex. `create_app(limite_post=2)`.
    `client_llm` : par défaut construit depuis l'environnement ; None le coupe ; un client fourni
    (tests) passe lui aussi par l'encadrement."""
    inconnus = surcharges.keys() - {f.name for f in fields(Reglages)}
    if inconnus:
        raise TypeError(f"réglage(s) inconnu(s) : {', '.join(sorted(inconnus))}")
    reglages = Reglages(**surcharges)
    fichier = reglages.fichier_historique
    if fichier is not None and fichier.resolve() == reglages.base.resolve():
        raise ValueError("l'historique ne doit jamais être écrit dans orsay.db (lecture seule)")
    configurer_logs()

    # Swagger désactivé : incompatible avec la CSP stricte (scripts et styles externes).
    app = FastAPI(title="Rapprochement Orsay Gestion", version=VERSION,
                  docs_url=None, redoc_url=None, openapi_url=None)  # fmt: skip
    app.state.reglages = reglages
    app.state.historique = Historique(reglages.historique_max, fichier)
    encadrement = (reglages.llm_budget_jour, reglages.llm_concurrence, reglages.llm_timeout)
    if client_llm is DEPUIS_ENVIRONNEMENT:
        load_dotenv(
            RACINE.parent / ".env", override=False
        )  # la clé reste dans l'environnement du process
        app.state.llm = client_depuis_environnement(*encadrement)
    else:
        app.state.llm = None if client_llm is None else ClientEncadre(client_llm, *encadrement)

    enregistrer_gestionnaires(app)
    for module in (systeme, rapprochements, questions, web):
        app.include_router(module.router)
    app.mount(
        "/static", web.Statiques(directory=reglages.dossier_web, check_dir=False), name="static"
    )

    limiteurs = {
        "POST": Limiteur(reglages.limite_post, reglages.fenetre),
        "GET": Limiteur(reglages.limite_get, reglages.fenetre),
        "QUESTIONS": Limiteur(reglages.limite_questions, reglages.fenetre),
    }
    app.add_middleware(Garde, limiteurs=limiteurs, taille_corps_max=reglages.taille_corps_max)
    return app
