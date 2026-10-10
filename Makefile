# Commandes du projet. Prérequis : uv (https://docs.astral.sh/uv/) ; Node 20+ seulement pour modifier le front.
PORT ?= 8000
API_URL ?= http://127.0.0.1:$(PORT)

.PHONY: install test lint format run back cli check front-install front-dev front-build front-check

install:        ## Python 3.12 et dépendances verrouillées (uv.lock)
	uv sync --locked

test:           ## Tests (le LLM est coupé, aucun appel réseau)
	uv run pytest -q

lint:           ## Lint et format, sans rien modifier
	uv run ruff check .
	uv run ruff format --check .

format:         ## Formate le code Python
	uv run ruff format .

run:            ## Application complète sur http://127.0.0.1:$(PORT) (API + front déjà buildé)
	uv run uvicorn middle_office.api:app --reload --port $(PORT)

back:           ## API seule, pour un front lancé à part (make front-dev)
	uv run uvicorn middle_office.api:app --reload --port $(PORT)

cli:            ## Rapprochement des fichiers du 25/09 en ligne de commande
	uv run python -m middle_office data/donnees

check: lint test ## Tout ce que vérifie la CI côté Python

front-install:  ## Dépendances du front (package-lock.json)
	cd front && npm ci

front-dev:      ## Front en développement sur http://localhost:5173, /api relayé vers $(API_URL)
	cd front && API_URL=$(API_URL) npm run dev

front-build:    ## Rebuild du front dans middle_office/web (à commiter)
	cd front && npm run build

front-check:    ## Lint et typage du front
	cd front && npm run lint && npm run typecheck
