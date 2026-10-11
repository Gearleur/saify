"""Traitement d'une question, partagé par la route JSON et le flux SSE : date de référence, compréhension,
réponse sur le dernier rapprochement exploitable, sérialisation, et une ligne d'audit par question."""

import hashlib
import logging
import sqlite3
from datetime import date
from pathlib import Path

from middle_office.api.config import Reglages
from middle_office.api.erreurs import ErreurApi
from middle_office.api.schemas import (
    ChiffreSortie,
    ComprehensionSortie,
    LigneSourceSortie,
    ReponseQuestion,
    VigilanceSortie,
)
from middle_office.api.services.historique import Historique
from middle_office.api.services.llm import ClientEncadre
from middle_office.domaine.base_gestion import date_reference
from middle_office.domaine.questions.comprehension import comprendre, executer
from middle_office.domaine.questions.intention import Comprehension
from middle_office.domaine.questions.modeles import ContexteRapprochement, Reponse

log = logging.getLogger("middle_office.api.audit")


def date_de_reference(base: Path) -> date:
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


def comprendre_question(
    question: str, reglages: Reglages, llm: ClientEncadre | None, jour: date
) -> Comprehension:
    return comprendre(question, reglages.base, llm, jour)


def repondre_question(
    c: Comprehension,
    question: str,
    reglages: Reglages,
    historique: Historique,
    jour: date,
    rid: str,
) -> ReponseQuestion:
    """Exécute l'intention comprise et trace la décision : qui a compris quoi (LLM ou mots-clés), avec
    quelle confiance, et ce qui a été répondu. Ni la question ni la réponse en clair : une empreinte
    de la question suffit à rapprocher une plainte de sa ligne d'audit."""
    reponse = executer(c, question, reglages.base, jour, contexte_suspens(historique))
    log.info(
        "audit question rid=%s empreinte=%s intention=%s source=%s confiance=%.2f fonds=%s isin=%s "
        "horizon=%s date_demandee=%s reponse=%s chiffres=%d detail=%s",
        rid,
        hashlib.sha256(question.encode()).hexdigest()[:12],
        c.intention,
        c.source,
        c.confiance,
        c.fonds,
        c.isin,
        c.horizon_mois,
        getattr(c, "date_demandee", None),
        reponse.confiance,
        len(reponse.chiffres),
        c.detail or "-",
    )
    return vers_sortie(reponse)


def contexte_suspens(historique: Historique) -> ContexteRapprochement | None:
    """Dernier rapprochement exploitable (OK), pour « d'où vient le suspens sur X ? ».

    Le plus récent n'est pas forcément le bon : bloqué, il n'a aucun suspens, et répondre « aucun
    suspens sur X » rassurerait à tort. On répond sur le dernier OK en signalant le blocage.
    """
    dernier = historique.dernier()
    if dernier is None:
        return None
    bloque = dernier.id if dernier.statut != "OK" else None
    ok = dernier if bloque is None else historique.dernier("OK")
    if ok is None:
        return ContexteRapprochement(id=None, bloque_plus_recent=bloque)
    return ContexteRapprochement(
        id=ok.id,
        date_arrete=ok.date_arrete,
        suspens=[s.model_dump() for s in ok.suspens],
        bloque_plus_recent=bloque,
    )


def vers_sortie(r: Reponse) -> ReponseQuestion:
    """Décimaux en texte (jamais de float), comme le reste de l'API."""
    return ReponseQuestion(
        question=r.question,
        reponse=r.reponse,
        chiffres=[
            ChiffreSortie(libelle=c.libelle, valeur=str(c.valeur), unite=c.unite)
            for c in r.chiffres
        ],
        requete_sql=r.requete_sql,
        parametres_sql=r.parametres_sql,
        lignes_sources=[
            LigneSourceSortie(table=ligne.table, valeurs=ligne.valeurs)
            for ligne in r.lignes_sources
        ],
        confiance=r.confiance,
        avertissements=r.avertissements,
        vigilances=[
            VigilanceSortie(
                code=v.code, message=v.message, emetteurs=v.emetteurs, valeur=str(v.valeur)
            )
            for v in r.vigilances
        ],
        reformulations=r.reformulations,
        comprehension=ComprehensionSortie(**r.comprehension),
    )
