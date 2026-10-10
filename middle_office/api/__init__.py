"""API HTTP du rapprochement (contrat : docs/API.md). Lancement : uv run uvicorn middle_office.api:app --reload

Organisation :
- config.py      réglages (limites, dossiers) et en-têtes de sécurité
- schemas.py     modèles pydantic d'entrée et de sortie
- erreurs.py     format d'erreur unique et gestionnaires
- limiteur.py    rate limit par IP ; middleware.py : garde (request id, limites, en-têtes, logs)
- services/      logique applicative (dépôt, exécution, historique, référentiel), sans HTTP
- routes/        un routeur par domaine fonctionnel
- app.py         assemblage (create_app)
"""

from middle_office.api.app import create_app

app = create_app()

__all__ = ["app", "create_app"]
