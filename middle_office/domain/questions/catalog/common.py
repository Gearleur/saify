"""Ce que partagent les entrées du catalogue : valorisation d'une ligne, périmètre, avertissement."""

from decimal import Decimal

PMS_WARNING = (
    "Positions de la base de gestion (vue PMS, en date de négociation) : "
    "opérations non dénouées incluses."
)


def market_value(quantity: Decimal, price: Decimal, quote_mode: str | None) -> Decimal | None:
    """Quantité en nominal pour les obligations (cours en % du nominal), en titres pour les actions."""
    if quote_mode == "POURCENTAGE":
        return (
            quantity * price / 100
        )  # surtout pas × valeur_nominale : la quantité est déjà un nominal
    if quote_mode == "UNITAIRE":
        return quantity * price
    return None  # mode inconnu : on ne devine pas


def scope_label(fund: str | None, isin: str | None) -> str:
    return " ".join(
        filter(
            None, [f"sur {isin}" if isin else "", f"pour {fund}" if fund else "pour les 3 fonds"]
        )
    )
