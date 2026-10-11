"""Contrôles qui n'empêchent pas le rapprochement mais remontent à un humain (niveau SIGNALE)."""

from collections import defaultdict
from datetime import date

from middle_office.domaine.formats import date_fr, formater_quantite
from middle_office.domaine.rapprochement.informations import Base
from middle_office.domaine.rapprochement.sources import Anomalie, Position, isin_valide


def _signale(fichier: str, ligne: int, regle: str, brut: str, retenu: str, motif: str) -> Anomalie:
    return Anomalie(fichier, ligne, "SIGNALE", regle, brut, retenu, motif)


def _isins_douteux(positions: list[Position], base: Base) -> list[Anomalie]:
    """Une fois par ISIN : clé de contrôle invalide, ou absent du référentiel de orsay.db."""
    anomalies, vus = [], set()
    for p in positions:
        if p.isin in vus:
            continue
        vus.add(p.isin)
        if not isin_valide(p.isin):
            motif = "clé de contrôle ISIN invalide : probable erreur de saisie"
            anomalies.append(
                _signale(p.fichier, p.ligne, "ISIN_CLE_INVALIDE", p.isin, p.isin, motif)
            )
        if base.referentiel is not None and p.isin not in base.referentiel:
            motif = "ISIN absent du référentiel titres"
            anomalies.append(
                _signale(p.fichier, p.ligne, "ISIN_HORS_REFERENTIEL", p.isin, p.isin, motif)
            )
    return anomalies


def _libelles_divergents(positions: list[Position]) -> list[Anomalie]:
    """Même ISIN, libellés PMS et conservateur différents (casse ignorée) : vérifier le titre."""
    par_isin: dict[str, dict[str, Position]] = defaultdict(dict)
    for p in positions:
        if p.libelle:
            par_isin[p.isin].setdefault("PMS" if p.source == "PMS" else "DEP", p)
    anomalies = []
    for isin, cotes in par_isin.items():
        pms, dep = cotes.get("PMS"), cotes.get("DEP")
        if pms and dep and pms.libelle.upper() != dep.libelle.upper():
            motif = f"{isin} : libellé PMS « {pms.libelle} » ≠ conservateur « {dep.libelle} »"
            anomalies.append(
                _signale(
                    dep.fichier, dep.ligne, "LIBELLE_DIFFERENT", dep.libelle, pms.libelle, motif
                )
            )
    return anomalies


def signaler_positions(positions: list[Position], base: Base) -> list[Anomalie]:
    """ISIN douteux et libellés divergents : conservés, mais remontés à un humain."""
    return _isins_douteux(positions, base) + _libelles_divergents(positions)


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
