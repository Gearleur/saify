"""Santé de l'API et référentiel (lecture seule)."""

from fastapi import APIRouter

from reco.api.config import VERSION
from reco.api.dependances import ReglagesDep
from reco.api.schemas import ParametrageSortie, Sante
from reco.api.services import referentiel
from reco.domaine.rapprochement import DATE_ARRETE

router = APIRouter(prefix="/api", tags=["système"])


@router.get("/sante")
def sante(reglages: ReglagesDep) -> Sante:
    return Sante(statut="ok", version=VERSION, date_arrete=DATE_ARRETE.isoformat(),
                 base_disponible=referentiel.base_disponible(reglages.base))  # fmt: skip


@router.get("/parametrage")
def parametrage(reglages: ReglagesDep) -> ParametrageSortie:
    return referentiel.parametrage(reglages)
