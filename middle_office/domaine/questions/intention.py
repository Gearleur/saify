"""Ce qui a été compris d'une question : l'entrée du catalogue, ses paramètres, et d'où vient
cette compréhension (LLM ou mots-clés). Tracé dans chaque réponse.
"""

from dataclasses import dataclass, field

FONDS = {"PAT": "ORSAY PATRIMOINE", "OBL": "ORSAY OBLIGATIONS", "ACT": "ORSAY ACTIONS EUROPE"}


@dataclass
class Comprehension:
    intention: str
    fonds: str | None = None
    horizon_mois: int | None = None
    isin: str | None = None
    source: str = "mots_cles"  # llm ou mots_cles
    confiance: float = 0.0
    reformulations: list[str] = field(default_factory=list)
    detail: str = ""  # pourquoi le LLM n'a pas été utilisé, le cas échéant
    # Ce que la question cite et que le catalogue ne sait pas toujours traiter : on refuse plutôt que
    # de répondre à côté (un vrai chiffre, mais d'une autre question).
    date_demandee: str | None = None  # AAAA-MM-JJ, ou l'expression relative trouvée (« hier »)
    titres_candidats: list[tuple[str, str]] = field(
        default_factory=list
    )  # (isin, libellé), si ambigu

    def trace(self) -> dict:
        return {
            "intention": self.intention,
            "fonds": self.fonds,
            "horizon_mois": self.horizon_mois,
            "isin": self.isin,
            "source": self.source,
            "confiance": self.confiance,
            "detail": self.detail,
            "date_demandee": self.date_demandee,
        }
