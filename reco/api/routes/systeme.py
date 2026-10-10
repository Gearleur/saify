"""Santé de l'API et référentiel (lecture seule)."""

from fastapi import APIRouter

from reco.api.config import VERSION
from reco.api.dependances import LLMDep, ReglagesDep
from reco.api.schemas import EtatLLM, ParametrageSortie, Sante
from reco.api.services import referentiel
from reco.domaine.questions.comprehension import MODELE
from reco.domaine.rapprochement import DATE_ARRETE

router = APIRouter(prefix="/api", tags=["système"])


@router.get("/sante")
def sante(reglages: ReglagesDep, llm: LLMDep) -> Sante:
    etat = EtatLLM(actif=llm is not None, modele=MODELE, budget_jour=reglages.llm_budget_jour,
                   appels_aujourdhui=0 if llm is None else llm.appels_aujourdhui)  # fmt: skip
    return Sante(statut="ok", version=VERSION, date_arrete=DATE_ARRETE.isoformat(),
                 base_disponible=referentiel.base_disponible(reglages.base), llm=etat)  # fmt: skip


@router.get("/parametrage")
def parametrage(reglages: ReglagesDep) -> ParametrageSortie:
    return referentiel.parametrage(reglages)
