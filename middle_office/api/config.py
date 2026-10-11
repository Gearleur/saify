"""Réglages de l'application et constantes HTTP (en-têtes de sécurité, extensions acceptées)."""

import logging
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from middle_office.domain.reconciliation.business_days import previous_business_day

ROOT = Path(__file__).resolve().parents[1]


def _version() -> str:
    """Une seule source de vérité : pyproject.toml (le projet n'est pas installé comme paquet)."""
    try:
        return tomllib.loads((ROOT.parent / "pyproject.toml").read_text())["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "inconnue"


VERSION = _version()
MB = 1024 * 1024
EXTENSIONS = (".csv", ".xlsx", ".txt", ".xml")

CSP = (
    # Tout est servi par l'application, polices comprises : aucune requête vers un tiers.
    "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; "
    "frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


AUTO = "auto"


def expected_date_from(value: str | None) -> date | str | None:
    """`EXPECTED_AS_OF_DATE` : vide, `auto` ou AAAA-MM-JJ. Une valeur invalide arrête le démarrage :
    mieux vaut un serveur qui refuse de partir qu'un contrôle de date silencieusement désactivé."""
    value = (value or "").strip().lower()
    if not value:
        return None
    if value == AUTO:
        return AUTO
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"EXPECTED_AS_OF_DATE « {value} » : attendu vide, « auto » ou AAAA-MM-JJ"
        ) from None


@dataclass(frozen=True)
class Settings:
    """Tout ce qui varie entre la production et les tests, injecté dans `create_app`."""

    post_limit: int = 20  # requêtes par fenêtre et par IP
    get_limit: int = 120
    put_limit: int = 120  # changements de statut de traitement
    question_limit: int = (
        10  # questions par fenêtre et par IP (chaque question peut coûter un appel LLM)
    )
    window: float = 60.0  # secondes
    max_body_size: int = 15 * MB
    max_file_size: int = 5 * MB
    web_dir: Path = ROOT / "web"
    data_dir: Path = ROOT.parent / "data" / "donnees"
    history_size: int = 20  # nombre de rapprochements listés (et gardés, si en mémoire)
    # SQLite à part, hors git (positions du client) ; None : en mémoire, perdu au redémarrage.
    history_file: Path | None = ROOT.parent / "var" / "history.db"
    llm_daily_budget: int = 300  # appels LLM réels par jour, au-delà : mots-clés
    llm_concurrency: int = 4  # appels LLM simultanés
    llm_timeout: float = 10.0  # secondes, une seule nouvelle tentative
    # Date d'arrêté exigée des fichiers : None (celle lue dans le PMS, pour la démo du 25/09), une date
    # fixe, ou AUTO (J-1 ouvré TARGET2, recalculé à chaque dépôt). Variable EXPECTED_AS_OF_DATE.
    expected_as_of_date: date | str | None = None

    def expected_date(self, today: date | None = None) -> date | None:
        if self.expected_as_of_date == AUTO:
            return previous_business_day(today or date.today())
        assert not isinstance(self.expected_as_of_date, str), self.expected_as_of_date
        return self.expected_as_of_date

    @property
    def client_config(self) -> Path:
        return self.data_dir / "parametrage.xlsx"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "orsay.db"


def configure_logging() -> logging.Logger:
    """Logger `middle_office.api` (parent de tous les modules de l'API). uvicorn ne configure que les siens."""
    log = logging.getLogger("middle_office.api")
    if not log.handlers:
        output = logging.StreamHandler()
        output.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        log.addHandler(output)
        log.setLevel(logging.INFO)
    return log
