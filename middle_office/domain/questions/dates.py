"""Dates citées dans une question (« au 01/01/2025 », « hier », « d'ici le 31/12 »).

La base ne contient qu'une date de positions : une autre date ne doit pas recevoir son chiffre.
"""

import re
from datetime import date

from middle_office.domain.questions.text import normalize

MONTHS = (
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


RELATIVE_DATES = "|".join(
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


def cited_date(question: str) -> str | None:
    """Une date explicite (AAAA-MM-JJ) ou une expression relative passée, trouvée dans la question."""
    text = normalize(question)
    for reason, order in (
        (r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", "amj"),
        (r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b", "jma"),
    ):
        if m := re.search(reason, text):
            values = dict(zip(order, map(int, m.groups()), strict=True))
            year = values["a"] + (2000 if values["a"] < 100 else 0)
            try:
                return date(year, values["m"], values["j"]).isoformat()
            except ValueError:
                return m.group()
    if m := re.search(rf"\b(1er|\d{{1,2}}) ({'|'.join(MONTHS)}) (\d{{4}})\b", text):
        day = 1 if m[1] == "1er" else int(m[1])
        try:
            return date(int(m[3]), MONTHS.index(m[2]) + 1, day).isoformat()
        except ValueError:
            return m.group()
    if m := re.search(RELATIVE_DATES, text):
        return m.group()
    return None


def cited_end(ref_date: date, target: str | None) -> date | None:
    """La date de fin citée pour des échéances (« d'ici le 31/12/2026 »), si elle est future."""
    try:
        end = date.fromisoformat(target or "")
    except ValueError:
        return None
    return end if end > ref_date else None
