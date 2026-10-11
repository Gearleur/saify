"""Catalogue des requêtes autorisées, une entrée par module. Chaque entrée : SQL fixe et paramétré,
calcul en Decimal, phrase issue d'un gabarit. Rien ici ne vient d'un LLM : il choisit seulement
l'entrée du catalogue et ses paramètres.
"""

from middle_office.domain.questions.catalog.break_origin import break_origin
from middle_office.domain.questions.catalog.maturities import DEFAULT_HORIZON_MONTHS, maturities
from middle_office.domain.questions.catalog.trades import unsettled_trades
from middle_office.domain.questions.catalog.valuation import (
    fund_valuation,
    issuer_concentration,
)

__all__ = [
    "DEFAULT_HORIZON_MONTHS",
    "issuer_concentration",
    "maturities",
    "fund_valuation",
    "unsettled_trades",
    "break_origin",
]
