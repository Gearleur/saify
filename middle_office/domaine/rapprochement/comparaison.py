"""Comparaison PMS ↔ conservateurs à la maille (fonds, ISIN, conservateur), tolérance nulle.

Une clé présente d'un seul côté est un suspens ; attendu chez X et livré chez Y, c'est un seul DEP.
"""

from collections import defaultdict
from decimal import Decimal

from middle_office.domaine.rapprochement.sources import Position
from middle_office.domaine.rapprochement.suspens import Suspens


def agreger(positions: list[Position]) -> dict[tuple[str, str, str], list[Position]]:
    groupes: dict[tuple[str, str, str], list[Position]] = defaultdict(list)
    for p in positions:
        groupes[(p.entite, p.isin, p.conservateur)].append(p)
    return groupes


def comparer(pms: list[Position], dep: list[Position]) -> list[Suspens]:
    """Jointure complète : une clé présente d'un seul côté est un suspens (sinon LVMH serait raté)."""
    cote_pms, cote_dep = agreger(pms), agreger(dep)
    suspens = []
    for cle in sorted(cote_pms.keys() | cote_dep.keys()):
        g_pms, g_dep = cote_pms.get(cle, []), cote_dep.get(cle, [])
        # Une position nulle est une absence : pas de suspens « ABS_DEP » pour 0 titre.
        q_pms = sum((p.quantite for p in g_pms), Decimal(0)) or None
        q_dep = sum((p.quantite for p in g_dep), Decimal(0)) or None
        if q_pms == q_dep:  # tolérance nulle : une seule unité d'écart est un suspens
            continue
        type_ = "ABS_DEP" if q_dep is None else "ABS_INT" if q_pms is None else "QTE"
        entite, isin, conservateur = cle
        libelle = next((p.libelle for p in g_pms + g_dep if p.libelle), "")
        sources = [p.ref for p in g_pms + g_dep]
        suspens.append(Suspens(entite, isin, conservateur, type_, q_pms, q_dep, libelle, sources))
    return suspens


def fusionner_dep(suspens: list[Suspens]) -> list[Suspens]:
    """Attendu chez X, livré chez Y : un seul suspens DEP (énoncé), même si les quantités diffèrent.

    Plusieurs candidats (2 conservateurs possibles) : on ne devine pas, on signale sur chaque suspens.
    """
    par_titre: dict[tuple[str, str], list[Suspens]] = defaultdict(list)
    for s in suspens:
        if s.type in ("ABS_DEP", "ABS_INT"):
            par_titre[(s.entite, s.isin)].append(s)
    for groupe in par_titre.values():
        absents = [s for s in groupe if s.type == "ABS_DEP"]
        trouves = [s for s in groupe if s.type == "ABS_INT"]
        if not absents or not trouves:
            continue
        if len(absents) == 1 and len(trouves) == 1:
            x, y = absents[0], trouves[0]
            suspens = [s for s in suspens if s is not x and s is not y]
            suspens.append(
                Suspens(
                    x.entite,
                    x.isin,
                    f"{x.conservateur}→{y.conservateur}",
                    "DEP",
                    x.qte_pms,
                    y.qte_dep,
                    x.libelle_titre or y.libelle_titre,
                    x.sources + y.sources,
                )
            )
        else:
            message = (
                f"DEP ambigu : absent chez {', '.join(s.conservateur for s in absents)}, "
                f"trouvé chez {', '.join(s.conservateur for s in trouves)} : à trancher par l'opérateur"
            )
            for s in groupe:
                s.signaler("DEP_AMBIGU", message)
    return suspens


def conservateurs_par_titre(positions: list[Position]) -> dict[tuple[str, str], set[str]]:
    """(entité, ISIN) -> conservateurs qui le détiennent (quantité non nulle), pour juger une piste :
    `mouvements` ne dit pas chez quel conservateur une opération se dénoue."""
    resultat: dict[tuple[str, str], set[str]] = defaultdict(set)
    for p in positions:
        if p.quantite:
            resultat[(p.entite, p.isin)].add(p.conservateur)
    return resultat
