"""Catalogue des requêtes autorisées, une entrée par module. Chaque entrée : SQL fixe et paramétré,
calcul en Decimal, phrase issue d'un gabarit. Rien ici ne vient d'un LLM : il choisit seulement
l'entrée du catalogue et ses paramètres.
"""

from middle_office.domaine.questions.catalogue.echeances import HORIZON_DEFAUT_MOIS, echeances
from middle_office.domaine.questions.catalogue.operations import operations_non_denouees
from middle_office.domaine.questions.catalogue.origine import origine_suspens
from middle_office.domaine.questions.catalogue.valorisation import (
    concentration_emetteurs,
    encours_valorise,
)

__all__ = [
    "HORIZON_DEFAUT_MOIS",
    "concentration_emetteurs",
    "echeances",
    "encours_valorise",
    "operations_non_denouees",
    "origine_suspens",
]
