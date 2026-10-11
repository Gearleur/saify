"""Santé de l'API et référentiel (lecture seule)."""

from fastapi import APIRouter

from middle_office.api.config import VERSION
from middle_office.api.dependances import LLMDep, ReglagesDep
from middle_office.api.schemas import EtatLLM, ParametrageSortie, Sante
from middle_office.api.services import referentiel
from middle_office.domaine.questions.comprehension import MODELE

router = APIRouter(prefix="/api", tags=["système"])


@router.get("/sante")
def sante(reglages: ReglagesDep, llm: LLMDep) -> Sante:
    etat = EtatLLM(
        actif=llm is not None,
        modele=MODELE,
        budget_jour=reglages.llm_budget_jour,
        appels_aujourdhui=0 if llm is None else llm.appels_aujourdhui,
    )
    return Sante(
        statut="ok",
        version=VERSION,
        date_arrete=referentiel.date_de_la_base(reglages.base),
        base_disponible=referentiel.base_disponible(reglages.base),
        llm=etat,
    )


@router.get("/parametrage")
def parametrage(reglages: ReglagesDep) -> ParametrageSortie:
    return referentiel.parametrage(reglages)
