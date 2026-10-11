"""Lecture des sources (PMS, conservateurs A/B/C, paramétrage) en positions normalisées.

Un module par source ; chaque lecteur rend des `Position` en `Decimal` et trace dans son journal
toute transformation (voir `commun.py`). Tous ont la même signature ; `date_arrete` vaut None quand le
PMS n'a pas permis de l'établir : ce blocage est déjà tracé, et les lecteurs lisent quand même pour
signaler tout le reste en une fois. Ce paquet expose ce dont le moteur et l'API ont besoin.
"""

from middle_office.domain.reconciliation.sources.client_config import (
    REQUIRED_TYPES,
    ClientConfig,
    read_client_config,
)
from middle_office.domain.reconciliation.sources.common import (
    FORMAT_ERRORS,
    Anomaly,
    Position,
    SourceReading,
    anomaly,
    is_valid_isin,
)
from middle_office.domain.reconciliation.sources.custodian_a import read_custodian_a
from middle_office.domain.reconciliation.sources.custodian_b import read_custodian_b
from middle_office.domain.reconciliation.sources.custodian_c import read_custodian_c
from middle_office.domain.reconciliation.sources.pms import pms_dates, read_pms

__all__ = [
    "FORMAT_ERRORS",
    "REQUIRED_TYPES",
    "Anomaly",
    "SourceReading",
    "ClientConfig",
    "Position",
    "anomaly",
    "pms_dates",
    "is_valid_isin",
    "read_custodian_a",
    "read_custodian_b",
    "read_custodian_c",
    "read_client_config",
    "read_pms",
]
