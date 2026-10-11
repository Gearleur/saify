"""Reconnaître les titres cités dans une question : ISIN, libellé, nom court ou émetteur.

Plusieurs titres possibles : la question est ambiguë, on ne choisit pas à la place du gérant.
"""

import re
from pathlib import Path

from middle_office.domaine.base_gestion import connexion_lecture_seule
from middle_office.domaine.questions.texte import normaliser


def pour_titres(texte: str) -> str:
    return normaliser(texte).replace(",", ".")


def alias_du_titre(libelle: str, emetteur: str | None) -> set[str]:
    """Façons de citer un titre : libellé complet, libellé sans coupon ni échéance (« SFIL 3% 2033 »
    → « SFIL »), émetteur. Trois lettres au moins (EDF, RTE, OAT)."""
    court = re.sub(r"\s+\d[\d.,]*\s*%.*$", "", libelle)
    return {a for a in map(pour_titres, (libelle, court, emetteur or "")) if len(a) >= 3}


def titres_cites(base: Path, texte: str | None) -> list[tuple[str, str]]:
    """(isin, libellé) des titres cités : un ISIN écrit tel quel, sinon les alias trouvés en mots
    entiers. Un alias inclus dans un alias plus long trouvé lui aussi est ignoré (« OAT » dans
    « OAT 2.5% 2030 »). Plusieurs résultats : la question est ambiguë, on ne choisit pas."""
    if not texte:
        return []
    with connexion_lecture_seule(base) as db:
        titres = db.execute("SELECT isin, libelle, emetteur FROM titres").fetchall()
    libelles = {isin: libelle for isin, libelle, _ in titres}
    if isin := re.search(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b", texte.upper()):
        return [(isin.group(), libelles.get(isin.group(), isin.group()))]
    cible = pour_titres(texte)
    trouves: dict[str, set[str]] = {}
    for isin, libelle, emetteur in titres:
        for alias in alias_du_titre(libelle, emetteur):
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", cible):
                trouves.setdefault(alias, set()).add(isin)
    retenus = [a for a in trouves if not any(a != b and a in b for b in trouves)]
    isins = set().union(*(trouves[a] for a in retenus))
    return sorted((isin, libelles[isin]) for isin in isins)


def resoudre_titre(base: Path, texte: str | None) -> str | None:
    """L'ISIN du titre cité, s'il n'y en a qu'un."""
    cites = titres_cites(base, texte)
    return cites[0][0] if len(cites) == 1 else None
