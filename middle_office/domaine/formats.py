"""Écritures à la française partagées par les deux besoins : quantités, montants, pourcentages, dates.

Tout part d'un `Decimal` : aucune valeur ne passe par un flottant pour être affichée.
"""

from datetime import date
from decimal import Decimal

CENTIME = Decimal("0.01")


def formater_quantite(q: Decimal) -> str:
    """250000 → « 250 000 » ; les décimales ne sont écrites que si elles existent."""
    texte = f"{q:,.0f}" if q == q.to_integral_value() else f"{q:,}"
    return texte.replace(",", " ")


def montant(valeur: Decimal) -> str:
    """724836.00 → « 724 836,00 »"""
    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",")


def pourcentage(valeur: Decimal) -> str:
    """33.456 → « 33,46 % »"""
    return f"{valeur.quantize(CENTIME)}".replace(".", ",") + " %"


def date_fr(d: date) -> str:
    return f"{d:%d/%m/%Y}"
