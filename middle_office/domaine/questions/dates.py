"""Dates citées dans une question (« au 01/01/2025 », « hier », « d'ici le 31/12 »).

La base ne contient qu'une date de positions : une autre date ne doit pas recevoir son chiffre.
"""

import re
from datetime import date

from middle_office.domaine.questions.texte import normaliser

MOIS = (
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
)


RELATIVES = "|".join(
    [
        r"avant.hier",
        r"\bhier\b",
        r"la veille",
        r"semaine (derniere|passee)",
        r"mois (dernier|passe)",
        r"trimestre (dernier|passe)",
        r"annee (derniere|passee)",
        r"an (dernier|passe)",
    ]
)


def date_citee(question: str) -> str | None:
    """Une date explicite (AAAA-MM-JJ) ou une expression relative passée, trouvée dans la question."""
    texte = normaliser(question)
    for motif, ordre in (
        (r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", "amj"),
        (r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b", "jma"),
    ):
        if m := re.search(motif, texte):
            valeurs = dict(zip(ordre, map(int, m.groups()), strict=True))
            annee = valeurs["a"] + (2000 if valeurs["a"] < 100 else 0)
            try:
                return date(annee, valeurs["m"], valeurs["j"]).isoformat()
            except ValueError:
                return m.group()
    if m := re.search(rf"\b(1er|\d{{1,2}}) ({'|'.join(MOIS)}) (\d{{4}})\b", texte):
        jour = 1 if m[1] == "1er" else int(m[1])
        try:
            return date(int(m[3]), MOIS.index(m[2]) + 1, jour).isoformat()
        except ValueError:
            return m.group()
    if m := re.search(RELATIVES, texte):
        return m.group()
    return None


def fin_citee(date_ref: date, cible: str | None) -> date | None:
    """La date de fin citée pour des échéances (« d'ici le 31/12/2026 »), si elle est future."""
    try:
        fin = date.fromisoformat(cible or "")
    except ValueError:
        return None
    return fin if fin > date_ref else None
