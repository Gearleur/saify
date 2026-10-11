"""Quand ne pas donner de chiffre, et quoi proposer à la place (« Attention » + reformulations).

Un chiffre inventé, ou vrai mais pour une autre question, finit chez le RCCI (ADR 0003).
"""

import re
from datetime import date

from middle_office.domain.questions.intent import FUNDS, Understanding
from middle_office.domain.questions.text import normalize

CONFIDENCE_THRESHOLD = 0.7


WRITE_REQUEST = (
    r"\b(supprim|modifi|ajout|effac|corrig|insere|annul|change|mets? a jour|mettre a jour)"
)


# Une demande d'écriture formulée comme un ordre, quel que soit le sujet (« corrige l'encours d'OBL ») ;
# « opérations annulées ? » reste une lecture.
WRITE_ORDER = (
    r"^(peux.tu |pouvez.vous |merci de |il faut |je veux )?"
    r"(supprim|modifi|ajout|efface|corrig|insere|annule|change|mets? a jour|mettre a jour|remplac)"
)


SINGLE_DATE_INTENTS = (
    "ENCOURS",
    "CONCENTRATION",
    "NON_DENOUEES",
)  # chiffres à la seule date de référence


PER_SECURITY_INTENTS = (
    "ECHEANCES",
    "NON_DENOUEES",
    "ORIGINE_SUSPENS",
)  # intentions qui savent filtrer un titre


DEFAULT_SUGGESTIONS = [
    "Encours valorisé du fonds OBL",
    "Tombées d'échéances à venir dans les 12 mois",
    "Opérations non dénouées",
]


def catalog_question(intent: str, fund: str | None, security: str | None = None) -> str:
    """Une question du catalogue, formulée pour être reconnue telle quelle (reformulation proposée)."""
    on = f" sur {security}" if security else ""
    return {
        "ENCOURS": f"Encours valorisé du fonds {fund or 'OBL'}",
        "CONCENTRATION": f"Concentration par émetteur du fonds {fund or 'OBL'}",
        "NON_DENOUEES": f"Opérations non dénouées{on}",
        "ECHEANCES": f"Tombées d'échéances à venir{on}",
        "ORIGINE_SUSPENS": f"D'où vient le suspens{on} ?",
    }[intent]


def refusal_reason(c: Understanding, question: str, ref_date: date) -> tuple[str, list[str]] | None:
    """Raison de ne pas répondre et reformulations proposées ; None si on peut répondre."""
    text = normalize(question).strip()
    if re.search(WRITE_ORDER, text) or (
        c.intent == "HORS_CATALOGUE" and re.search(WRITE_REQUEST, text)
    ):
        return (
            "cet outil est en lecture seule : il ne modifie jamais l'inventaire (ni positions, ni "
            "opérations). Une correction se saisit dans le PMS.",
            DEFAULT_SUGGESTIONS,
        )
    if c.intent == "CONCENTRATION" and c.fund is None:
        return (
            "la concentration par émetteur se lit fonds par fonds : précisez le fonds.",
            [f"Concentration par émetteur du fonds {code}" for code in ("OBL", "PAT", "ACT")],
        )
    if (
        c.intent in SINGLE_DATE_INTENTS
        and c.requested_date
        and c.requested_date != ref_date.isoformat()
    ):
        try:
            target_text = f"le {date.fromisoformat(c.requested_date):%d/%m/%Y}"
        except ValueError:
            target_text = f"« {c.requested_date} »"
        return (
            f"la base de gestion ne contient que les positions au {ref_date:%d/%m/%Y}, et la question "
            f"vise {target_text}. Je ne donne pas le chiffre d'une autre date à la place.",
            [catalog_question(c.intent, c.fund)],
        )
    if c.intent == "ENCOURS" and (c.isin or c.candidate_securities):
        return (
            "l'encours valorisé se calcule par fonds, pas pour un titre seul : je ne réponds pas "
            "à côté de la question.",
            [f"Encours valorisé du fonds {code}" for code in FUNDS],
        )
    if c.intent in PER_SECURITY_INTENTS and c.candidate_securities:
        names = ", ".join(label for _, label in c.candidate_securities)
        return (
            f"plusieurs titres correspondent ({names}) : précisez lequel.",
            [catalog_question(c.intent, c.fund, label) for _, label in c.candidate_securities[:3]],
        )
    if c.intent == "ORIGINE_SUSPENS" and c.isin is None:
        return (
            "je n'ai pas reconnu le titre : précisez son nom ou son ISIN.",
            ["D'où vient le suspens sur SCHNEIDER ?", "D'où vient le suspens sur FR0000051641 ?"],
        )
    if c.intent == "HORS_CATALOGUE":
        return (
            "je ne sais pas répondre à cette question de façon fiable. Je sais calculer : encours "
            "valorisé, tombées d'échéances, concentration par émetteur, opérations non dénouées, "
            "origine d'un suspens.",
            DEFAULT_SUGGESTIONS,
        )
    if c.confidence < CONFIDENCE_THRESHOLD:
        return (
            "je ne suis pas sûr d'avoir compris la question, et je ne donne pas de chiffre sans en être sûr.",
            DEFAULT_SUGGESTIONS,
        )
    return None
