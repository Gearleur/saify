"""Assemblage de l'application : réglages, services, gestionnaires d'erreurs, routes, middleware."""

from dataclasses import fields

from fastapi import FastAPI

from reco.api.config import VERSION, Reglages, configurer_logs
from reco.api.erreurs import enregistrer_gestionnaires
from reco.api.limiteur import Limiteur
from reco.api.middleware import Garde
from reco.api.routes import questions, rapprochements, systeme, web
from reco.api.services.historique import Historique


def create_app(**surcharges) -> FastAPI:
    """`surcharges` : champs de `Reglages` à remplacer (tests), ex. `create_app(limite_post=2)`."""
    inconnus = surcharges.keys() - {f.name for f in fields(Reglages)}
    if inconnus:
        raise TypeError(f"réglage(s) inconnu(s) : {', '.join(sorted(inconnus))}")
    reglages = Reglages(**surcharges)
    configurer_logs()

    # Swagger désactivé : incompatible avec la CSP stricte (scripts et styles externes).
    app = FastAPI(title="Rapprochement Orsay Gestion", version=VERSION,
                  docs_url=None, redoc_url=None, openapi_url=None)  # fmt: skip
    app.state.reglages = reglages
    app.state.historique = Historique(reglages.historique_max)

    enregistrer_gestionnaires(app)
    for module in (systeme, rapprochements, questions, web):
        app.include_router(module.router)
    app.mount(
        "/static", web.Statiques(directory=reglages.dossier_web, check_dir=False), name="static"
    )

    limiteurs = {
        "POST": Limiteur(reglages.limite_post, reglages.fenetre),
        "GET": Limiteur(reglages.limite_get, reglages.fenetre),
    }
    app.add_middleware(Garde, limiteurs=limiteurs, taille_corps_max=reglages.taille_corps_max)
    return app
