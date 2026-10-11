"""Référentiel en lecture seule : paramétrage client, codes fonds et disponibilité de orsay.db."""

import logging
import sqlite3
from pathlib import Path

from middle_office.api.config import Reglages
from middle_office.api.erreurs import ErreurApi
from middle_office.api.schemas import Conservateur, Fonds, ParametrageSortie, Transco, TypeEcart
from middle_office.domaine.base_gestion import connexion_lecture_seule, date_reference
from middle_office.domaine.rapprochement.sources import ERREURS_DE_FORMAT, lire_parametrage

log = logging.getLogger("middle_office.api.referentiel")

TRANSCOS = ("TRANSCO_SOUS_COMPTES", "TRANSCO_DEPOSITAIRE_A", "TRANSCO_DEPOSITAIRE_B", "TRANSCO_DEPOSITAIRE_C")  # fmt: skip
# Ni le paramétrage ni la base ne les portent : repris de l'énoncé (limite connue).
CONSERVATEURS = [
    Conservateur(code="A", nom="CACEIS"),
    Conservateur(code="B", nom="Euroclear"),
    Conservateur(code="C", nom="BNP Paribas (BP2S)"),
]
EXCLUSIONS = [
    "Sous-compte P3G (compte technique de passage)",
    "Ligne sans sous-compte (saisie incomplète)",
    "Item conservateur C annulé (ACTION=S)",
]


def _lire_base(base: Path, requete: str) -> list[tuple]:
    with connexion_lecture_seule(base) as db:
        return db.execute(requete).fetchall()


def base_disponible(base: Path) -> bool:
    try:
        _lire_base(base, "SELECT 1 FROM portefeuilles LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def date_de_la_base(base: Path) -> str | None:
    """Date des dernières positions de orsay.db (ISO), None si la base est illisible."""
    try:
        jour = date_reference(base)
    except sqlite3.Error:
        return None
    return jour.isoformat() if jour else None


def codes_fonds(base: Path) -> dict[str, str]:
    try:
        return dict(_lire_base(base, "SELECT nom, code FROM portefeuilles"))
    except sqlite3.Error:
        return {}


def parametrage(reglages: Reglages) -> ParametrageSortie:
    try:
        param = lire_parametrage(reglages.parametrage)
    except (*ERREURS_DE_FORMAT, OSError) as exc:
        log.warning("parametrage illisible : %s", exc)
        raise ErreurApi(503, "PARAMETRAGE_INDISPONIBLE", f"parametrage.xlsx illisible : {exc}") from exc  # fmt: skip
    tables = dict(zip(TRANSCOS, (param.sous_comptes, param.comptes_a, param.desks_b, param.comptes_c), strict=True))  # fmt: skip
    entites = list(dict.fromkeys(e for table in tables.values() for e in table.values()))
    codes = codes_fonds(reglages.base)
    return ParametrageSortie(
        date_arrete=date_de_la_base(reglages.base),
        fonds=[Fonds(entite=e, code=codes.get(e, "")) for e in entites],
        conservateurs=CONSERVATEURS,
        types_ecarts=[
            TypeEcart(code=code, libelle=str(libelle), action_attendue=str(action))
            for code, (libelle, action) in param.types_ecarts.items()
        ],
        transcos={
            nom: [Transco(cle=cle, entite=entite) for cle, entite in table.items()]
            for nom, table in tables.items()
        },
        exclusions=EXCLUSIONS,
    )
