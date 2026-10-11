"""Lecture des sources (PMS, conservateurs A/B/C, paramétrage) en positions normalisées.

Un module par source ; chaque lecteur rend des `Position` en `Decimal` et trace dans son journal
toute transformation (voir `commun.py`). Tous ont la même signature ; `date_arrete` vaut None quand le
PMS n'a pas permis de l'établir : ce blocage est déjà tracé, et les lecteurs lisent quand même pour
signaler tout le reste en une fois. Ce paquet expose ce dont le moteur et l'API ont besoin.
"""

from middle_office.domaine.rapprochement.sources.commun import (
    ERREURS_DE_FORMAT,
    Anomalie,
    Lecture,
    Position,
    anomalie,
    isin_valide,
)
from middle_office.domaine.rapprochement.sources.depositaire_a import lire_depositaire_a
from middle_office.domaine.rapprochement.sources.depositaire_b import lire_depositaire_b
from middle_office.domaine.rapprochement.sources.depositaire_c import lire_depositaire_c
from middle_office.domaine.rapprochement.sources.parametrage import (
    TYPES_REQUIS,
    Parametrage,
    lire_parametrage,
)
from middle_office.domaine.rapprochement.sources.pms import dates_pms, lire_pms

__all__ = [
    "ERREURS_DE_FORMAT",
    "TYPES_REQUIS",
    "Anomalie",
    "Lecture",
    "Parametrage",
    "Position",
    "anomalie",
    "dates_pms",
    "isin_valide",
    "lire_depositaire_a",
    "lire_depositaire_b",
    "lire_depositaire_c",
    "lire_parametrage",
    "lire_pms",
]
