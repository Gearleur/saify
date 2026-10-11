"""Contrôles qui n'empêchent pas le rapprochement mais remontent à un humain (niveau SIGNALE)."""

from collections import defaultdict
from datetime import date

from middle_office.domaine.formats import date_fr, formater_quantite
from middle_office.domaine.rapprochement.informations import Base
from middle_office.domaine.rapprochement.sources import Anomalie, Position, isin_valide


def signaler_positions(positions: list[Position], base: Base) -> list[Anomalie]:
    """ISIN douteux et libellés divergents : conservés, mais remontés à un humain."""
    anomalies = []
    vus: set[str] = set()
    for p in positions:
        if p.isin in vus:
            continue
        vus.add(p.isin)
        if not isin_valide(p.isin):
            anomalies.append(
                Anomalie(
                    p.fichier,
                    p.ligne,
                    "SIGNALE",
                    "ISIN_CLE_INVALIDE",
                    p.isin,
                    p.isin,
                    "clé de contrôle ISIN invalide : probable erreur de saisie",
                )
            )
        if base.referentiel is not None and p.isin not in base.referentiel:
            anomalies.append(
                Anomalie(
                    p.fichier,
                    p.ligne,
                    "SIGNALE",
                    "ISIN_HORS_REFERENTIEL",
                    p.isin,
                    p.isin,
                    "ISIN absent du référentiel titres",
                )
            )
    libelles: dict[str, dict[str, Position]] = defaultdict(dict)
    for p in positions:
        if p.libelle:
            libelles[p.isin].setdefault("PMS" if p.source == "PMS" else "DEP", p)
    for isin, par_cote in libelles.items():
        if (
            len(par_cote) == 2
            and par_cote["PMS"].libelle.upper() != par_cote["DEP"].libelle.upper()
        ):
            p, d = par_cote["PMS"], par_cote["DEP"]
            anomalies.append(
                Anomalie(
                    d.fichier,
                    d.ligne,
                    "SIGNALE",
                    "LIBELLE_DIFFERENT",
                    d.libelle,
                    p.libelle,
                    f"{isin} : libellé PMS « {p.libelle} » ≠ conservateur « {d.libelle} »",
                )
            )
    return anomalies


def denouements_depasses(base: Base, date_arrete: date) -> list[Anomalie]:
    """Opération toujours en attente alors que son dénouement était prévu au plus tard à l'arrêté :
    défaut de règlement-livraison, signalé même si les positions tombent juste."""
    return [
        Anomalie(
            "orsay.db",
            m.id,
            "SIGNALE",
            "DENOUEMENT_DEPASSE",
            f"mouvement {m.id}",
            "",
            f"{m.portefeuille} {m.isin} {m.sens} {formater_quantite(m.quantite)} non dénoué "
            f"au {date_fr(m.date_denouement)} : risque CSDR",
        )
        for m in base.en_attente
        if m.date_denouement <= date_arrete
    ]
