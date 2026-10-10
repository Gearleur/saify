# Test technique Saify : agents IA pour la finance

Projet vide, prêt à recevoir le cas client. Python 3.12 géré par uv ; FastAPI, SDK Anthropic, LangGraph disponibles (aucun framework d'agents n'est imposé).

## Commandes
- Tests : `uv run pytest -q` · Lint : `uv run ruff check .` · Format : `uv run ruff format .`
- API (quand elle existera) : `uv run uvicorn <module>:app --reload`
- Clé API : `ANTHROPIC_API_KEY` dans `.env` (déjà ignoré par git, ne jamais l'afficher).

## Structure
- `data/` fichiers du cas client · `docs/CONSIGNE.md` la consigne · `docs/adr/` décisions (modèle `0000-template.md`)
- `CONTEXT.md` langage du domaine (glossaire finance, à enrichir avec le cas) · `NOTES.md` choix au fil de l'eau
- Code à créer en `src/` (ou le dossier le plus simple pour le cas), tests en `tests/`.

## Règles
- Aligner avant de coder (`/grill`). Tests avant de déclarer fini ; ne jamais annoncer « ça marche » sans avoir vu la sortie.
- Argent = `Decimal`, jamais `float`. Pas de secret dans le code ni dans git. Aucune donnée réelle.
- Rester simple : version minimale de bout en bout d'abord. Demander avant d'ajouter une dépendance.
- Le LLM ne décide que de l'ambigu ; sa sortie est validée (pydantic), justifiée et tracée. Sous un seuil de confiance : revue humaine.
- Mettre à jour CONTEXT.md et les ADR quand le vocabulaire ou une décision change. Commit court à chaque étape verte.
