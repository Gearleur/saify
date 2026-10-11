"""Traitement d'une question, partagé par la route JSON et le flux SSE : date de référence, compréhension,
réponse sur le dernier rapprochement exploitable, sérialisation, et une ligne d'audit par question."""

import hashlib
import logging
import sqlite3
from datetime import date
from pathlib import Path

from middle_office.api.config import Settings
from middle_office.api.errors import ApiError
from middle_office.api.schemas import (
    FigureOut,
    QuestionAnswer,
    SourceRowOut,
    UnderstandingOut,
    VigilanceOut,
)
from middle_office.api.services.history import History
from middle_office.api.services.llm import GuardedClient
from middle_office.domain.management_db import latest_position_date
from middle_office.domain.questions.intent import Understanding
from middle_office.domain.questions.models import Answer, ReconciliationContext
from middle_office.domain.questions.understanding import execute, understand

log = logging.getLogger("middle_office.api.audit")


def reference_date(db_path: Path) -> date:
    """Les questions portent sur la date des dernières positions de la base, affichée dans chaque réponse."""
    try:
        day = latest_position_date(db_path)
    except sqlite3.Error as exc:
        raise ApiError(
            503, "BASE_INDISPONIBLE", "Base de gestion illisible : réessayer plus tard"
        ) from exc
    if day is None:
        raise ApiError(503, "BASE_INDISPONIBLE", "Aucune position dans la base de gestion")
    return day


def understand_question(
    question: str, settings: Settings, llm: GuardedClient | None, day: date
) -> Understanding:
    return understand(question, settings.db_path, llm, day)


def answer_and_audit(
    c: Understanding,
    question: str,
    settings: Settings,
    history: History,
    day: date,
    rid: str,
) -> QuestionAnswer:
    """Exécute l'intention comprise et trace la décision : qui a compris quoi (LLM ou mots-clés), avec
    quelle confiance, et ce qui a été répondu. Ni la question ni la réponse en clair : une empreinte
    de la question suffit à rapprocher une plainte de sa ligne d'audit."""
    answer = execute(c, question, settings.db_path, day, break_context(history))
    log.info(
        "audit question rid=%s empreinte=%s intention=%s source=%s confiance=%.2f fonds=%s isin=%s "
        "horizon=%s date_demandee=%s reponse=%s chiffres=%d detail=%s",
        rid,
        hashlib.sha256(question.encode()).hexdigest()[:12],
        c.intent,
        c.source,
        c.confidence,
        c.fund,
        c.isin,
        c.horizon_months,
        getattr(c, "date_demandee", None),
        answer.confidence,
        len(answer.figures),
        c.detail or "-",
    )
    return to_output(answer)


def break_context(history: History) -> ReconciliationContext | None:
    """Dernier rapprochement exploitable (OK), pour « d'où vient le suspens sur X ? ».

    Le plus récent n'est pas forcément le bon : bloqué, il n'a aucun suspens, et répondre « aucun
    suspens sur X » rassurerait à tort. On répond sur le dernier OK en signalant le blocage.
    """
    latest = history.latest()
    if latest is None:
        return None
    blocked = latest.id if latest.status != "OK" else None
    ok = latest if blocked is None else history.latest("OK")
    if ok is None:
        return ReconciliationContext(id=None, newer_blocked=blocked)
    return ReconciliationContext(
        id=ok.id,
        as_of_date=ok.as_of_date,
        breaks=[s.model_dump() for s in ok.breaks],
        newer_blocked=blocked,
    )


def to_output(r: Answer) -> QuestionAnswer:
    """Décimaux en texte (jamais de float), comme le reste de l'API."""
    return QuestionAnswer(
        question=r.question,
        answer=r.answer,
        figures=[FigureOut(label=c.label, value=str(c.value), unit=c.unit) for c in r.figures],
        sql_query=r.sql_query,
        sql_params=r.sql_params,
        source_rows=[SourceRowOut(table=line.table, values=line.values) for line in r.source_rows],
        confidence=r.confidence,
        warnings=r.warnings,
        vigilances=[
            VigilanceOut(code=v.code, message=v.message, issuers=v.issuers, value=str(v.value))
            for v in r.vigilances
        ],
        suggestions=r.suggestions,
        understanding=UnderstandingOut(**r.understanding),
    )
