"""Quand ne pas donner de chiffre, et quoi proposer à la place (« Attention » + reformulations).

Un chiffre inventé, ou vrai mais pour une autre question, finit chez le RCCI (ADR 0003).
"""

import re
from datetime import date

from middle_office.domaine.questions.intention import FONDS, Comprehension
from middle_office.domaine.questions.texte import normaliser

SEUIL_CONFIANCE = 0.7


ECRITURE = r"\b(supprim|modifi|ajout|effac|corrig|insere|annul|change|mets? a jour|mettre a jour)"


# Une demande d'écriture formulée comme un ordre, quel que soit le sujet (« corrige l'encours d'OBL ») ;
# « opérations annulées ? » reste une lecture.
ORDRE_ECRITURE = (
    r"^(peux.tu |pouvez.vous |merci de |il faut |je veux )?"
    r"(supprim|modifi|ajout|efface|corrig|insere|annule|change|mets? a jour|mettre a jour|remplac)"
)


DATE_UNIQUE = ("ENCOURS", "CONCENTRATION", "NON_DENOUEES")  # chiffres à la seule date de référence


PAR_TITRE = (
    "ECHEANCES",
    "NON_DENOUEES",
    "ORIGINE_SUSPENS",
)  # intentions qui savent filtrer un titre


CATALOGUE_PAR_DEFAUT = [
    "Encours valorisé du fonds OBL",
    "Tombées d'échéances à venir dans les 12 mois",
    "Opérations non dénouées",
]


def question_type(intention: str, fonds: str | None, titre: str | None = None) -> str:
    """Une question du catalogue, formulée pour être reconnue telle quelle (reformulation proposée)."""
    sur = f" sur {titre}" if titre else ""
    return {
        "ENCOURS": f"Encours valorisé du fonds {fonds or 'OBL'}",
        "CONCENTRATION": f"Concentration par émetteur du fonds {fonds or 'OBL'}",
        "NON_DENOUEES": f"Opérations non dénouées{sur}",
        "ECHEANCES": f"Tombées d'échéances à venir{sur}",
        "ORIGINE_SUSPENS": f"D'où vient le suspens{sur} ?",
    }[intention]


def motif_de_refus(c: Comprehension, question: str, date_ref: date) -> tuple[str, list[str]] | None:
    """Raison de ne pas répondre et reformulations proposées ; None si on peut répondre."""
    texte = normaliser(question).strip()
    if re.search(ORDRE_ECRITURE, texte) or (
        c.intention == "HORS_CATALOGUE" and re.search(ECRITURE, texte)
    ):
        return (
            "cet outil est en lecture seule : il ne modifie jamais l'inventaire (ni positions, ni "
            "opérations). Une correction se saisit dans le PMS.",
            CATALOGUE_PAR_DEFAUT,
        )
    if c.intention == "CONCENTRATION" and c.fonds is None:
        return (
            "la concentration par émetteur se lit fonds par fonds : précisez le fonds.",
            [f"Concentration par émetteur du fonds {code}" for code in ("OBL", "PAT", "ACT")],
        )
    if c.intention in DATE_UNIQUE and c.date_demandee and c.date_demandee != date_ref.isoformat():
        try:
            visee = f"le {date.fromisoformat(c.date_demandee):%d/%m/%Y}"
        except ValueError:
            visee = f"« {c.date_demandee} »"
        return (
            f"la base de gestion ne contient que les positions au {date_ref:%d/%m/%Y}, et la question "
            f"vise {visee}. Je ne donne pas le chiffre d'une autre date à la place.",
            [question_type(c.intention, c.fonds)],
        )
    if c.intention == "ENCOURS" and (c.isin or c.titres_candidats):
        return (
            "l'encours valorisé se calcule par fonds, pas pour un titre seul : je ne réponds pas "
            "à côté de la question.",
            [f"Encours valorisé du fonds {code}" for code in FONDS],
        )
    if c.intention in PAR_TITRE and c.titres_candidats:
        noms = ", ".join(libelle for _, libelle in c.titres_candidats)
        return (
            f"plusieurs titres correspondent ({noms}) : précisez lequel.",
            [question_type(c.intention, c.fonds, libelle) for _, libelle in c.titres_candidats[:3]],
        )
    if c.intention == "ORIGINE_SUSPENS" and c.isin is None:
        return (
            "je n'ai pas reconnu le titre : précisez son nom ou son ISIN.",
            ["D'où vient le suspens sur SCHNEIDER ?", "D'où vient le suspens sur FR0000051641 ?"],
        )
    if c.intention == "HORS_CATALOGUE":
        return (
            "je ne sais pas répondre à cette question de façon fiable. Je sais calculer : encours "
            "valorisé, tombées d'échéances, concentration par émetteur, opérations non dénouées, "
            "origine d'un suspens.",
            CATALOGUE_PAR_DEFAUT,
        )
    if c.confiance < SEUIL_CONFIANCE:
        return (
            "je ne suis pas sûr d'avoir compris la question, et je ne donne pas de chiffre sans en être sûr.",
            CATALOGUE_PAR_DEFAUT,
        )
    return None
