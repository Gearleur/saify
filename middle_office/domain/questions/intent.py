"""Ce qui a été compris d'une question : l'entrée du catalogue, ses paramètres, et d'où vient
cette compréhension (LLM ou mots-clés). Tracé dans chaque réponse.
"""

from dataclasses import dataclass, field

FUNDS = {"PAT": "ORSAY PATRIMOINE", "OBL": "ORSAY OBLIGATIONS", "ACT": "ORSAY ACTIONS EUROPE"}


@dataclass
class Understanding:
    intent: str
    fund: str | None = None
    horizon_months: int | None = None
    isin: str | None = None
    source: str = "mots_cles"  # llm ou mots_cles
    confidence: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    detail: str = ""  # pourquoi le LLM n'a pas été utilisé, le cas échéant
    # Ce que la question cite et que le catalogue ne sait pas toujours traiter : on refuse plutôt que
    # de répondre à côté (un vrai chiffre, mais d'une autre question).
    requested_date: str | None = None  # AAAA-MM-JJ, ou l'expression relative trouvée (« hier »)
    candidate_securities: list[tuple[str, str]] = field(
        default_factory=list
    )  # (isin, libellé), si ambigu

    def trace(self) -> dict:
        return {
            "intent": self.intent,
            "fund": self.fund,
            "horizon_months": self.horizon_months,
            "isin": self.isin,
            "source": self.source,
            "confidence": self.confidence,
            "detail": self.detail,
            "requested_date": self.requested_date,
        }
