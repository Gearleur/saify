"""Statut de traitement des suspens (à traiter, en cours, traité), partagé entre les postes et tracé.

La clé ne dépend pas du rapprochement mais du suspens lui-même (date d'arrêté, entité, ISIN,
conservateur, type) : relancer le rapprochement du jour ne remet pas le travail à zéro.
"""

import logging
from datetime import UTC, datetime

from middle_office.api.errors import ApiError
from middle_office.api.schemas import (
    BreakOut,
    BreakWorkStatus,
    Reconciliation,
    WorkStatus,
    WorkStatuses,
)
from middle_office.api.services.history import History

log = logging.getLogger("middle_office.api.audit")
DEFAULT_STATUS = "a_traiter"


def key(r: Reconciliation, s: BreakOut) -> str:
    return "|".join([r.as_of_date or "date-inconnue", s.entity, s.isin, s.custodian, s.type])


def read(history: History, id_: str) -> WorkStatuses:
    """Statuts des suspens de ce rapprochement ; « à traiter » est implicite et n'est pas renvoyé."""
    r = history.read(id_).model
    known = history.statuses([key(r, s) for s in r.breaks])
    statuses = {
        s.id: known[key(r, s)]
        for s in r.breaks
        if known.get(key(r, s), DEFAULT_STATUS) != DEFAULT_STATUS
    }
    # Validé par pydantic : un statut inattendu en base lève plutôt que d'être renvoyé tel quel.
    return WorkStatuses.model_validate({"statuses": statuses})


def set_status(
    history: History, id_: str, break_id: str, status: WorkStatus, rid: str
) -> BreakWorkStatus:
    r = history.read(id_).model
    s = next((s for s in r.breaks if s.id == break_id), None)
    if s is None:
        raise ApiError(404, "INTROUVABLE", f"suspens « {break_id} » introuvable dans {id_}")
    updated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    history.save_status(key(r, s), status, updated_at, rid)
    log.info(
        "audit statut rid=%s rapprochement=%s suspens=%s cle=%s statut=%s",
        rid,
        id_,
        break_id,
        key(r, s),
        status,
    )
    return BreakWorkStatus(break_id=break_id, status=status, updated_at=updated_at)
