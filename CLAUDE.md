# Test technique Saify : cas Orsay Gestion (middle office)

Rapprochement quotidien des positions titres (besoin 1) et questions sur la base de gestion (besoin 2). Python 3.12 géré par uv ; FastAPI, SDK Anthropic, LangGraph disponibles (aucun framework d'agents n'est imposé).

## Commandes
- Tout vérifier : `make check` (ruff, pyright, pytest) et `make front-check` (eslint, tsc, prettier, vitest)
- Application : `make run` (`uv run uvicorn middle_office.api:app --reload`) · CLI : `make cli`
- Front : `make front-install`, `make front-dev` (Vite + proxy), `make front-build` (à commiter), `make front-check`
- Clé API : `ANTHROPIC_API_KEY` dans `.env` (déjà ignoré par git, ne jamais l'afficher).

## Structure
- `middle_office/domaine/` métier pur, sans HTTP : `rapprochement/` (besoin 1), `questions/` (besoin 2)
- `middle_office/api/` HTTP (contrat : `docs/API.md`) · `middle_office/web/` build du front (généré, commité)
- `front/` sources React (architecture : `docs/FRONT.md`) · `tests/` tests Python (oracles calculés à la main)
- `data/donnees/` fichiers du client · `docs/adr/` décisions · `CONTEXT.md` glossaire · `NOTES.md` journal des choix
- `exploration/` analyse exploratoire des données (hors application)

## Règles
- Aligner avant de coder (`/grill`). Tests avant de déclarer fini ; ne jamais annoncer « ça marche » sans avoir vu la sortie.
- Argent = `Decimal`, jamais `float`. Pas de secret dans le code ni dans git. Aucune donnée réelle.
- Rester simple : version minimale de bout en bout d'abord. Demander avant d'ajouter une dépendance.
- Le LLM ne décide que de l'ambigu ; sa sortie est validée (pydantic), justifiée et tracée. Sous un seuil de confiance : revue humaine.
- Mettre à jour CONTEXT.md et les ADR quand le vocabulaire ou une décision change. Commit court à chaque étape verte.
