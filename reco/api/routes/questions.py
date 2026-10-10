"""Questions sur la base de gestion (besoin 2) : réponse JSON, ou flux SSE des étapes du traitement.

Le flux n'émet pas de texte de LLM (la réponse est un gabarit) : il annonce chaque étape au fil de
l'eau, puis la réponse complète, identique à celle de la route JSON.
"""

import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from reco.api.dependances import HistoriqueDep, LLMDep, ReglagesDep
from reco.api.erreurs import ERREUR_INTERNE
from reco.api.schemas import Question, ReponseQuestion
from reco.api.services.questions import contexte_suspens, vers_sortie
from reco.domaine.questions.comprehension import comprendre, executer
from reco.domaine.rapprochement import DATE_ARRETE

router = APIRouter(prefix="/api/questions", tags=["questions"])
log = logging.getLogger("reco.api.questions")


@router.post("")
def poser(question: Question, reglages: ReglagesDep, historique: HistoriqueDep, llm: LLMDep) -> ReponseQuestion:  # fmt: skip
    c = comprendre(question.question, reglages.base, llm, DATE_ARRETE)
    suspens, id_ = contexte_suspens(historique)
    return vers_sortie(executer(c, question.question, reglages.base, DATE_ARRETE, suspens, id_))


def _evenement(nom: str, donnees: dict) -> str:
    return f"event: {nom}\ndata: {json.dumps(donnees, ensure_ascii=False)}\n\n"


@router.post("/flux")
def poser_en_flux(question: Question, reglages: ReglagesDep, historique: HistoriqueDep, llm: LLMDep) -> StreamingResponse:  # fmt: skip
    """L'entrée est validée avant d'ouvrir le flux : une question invalide reçoit un vrai 422."""

    def flux() -> Iterator[str]:
        try:
            yield _evenement(
                "etape", {"etape": "comprehension", "message": "Analyse de la question…"}
            )
            c = comprendre(question.question, reglages.base, llm, DATE_ARRETE)
            yield _evenement("comprehension", c.trace())
            yield _evenement("etape", {"etape": "calcul", "message": "Requête en lecture seule sur la base de gestion…"})  # fmt: skip
            suspens, id_ = contexte_suspens(historique)
            reponse = executer(c, question.question, reglages.base, DATE_ARRETE, suspens, id_)
            yield _evenement("reponse", vers_sortie(reponse).model_dump(mode="json"))
        except Exception:
            log.exception("erreur dans le flux de question")
            _, code, message = ERREUR_INTERNE
            yield _evenement("erreur", {"code": code, "message": message})
        yield _evenement("fin", {})

    return StreamingResponse(flux(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})  # fmt: skip
