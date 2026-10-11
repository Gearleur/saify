"""Questions sur la base de gestion (besoin 2) : réponse JSON, ou flux SSE des étapes du traitement.

Le flux n'émet pas de texte de LLM (la réponse est un gabarit) : il annonce chaque étape au fil de
l'eau, puis la réponse complète, identique à celle de la route JSON.
"""

import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from middle_office.api.dependances import HistoriqueDep, LLMDep, ReglagesDep
from middle_office.api.erreurs import ERREUR_INTERNE
from middle_office.api.schemas import Question, ReponseQuestion
from middle_office.api.services.questions import (
    comprendre_question,
    date_de_reference,
    repondre_question,
)

router = APIRouter(prefix="/api/questions", tags=["questions"])
log = logging.getLogger("middle_office.api.questions")


@router.post("")
def poser(question: Question, request: Request, reglages: ReglagesDep, historique: HistoriqueDep,
          llm: LLMDep) -> ReponseQuestion:  # fmt: skip
    jour = date_de_reference(reglages.base)
    c = comprendre_question(question.question, reglages, llm, jour)
    return repondre_question(
        c, question.question, reglages, historique, jour, request.state.request_id
    )


def _evenement(nom: str, donnees: dict) -> str:
    return f"event: {nom}\ndata: {json.dumps(donnees, ensure_ascii=False)}\n\n"


@router.post("/flux")
def poser_en_flux(question: Question, request: Request, reglages: ReglagesDep,
                  historique: HistoriqueDep, llm: LLMDep) -> StreamingResponse:  # fmt: skip
    """L'entrée et la base sont vérifiées avant d'ouvrir le flux : on reçoit un vrai 422 ou 503."""
    jour = date_de_reference(reglages.base)
    rid = request.state.request_id

    def flux() -> Iterator[str]:
        try:
            yield _evenement(
                "etape", {"etape": "comprehension", "message": "Analyse de la question…"}
            )
            c = comprendre_question(question.question, reglages, llm, jour)
            yield _evenement("comprehension", c.trace())
            yield _evenement("etape", {"etape": "calcul", "message": "Requête en lecture seule sur la base de gestion…"})  # fmt: skip
            reponse = repondre_question(c, question.question, reglages, historique, jour, rid)
            yield _evenement("reponse", reponse.model_dump(mode="json"))
        except Exception:
            log.exception("rid=%s erreur dans le flux de question", rid)
            _, code, message = ERREUR_INTERNE
            yield _evenement("erreur", {"code": code, "message": message})
        yield _evenement("fin", {})

    return StreamingResponse(flux(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})  # fmt: skip
