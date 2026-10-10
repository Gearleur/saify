"""Réglages de l'application et constantes HTTP (en-têtes de sécurité, extensions acceptées)."""

import logging
from dataclasses import dataclass
from pathlib import Path

VERSION = "0.3.0"
RACINE = Path(__file__).resolve().parents[1]
MO = 1024 * 1024
EXTENSIONS = (".csv", ".xlsx", ".txt", ".xml")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
    "frame-ancestors 'none'"
)
EN_TETES_SECURITE = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@dataclass(frozen=True)
class Reglages:
    """Tout ce qui varie entre la production et les tests, injecté dans `create_app`."""

    limite_post: int = 20  # requêtes par fenêtre et par IP
    limite_get: int = 120
    limite_questions: int = (
        10  # questions par fenêtre et par IP (chaque question peut coûter un appel LLM)
    )
    fenetre: float = 60.0  # secondes
    taille_corps_max: int = 15 * MO
    taille_fichier_max: int = 5 * MO
    dossier_web: Path = RACINE / "web"
    dossier_donnees: Path = RACINE.parent / "data" / "donnees"
    historique_max: int = 20  # nombre de rapprochements listés (et gardés, si en mémoire)
    # SQLite à part, hors git (positions du client) ; None : en mémoire, perdu au redémarrage.
    fichier_historique: Path | None = RACINE.parent / "var" / "historique.db"
    llm_budget_jour: int = 300  # appels LLM réels par jour, au-delà : mots-clés
    llm_concurrence: int = 4  # appels LLM simultanés
    llm_timeout: float = 10.0  # secondes, une seule nouvelle tentative

    @property
    def parametrage(self) -> Path:
        return self.dossier_donnees / "parametrage.xlsx"

    @property
    def base(self) -> Path:
        return self.dossier_donnees / "orsay.db"


def configurer_logs() -> logging.Logger:
    """Logger `reco.api` (parent de tous les modules de l'API). uvicorn ne configure que les siens."""
    log = logging.getLogger("reco.api")
    if not log.handlers:
        sortie = logging.StreamHandler()
        sortie.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        log.addHandler(sortie)
        log.setLevel(logging.INFO)
    return log
