"""Référentiel en lecture seule : paramétrage client, codes fonds et disponibilité de orsay.db."""

import logging
import sqlite3
from pathlib import Path

from middle_office.api.config import Settings
from middle_office.api.errors import ApiError
from middle_office.api.schemas import BreakType, ClientConfigOut, Custodian, Fund, Mapping
from middle_office.domain.management_db import latest_position_date, read_only_connection
from middle_office.domain.reconciliation.sources import FORMAT_ERRORS, read_client_config

log = logging.getLogger("middle_office.api.referentiel")

MAPPING_TABLES = (
    "TRANSCO_SOUS_COMPTES",
    "TRANSCO_DEPOSITAIRE_A",
    "TRANSCO_DEPOSITAIRE_B",
    "TRANSCO_DEPOSITAIRE_C",
)
# Ni le paramétrage ni la base ne les portent : repris de l'énoncé (limite connue).
CUSTODIANS = [
    Custodian(code="A", name="CACEIS"),
    Custodian(code="B", name="Euroclear"),
    Custodian(code="C", name="BNP Paribas (BP2S)"),
]
EXCLUSIONS = [
    "Sous-compte P3G (compte technique de passage)",
    "Ligne sans sous-compte (saisie incomplète)",
    "Item conservateur C annulé (ACTION=S)",
]


def _read_db(db_path: Path, query: str) -> list[tuple]:
    with read_only_connection(db_path) as db:
        return db.execute(query).fetchall()


def db_available(db_path: Path) -> bool:
    try:
        _read_db(db_path, "SELECT 1 FROM portefeuilles LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def db_date(db_path: Path) -> str | None:
    """Date des dernières positions de orsay.db (ISO), None si la base est illisible."""
    try:
        day = latest_position_date(db_path)
    except sqlite3.Error:
        return None
    return day.isoformat() if day else None


def fund_codes(db_path: Path) -> dict[str, str]:
    try:
        return dict(_read_db(db_path, "SELECT nom, code FROM portefeuilles"))
    except sqlite3.Error:
        return {}


def client_config(settings: Settings) -> ClientConfigOut:
    try:
        config = read_client_config(settings.client_config)
    except (*FORMAT_ERRORS, OSError) as exc:
        log.warning("parametrage illisible : %s", exc)
        raise ApiError(
            503, "PARAMETRAGE_INDISPONIBLE", f"parametrage.xlsx illisible : {exc}"
        ) from exc
    tables = dict(
        zip(
            MAPPING_TABLES,
            (config.sub_accounts, config.accounts_a, config.desks_b, config.accounts_c),
            strict=True,
        )
    )
    entities = list(dict.fromkeys(e for table in tables.values() for e in table.values()))
    codes = fund_codes(settings.db_path)
    return ClientConfigOut(
        as_of_date=db_date(settings.db_path),
        fund=[Fund(entity=e, code=codes.get(e, "")) for e in entities],
        custodians=CUSTODIANS,
        break_types=[
            BreakType(code=code, label=str(label), expected_action=str(action))
            for code, (label, action) in config.break_types.items()
        ],
        mappings={
            name: [Mapping(key=key, entity=entity) for key, entity in table.items()]
            for name, table in tables.items()
        },
        exclusions=EXCLUSIONS,
    )
