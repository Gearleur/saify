"""Questions sur la base de gestion (besoin 2) : réponse JSON, ou flux SSE des étapes du traitement.

Le flux n'émet pas de texte de LLM (la réponse est un gabarit) : il annonce chaque étape au fil de
l'eau, puis la réponse complète, identique à celle de la route JSON.
"""

import json
import logging
import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from middle_office.api.dependances import HistoriqueDep, LLMDep, ReglagesDep
from middle_office.api.erreurs import ERREUR_INTERNE, ErreurApi
from middle_office.api.schemas import Question, ReponseQuestion
from middle_office.api.services.questions import contexte_suspens, vers_sortie
from middle_office.domaine.questions.base import date_reference
from middle_office.domaine.questions.comprehension import comprendre, executer

router = APIRouter(prefix="/api/questions", tags=["questions"])
log = logging.getLogger("middle_office.api.questions")


@router.post("")
def poser(question: Question, reglages: ReglagesDep, historique: HistoriqueDep, llm: LLMDep) -> ReponseQuestion:  # fmt: skip
    jour = _date_de_reference(reglages.base)
    c = comprendre(question.question, reglages.base, llm, jour)
    contexte = contexte_suspens(historique)
    return vers_sortie(executer(c, question.question, reglages.base, jour, contexte))


def _date_de_reference(base: Path) -> date:
    """Les questions portent sur la date des dernières positions de la base, affichée dans chaque réponse."""
    try:
        jour = date_reference(base)
    except sqlite3.Error as exc:
        raise ErreurApi(
            503, "BASE_INDISPONIBLE", "Base de gestion illisible : réessayer plus tard"
        ) from exc
    if jour is None:
        raise ErreurApi(503, "BASE_INDISPONIBLE", "Aucune position dans la base de gestion")
    return jour


def _evenement(nom: str, donnees: dict) -> str:
    return f"event: {nom}\ndata: {json.dumps(donnees, ensure_ascii=False)}\n\n"


@router.post("/flux")
def poser_en_flux(question: Question, reglages: ReglagesDep, historique: HistoriqueDep, llm: LLMDep) -> StreamingResponse:  # fmt: skip
    """L'entrée et la base sont vérifiées avant d'ouvrir le flux : on reçoit un vrai 422 ou 503."""
    jour = _date_de_reference(reglages.base)

    def flux() -> Iterator[str]:
        try:
            yield _evenement(
                "etape", {"etape": "comprehension", "message": "Analyse de la question…"}
            )
            c = comprendre(question.question, reglages.base, llm, jour)
            yield _evenement("comprehension", c.trace())
            yield _evenement("etape", {"etape": "calcul", "message": "Requête en lecture seule sur la base de gestion…"})  # fmt: skip
            contexte = contexte_suspens(historique)
            reponse = executer(c, question.question, reglages.base, jour, contexte)
            yield _evenement("reponse", vers_sortie(reponse).model_dump(mode="json"))
        except Exception:
            log.exception("erreur dans le flux de question")
            _, code, message = ERREUR_INTERNE
            yield _evenement("erreur", {"code": code, "message": message})
        yield _evenement("fin", {})

    return StreamingResponse(flux(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})  # fmt: skip
