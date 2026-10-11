"""Ce que partagent les entrées du catalogue : valorisation d'une ligne, périmètre, avertissement."""

from decimal import Decimal

AVERTISSEMENT_PMS = (
    "Positions de la base de gestion (vue PMS, en date de négociation) : "
    "opérations non dénouées incluses."
)


def valoriser(quantite: Decimal, cours: Decimal, mode_cotation: str | None) -> Decimal | None:
    """Quantité en nominal pour les obligations (cours en % du nominal), en titres pour les actions."""
    if mode_cotation == "POURCENTAGE":
        return (
            quantite * cours / 100
        )  # surtout pas × valeur_nominale : la quantité est déjà un nominal
    if mode_cotation == "UNITAIRE":
        return quantite * cours
    return None  # mode inconnu : on ne devine pas


def libelle_perimetre(fonds: str | None, isin: str | None) -> str:
    return " ".join(
        filter(
            None, [f"sur {isin}" if isin else "", f"pour {fonds}" if fonds else "pour les 3 fonds"]
        )
    )
