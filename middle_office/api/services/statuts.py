"""Statut de traitement des suspens (à traiter, en cours, traité), partagé entre les postes et tracé.

La clé ne dépend pas du rapprochement mais du suspens lui-même (date d'arrêté, entité, ISIN,
conservateur, type) : relancer le rapprochement du jour ne remet pas le travail à zéro.
"""

import logging
from datetime import UTC, datetime

from middle_office.api.erreurs import ErreurApi
from middle_office.api.schemas import (
    Rapprochement,
    StatutsTraitement,
    StatutSuspens,
    StatutTraitement,
    SuspensSortie,
)
from middle_office.api.services.historique import Historique

log = logging.getLogger("middle_office.api.audit")
A_TRAITER = "a_traiter"


def cle(r: Rapprochement, s: SuspensSortie) -> str:
    return "|".join([r.date_arrete or "date-inconnue", s.entite, s.isin, s.conservateur, s.type])


def lire(historique: Historique, id_: str) -> StatutsTraitement:
    """Statuts des suspens de ce rapprochement ; « à traiter » est implicite et n'est pas renvoyé."""
    r = historique.lire(id_).modele
    connus = historique.statuts([cle(r, s) for s in r.suspens])
    statuts = {
        s.id: connus[cle(r, s)] for s in r.suspens if connus.get(cle(r, s), A_TRAITER) != A_TRAITER
    }
    # Validé par pydantic : un statut inattendu en base lève plutôt que d'être renvoyé tel quel.
    return StatutsTraitement.model_validate({"statuts": statuts})


def changer(
    historique: Historique, id_: str, suspens: str, statut: StatutTraitement, rid: str
) -> StatutSuspens:
    r = historique.lire(id_).modele
    s = next((s for s in r.suspens if s.id == suspens), None)
    if s is None:
        raise ErreurApi(404, "INTROUVABLE", f"suspens « {suspens} » introuvable dans {id_}")
    modifie_le = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    historique.changer_statut(cle(r, s), statut, modifie_le, rid)
    log.info(
        "audit statut rid=%s rapprochement=%s suspens=%s cle=%s statut=%s",
        rid,
        id_,
        suspens,
        cle(r, s),
        statut,
    )
    return StatutSuspens(suspens=suspens, statut=statut, modifie_le=modifie_le)
