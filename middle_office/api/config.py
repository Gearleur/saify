"""Réglages de l'application et constantes HTTP (en-têtes de sécurité, extensions acceptées)."""

import logging
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from middle_office.domaine.rapprochement.calendrier import jour_ouvre_precedent

RACINE = Path(__file__).resolve().parents[1]


def _version() -> str:
    """Une seule source de vérité : pyproject.toml (le projet n'est pas installé comme paquet)."""
    try:
        return tomllib.loads((RACINE.parent / "pyproject.toml").read_text())["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "inconnue"


VERSION = _version()
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


AUTO = "auto"


def date_attendue_depuis(valeur: str | None) -> date | str | None:
    """`DATE_ARRETE_ATTENDUE` : vide, `auto` ou AAAA-MM-JJ. Une valeur invalide arrête le démarrage :
    mieux vaut un serveur qui refuse de partir qu'un contrôle de date silencieusement désactivé."""
    valeur = (valeur or "").strip().lower()
    if not valeur:
        return None
    if valeur == AUTO:
        return AUTO
    try:
        return date.fromisoformat(valeur)
    except ValueError:
        raise ValueError(
            f"DATE_ARRETE_ATTENDUE « {valeur} » : attendu vide, « auto » ou AAAA-MM-JJ"
        ) from None


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
    # Date d'arrêté exigée des fichiers : None (celle lue dans le PMS, pour la démo du 25/09), une date
    # fixe, ou AUTO (J-1 ouvré TARGET2, recalculé à chaque dépôt). Variable DATE_ARRETE_ATTENDUE.
    date_arrete_attendue: date | str | None = None

    def date_attendue(self, aujourdhui: date | None = None) -> date | None:
        if self.date_arrete_attendue == AUTO:
            return jour_ouvre_precedent(aujourdhui or date.today())
        assert not isinstance(self.date_arrete_attendue, str), self.date_arrete_attendue
        return self.date_arrete_attendue

    @property
    def parametrage(self) -> Path:
        return self.dossier_donnees / "parametrage.xlsx"

    @property
    def base(self) -> Path:
        return self.dossier_donnees / "orsay.db"


def configurer_logs() -> logging.Logger:
    """Logger `middle_office.api` (parent de tous les modules de l'API). uvicorn ne configure que les siens."""
    log = logging.getLogger("middle_office.api")
    if not log.handlers:
        sortie = logging.StreamHandler()
        sortie.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        log.addHandler(sortie)
        log.setLevel(logging.INFO)
    return log
