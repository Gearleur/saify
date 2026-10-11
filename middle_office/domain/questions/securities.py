"""Reconnaître les titres cités dans une question : ISIN, libellé, nom court ou émetteur.

Plusieurs titres possibles : la question est ambiguë, on ne choisit pas à la place du gérant.
"""

import re
from pathlib import Path

from middle_office.domain.management_db import read_only_connection
from middle_office.domain.questions.text import normalize


def for_securities(text: str) -> str:
    return normalize(text).replace(",", ".")


def security_aliases(label: str, issuer: str | None) -> set[str]:
    """Façons de citer un titre : libellé complet, libellé sans coupon ni échéance (« SFIL 3% 2033 »
    → « SFIL »), émetteur. Trois lettres au moins (EDF, RTE, OAT)."""
    short = re.sub(r"\s+\d[\d.,]*\s*%.*$", "", label)
    return {a for a in map(for_securities, (label, short, issuer or "")) if len(a) >= 3}


def cited_securities(db_path: Path, text: str | None) -> list[tuple[str, str]]:
    """(isin, libellé) des titres cités : un ISIN écrit tel quel, sinon les alias trouvés en mots
    entiers. Un alias inclus dans un alias plus long trouvé lui aussi est ignoré (« OAT » dans
    « OAT 2.5% 2030 »). Plusieurs résultats : la question est ambiguë, on ne choisit pas."""
    if not text:
        return []
    with read_only_connection(db_path) as db:
        securities = db.execute("SELECT isin, libelle, emetteur FROM titres").fetchall()
    labels = {isin: label for isin, label, _ in securities}
    if isin := re.search(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b", text.upper()):
        return [(isin.group(), labels.get(isin.group(), isin.group()))]
    target = for_securities(text)
    found: dict[str, set[str]] = {}
    for isin, label, issuer in securities:
        for alias in security_aliases(label, issuer):
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", target):
                found.setdefault(alias, set()).add(isin)
    kept_aliases = [a for a in found if not any(a != b and a in b for b in found)]
    isins = set().union(*(found[a] for a in kept_aliases))
    return sorted((isin, labels[isin]) for isin in isins)


def resolve_security(db_path: Path, text: str | None) -> str | None:
    """L'ISIN du titre cité, s'il n'y en a qu'un."""
    cited = cited_securities(db_path, text)
    return cited[0][0] if len(cited) == 1 else None
