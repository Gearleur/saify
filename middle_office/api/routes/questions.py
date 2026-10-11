"""Questions sur la base de gestion (besoin 2) : réponse JSON, ou flux SSE des étapes du traitement.

Le flux n'émet pas de texte de LLM (la réponse est un gabarit) : il annonce chaque étape au fil de
l'eau, puis la réponse complète, identique à celle de la route JSON.
"""

import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from middle_office.api.dependencies import HistoryDep, LlmDep, SettingsDep
from middle_office.api.errors import INTERNAL_ERROR
from middle_office.api.schemas import Question, QuestionAnswer
from middle_office.api.services.questions import (
    answer_and_audit,
    reference_date,
    understand_question,
)

router = APIRouter(prefix="/api/questions", tags=["questions"])
log = logging.getLogger("middle_office.api.questions")


@router.post("")
def ask(
    question: Question,
    request: Request,
    settings: SettingsDep,
    history: HistoryDep,
    llm: LlmDep,
) -> QuestionAnswer:
    day = reference_date(settings.db_path)
    c = understand_question(question.question, settings, llm, day)
    return answer_and_audit(c, question.question, settings, history, day, request.state.request_id)


def _event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
def ask_streaming(
    question: Question,
    request: Request,
    settings: SettingsDep,
    history: HistoryDep,
    llm: LlmDep,
) -> StreamingResponse:
    """L'entrée et la base sont vérifiées avant d'ouvrir le flux : on reçoit un vrai 422 ou 503."""
    day = reference_date(settings.db_path)
    rid = request.state.request_id

    def stream() -> Iterator[str]:
        try:
            yield _event("step", {"step": "understanding", "message": "Analyse de la question…"})
            c = understand_question(question.question, settings, llm, day)
            yield _event("understanding", c.trace())
            yield _event(
                "step",
                {
                    "step": "computing",
                    "message": "Requête en lecture seule sur la base de gestion…",
                },
            )
            answer = answer_and_audit(c, question.question, settings, history, day, rid)
            yield _event("answer", answer.model_dump(mode="json"))
        except Exception:
            log.exception("rid=%s erreur dans le flux de question", rid)
            _, code, message = INTERNAL_ERROR
            yield _event("error", {"code": code, "message": message})
        yield _event("end", {})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
